"""
DECODIFICAR - Convierte los bytes del archivo en una cadena de texto.

Responsabilidad unica: bytes -> str. No lee archivos, no quita etiquetas,
no importa a los otros modulos.

    decodificar(datos) -> (texto: str | None, error: str | None,
                           codec_usado: str)

Nunca lanza excepciones.

POR QUE ESTE PASO VA ANTES DE QUITAR LAS ETIQUETAS
--------------------------------------------------
Quitar las etiquetas directamente sobre los bytes es algo mas rapido,
porque ahorra decodificar el marcado que se va a tirar. Y es un fallo de
seguridad. Dos contraejemplos:

  UTF-16  el byte '<' va seguido de \\x00, asi que un filtro que trabaje
          sobre bytes no reconoce NINGUNA etiqueta: devuelve el
          documento entero como si fuera texto.

  UTF-7   la secuencia '+ADw-script+AD4-' no contiene el byte '<'. Pasa
          intacta por el filtro y se convierte en '<script>' DESPUES de
          decodificar. Ese "texto limpio" con una etiqueta viva dentro es
          XSS almacenado (CWE-79) introducido por el propio sanitizador.

De ahi el orden: primero decodificar, luego limpiar.

Protecciones:

  CWE-838 Codificacion inadecuada .. BOM > meta declarado > validacion
  CWE-176 Manejo de Unicode ........ lista blanca de codecs
  CWE-79  Contrabando de etiquetas . UTF-7 prohibido
  CWE-451 Suplantacion visual ...... controles bidireccionales eliminados
  CWE-20  Validacion de entrada .... errors='replace': nunca aborta
"""

import codecs
import re

SNIFF = 2048          # solo se inspecciona la cabecera buscando el meta

# Lista blanca. Un codec que no este aqui se rechaza y se pasa a adivinar.
# UTF-7 esta excluido a proposito: es el vector clasico de contrabando de
# etiquetas y ningun documento legitimo lo usa hoy.
CODECS_PERMITIDOS = {
    "ascii", "utf-8", "utf-8-sig",
    "utf-16", "utf-16-le", "utf-16-be",
    "utf-32", "utf-32-le", "utf-32-be",
    "cp1252", "cp1251", "cp1250", "cp850", "cp437",
    "latin-1", "iso-8859-1", "iso-8859-2", "iso-8859-9", "iso-8859-15",
    "koi8-r", "shift_jis", "euc-jp", "euc-kr", "gbk", "gb2312", "big5",
}

# Un HTML que declara latin-1 casi siempre trae bytes de windows-1252,
# que es un superconjunto: los 96 bytes de los acentos son identicos, y
# el rango 0x80-0x9F que latin-1 desperdicia en controles invisibles
# contiene las comillas tipograficas, el euro y la raya que Word genera
# constantemente. Decodificarlo como latin-1 estricto haria desaparecer
# esos caracteres. Los navegadores hacen esta misma sustitucion.
_ALIAS = {
    "latin-1": "cp1252", "latin1": "cp1252",
    "iso-8859-1": "cp1252", "iso8859-1": "cp1252",
    "us-ascii": "ascii", "utf8": "utf-8",
}

_RE_META = re.compile(
    rb"""<meta[^>]{0,200}?charset\s*=\s*["']?\s*([a-zA-Z0-9_\-]{1,40})""",
    re.I)

# El BOM de UTF-32 empieza igual que el de UTF-16, asi que va antes.
_BOMS = [
    (codecs.BOM_UTF8, "utf-8-sig"),
    (codecs.BOM_UTF32_LE, "utf-32-le"), (codecs.BOM_UTF32_BE, "utf-32-be"),
    (codecs.BOM_UTF16_LE, "utf-16-le"), (codecs.BOM_UTF16_BE, "utf-16-be"),
]

# Caracteres de formato invisibles que se eliminan del texto. Se listan
# por punto de codigo y no como literales a proposito: escritos tal cual
# serian invisibles en el editor y nadie podria revisar estas lineas.
_INVISIBLES = dict.fromkeys([
    0x200B, 0x200C, 0x200D, 0xFEFF,   # ancho cero: parten palabras y
                                      # esquivan busquedas por palabra
    0x202A, 0x202B, 0x202C,           # bidireccionales: embedding y pop
    0x202D, 0x202E,                   # bidireccionales: override
    0x2066, 0x2067, 0x2068, 0x2069,   # bidireccionales: isolates
    0x200E, 0x200F,                   # bidireccionales: marks
    0x2061, 0x2062, 0x2063, 0x2064,   # invisibles matematicos
], None)

# Los separadores de linea Unicode SI son saltos de linea, asi que se
# conservan como tales en vez de borrarse. Importan porque str.splitlines()
# parte por ellos y str.split('\n') no: dejarlos sin normalizar hace que
# dos formas de contar lineas den respuestas distintas sobre el mismo texto.
_SEPARADORES = {0x2028: "\n", 0x2029: "\n"}

# Una sola tabla, una sola pasada de translate() sobre el documento.
_NORMALIZAR = dict(_INVISIBLES)
_NORMALIZAR.update(_SEPARADORES)

# Sonda barata: translate() recorre todo el texto, mientras que esta
# busqueda la resuelve el motor de expresiones regulares y sale al primer
# acierto. Casi ningun documento trae estos caracteres, asi que lo normal
# es ahorrarse la pasada entera.
_RE_HAY_INVISIBLES = re.compile(
    "[" + "".join(chr(c) for c in sorted(_NORMALIZAR)) + "]")


def _adivinar(datos):
    """Sin declaracion fiable: se prueba UTF-8 estricto y si falla, cp1252.

    UTF-8 es autovalidante -- sus secuencias multibyte siguen un patron
    estricto que un texto latin-1 con acentos no cumple -- asi que el
    intento estricto es una prueba, no una suposicion. Sin ella, un
    archivo latin-1 sin declarar se degradaria en silencio, con los
    acentos convertidos en caracteres de reemplazo.

    Devuelve (codec, motivo, texto_o_None). El tercer elemento trae el
    texto ya decodificado cuando la prueba de UTF-8 salio bien, para que
    decodificar() no repita el trabajo: decodificar es caro y hacerlo dos
    veces duplicaria su coste.
    """
    try:
        return "utf-8", "utf-8 validado", bytes(datos).decode("utf-8")
    except UnicodeDecodeError:
        return "cp1252", "no es utf-8 valido -> cp1252", None


def detectar_encoding(datos):
    """Elige el codec. Devuelve (codec, motivo, texto_o_None)."""

    # 1. BOM. Es la senal mas fuerte porque esta en los bytes, no en una
    #    declaracion que el documento hace sobre si mismo.
    for bom, nombre in _BOMS:
        if datos.startswith(bom):
            return nombre, "BOM", None

    # 2. <meta charset>. Lo escribe quien creo el archivo, asi que pasa
    #    por la lista blanca antes de usarse. Si declara algo que no
    #    permitimos, se ignora y se adivina igual que si no hubiera nada.
    m = _RE_META.search(datos[:SNIFF])
    if m:
        crudo = m.group(1).decode("ascii", "ignore").lower().strip()
        nombre = _ALIAS.get(crudo, crudo)
        if nombre in CODECS_PERMITIDOS:
            try:
                codecs.lookup(nombre)
                return nombre, f"meta charset={crudo}", None
            except LookupError:
                pass
        codec, _motivo, texto = _adivinar(datos)
        return codec, f"meta '{crudo}' rechazado -> {codec}", texto

    # 3. Sin declaracion: se valida.
    return _adivinar(datos)


def decodificar(datos, encoding=None):
    """bytes -> (texto, error, codec_usado). Nunca lanza excepciones."""
    try:
        if not isinstance(datos, (bytes, bytearray)):
            return None, "la entrada no son bytes", ""

        if not datos:
            return "", None, "vacio"

        listo = None
        if encoding is None:
            encoding, _motivo, listo = detectar_encoding(datos)

        if encoding not in CODECS_PERMITIDOS:
            return None, f"codec no permitido: {encoding}", encoding

        # Si la deteccion ya decodifico el archivo para validarlo, se
        # reutiliza ese texto en vez de decodificarlo otra vez.
        #
        # errors='replace' es deliberado: un programa que recorre una
        # carpeta entera no debe abortar por un byte invalido. Los bytes
        # malos se vuelven U+FFFD y el analisis continua.
        texto = (listo if listo is not None
                 else bytes(datos).decode(encoding, errors="replace"))

        if _RE_HAY_INVISIBLES.search(texto):
            texto = texto.translate(_NORMALIZAR)

        return texto, None, encoding

    except LookupError:
        return None, f"codec desconocido: {encoding}", str(encoding)
    except MemoryError:
        return None, "sin memoria al decodificar", str(encoding)
