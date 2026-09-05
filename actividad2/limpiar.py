"""
LIMPIAR - Quita las etiquetas y deja solo el texto visible.

Responsabilidad unica: str con HTML -> str con el texto. No lee archivos,
no decodifica, no importa a los otros modulos.

    limpiar(texto) -> (texto_limpio: str | None, error: str | None)

Nunca lanza excepciones. Este es el unico paso que el programa cronometra.

EL PATRON DE ETIQUETA Y EL ReDoS (CWE-1333)
-------------------------------------------
El patron que sale solo al querer respetar las comillas de los atributos:

    <[a-zA-Z/!?][^>"']*(?:"[^"]*"|'[^']*'|[^>"'])*>

es vulnerable. El [^>"']* inicial y el [^>"'] del grupo pueden consumir
los mismos caracteres, y esa ambiguedad dispara un backtracking
cuadratico: unos pocos KB de basura sin un '>' que cierre bastan para
congelar el proceso. Denegacion de servicio con un archivo diminuto.

La solucion es quitar el [^>"']* inicial. Sin el, las tres alternativas
del grupo empiezan por caracteres disjuntos ('"', "'", y todo lo demas),
el patron deja de ser ambiguo y el coste pasa a ser lineal. El
cuantificador posesivo *+ es un extra que prohibe el backtracking del
todo, pero solo existe desde Python 3.11: se compila si esta disponible
y si no se usa la version sin el, que tambien es lineal.

Protecciones:

  CWE-1333 ReDoS ................. patron no ambiguo (+ posesivo si se puede)
  CWE-79   Sanitizado ingenuo .... unescape al final y una sola vez
  CWE-158  Caracteres nulos ...... los controles no llegan a la salida
  CWE-400  Agotar recursos ....... limite de longitud del texto
"""

import html as _html
import re

MAX_CHARS = 40 * 1024 * 1024

# script y style se eliminan CON su contenido. Sin esto, el JavaScript y
# el CSS acabarian dentro de lo que el programa llama "texto".
_RE_SCRIPT_STYLE = re.compile(
    r"<(script|style|template|noscript)\b[^>]*>.*?</\1\s*>", re.I | re.S)

# Un script que nunca se cierra: nos comemos el resto del archivo antes
# que dejar codigo suelto en la salida.
_RE_SCRIPT_ABIERTO = re.compile(r"<(script|style)\b[^>]*>.*\Z", re.I | re.S)

_RE_COMENTARIO = re.compile(r"<!--.*?-->", re.S)

# --- Etiquetas de bloque frente a etiquetas en linea --------------------
# No todas las etiquetas separan palabras. Un navegador dibuja
#
#     <b>ne</b><i>gri</i><u>ta</u>      como   negrita
#     <p>uno</p><p>dos</p>              como   uno / dos en dos lineas
#
# Sustituir TODA etiqueta por un espacio parte palabras que en la pagina
# se leen juntas: '1</span><span>2' es el precio 12, no '1 2'. Y es un
# patron comun de verdad: resaltados de busqueda, superindices, enlaces
# a mitad de palabra, digitos envueltos en span para darles estilo.
#
# Por eso cada etiqueta se sustituye segun su nombre: las de bloque por
# un salto de linea y las demas por nada.
#
# Se hace en UNA sola pasada, no en dos. Con dos pasadas, la de bloques
# puede consumir caracteres que estaban DENTRO de otra etiqueta mal
# formada y dejar a la segunda sin saber donde termina. Con este HTML
# real, donde sobra un '<':
#
#     <TD ALIGN="left"><CHAMBERLAIN</TD>  <TD ALIGN="right">70</TD>
#
# la primera pasada se llevaba el </TD> de dentro del pseudo-tag
# '<CHAMBERLAIN</TD>' y la segunda seguia buscando el cierre hasta
# comerse el 70.
_BLOQUE = [
    "address", "article", "aside", "blockquote", "body", "br", "caption",
    "center", "col", "colgroup", "dd", "details", "dialog", "dir", "div",
    "dl", "dt", "fieldset", "figcaption", "figure", "footer", "form",
    "h1", "h2", "h3", "h4", "h5", "h6", "head", "header", "hgroup", "hr",
    "html", "legend", "li", "main", "menu", "nav", "ol", "optgroup",
    "option", "p", "pre", "section", "summary", "table", "tbody", "td",
    "tfoot", "th", "thead", "title", "tr", "ul",
]

# --- Donde termina una etiqueta -----------------------------------------
# La regla del estandar HTML es que una comilla solo abre un valor de
# atributo si aparece JUSTO DESPUES del '='. En cualquier otro sitio es
# un caracter mas y la etiqueta acaba en el primer '>'.
#
# Tratar toda comilla como delimitador es un error caro con HTML del
# mundo real, donde abundan las comillas descolgadas:
#
#     <A NAME=HeadList"></A>
#
# Esa comilla suelta hacia que el filtro buscara su pareja cientos de
# lineas mas abajo y se llevara por delante todo el texto intermedio.
#
# Las cuatro alternativas empiezan por caracteres disjuntos ('=' contra
# todo lo demas, y entre las tres del '=' decide el lookahead), asi que
# el patron no es ambiguo y el coste sigue siendo lineal.
_CUERPO = r"""(?:[^>=]|=\s*"[^"]*"|=\s*'[^']*'|=(?!\s*["']))*{}"""

_BASE_ETIQUETA = r"<[a-zA-Z/!?]" + _CUERPO + ">"

# El cuantificador posesivo solo existe desde Python 3.11; si no esta,
# se compila la misma expresion sin el.
try:
    _RE_ETIQUETA = re.compile(_BASE_ETIQUETA.format("+"), re.S)
except re.error:
    _RE_ETIQUETA = re.compile(_BASE_ETIQUETA.format(""), re.S)

_BLOQUE_SET = frozenset(_BLOQUE)


def _sustituir(m):
    """Un salto de linea si la etiqueta es de bloque, nada si es en linea.

    El nombre se saca del texto ya emparejado con operaciones de cadena,
    no con otra expresion regular: capturarlo dentro del patron volveria
    a hacerlo ambiguo, que es lo que causaba el ReDoS.
    """
    s = m.group(0)
    i = 2 if s[1] == "/" else 1
    j = i
    while j < len(s) and s[j].isalnum():
        j += 1
    return "\n" if s[i:j].lower() in _BLOQUE_SET else ""

# --- Ultimo repaso para etiquetas con una comilla que nunca cierra ------
# '<a title="rota>texto</a>' no lo resuelve el patron principal: la
# comilla viene justo despues del '=', asi que abre un valor de atributo
# que nunca se cierra. Un navegador se traga el resto del documento
# entero; aqui preferimos recuperar el texto.
#
# Este patron es deliberadamente estricto: exige un nombre de etiqueta
# seguido de un atributo con '='. Asi nunca toca un '<' suelto del
# texto -- 'si a<b y c>d' no tiene ningun '=' antes del '>' y no encaja.
_RE_RESTO = re.compile(r"<[a-zA-Z][a-zA-Z0-9]*\s+[a-zA-Z-]+\s*=[^>]*>", re.S)

# DOCTYPE, CDATA y restos de instrucciones de procesamiento.
_RE_DECLARACION = re.compile(r"<![^>]*>", re.S)

# Una etiqueta abierta que se queda a medias al final del archivo.
_RE_COLA = re.compile(r"<[a-zA-Z/!?][^>]*\Z", re.S)

# Caracteres de control, NUL incluido. Un \x00 trunca cualquier programa
# posterior que trabaje con cadenas de C, y es un truco conocido para
# esconder contenido de un filtro que venga despues.
_RE_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

_RE_ESPACIOS = re.compile(r"[ \t\r\f\v\xa0]+")
_RE_LINEAS = re.compile(r"\n{3,}")

# --- Texto preformateado ------------------------------------------------
# Dentro de <pre> los espacios SON el contenido: alli viven las tablas
# de texto, el codigo y el arte ASCII. Colapsarlos destruye el dibujo,
# y un navegador no lo hace. Asi que el contenido de cada <pre> se
# aparta antes de normalizar los espacios y se devuelve al final.
#
# El hueco se marca con caracteres del Area de Uso Privado de Unicode,
# que no aparecen en texto real y que ninguna de las otras limpiezas
# toca. Se busca con una expresion regular en vez de con 'in' para no
# tener que copiar el documento entero en minusculas solo para mirar.
_RE_HAY_PRE = re.compile(r"<pre\b", re.I)
_MARCA_INI, _MARCA_FIN = "", ""
_RE_MARCA = re.compile(_MARCA_INI + r"(\d+)" + _MARCA_FIN)

_BASE_PRE = r"<pre\b" + _CUERPO + r">(.*?)</pre\s*>"

# Un <pre> que nunca se cierra llega hasta el final del documento, que es
# lo que hace un navegador. No es un caso raro: en archivos historicos de
# listas de correo es lo habitual, y es justo donde vive el arte ASCII.
_BASE_PRE_ABIERTO = r"<pre\b" + _CUERPO + r">(.*)\Z"

try:
    _RE_PRE = re.compile(_BASE_PRE.format("+"), re.I | re.S)
    _RE_PRE_ABIERTO = re.compile(_BASE_PRE_ABIERTO.format("+"), re.I | re.S)
except re.error:
    _RE_PRE = re.compile(_BASE_PRE.format(""), re.I | re.S)
    _RE_PRE_ABIERTO = re.compile(_BASE_PRE_ABIERTO.format(""), re.I | re.S)

# Dentro de un <pre>, un <br> si es un salto de linea.
_RE_BR = re.compile(r"<br\b" + _CUERPO.format("") + ">", re.I | re.S)

# --- Elementos de texto crudo -------------------------------------------
# <xmp>, <listing> y <plaintext> son de los anos noventa y siguen
# apareciendo en archivos de esa epoca. Su contenido NO es marcado: un
# '<b>' dentro de un <xmp> se ve tal cual en la pagina, no en negrita, y
# las entidades tampoco se traducen. Ademas conservan los espacios, como
# <pre>.
#
# <plaintext> es el caso extremo: no tiene etiqueta de cierre, todo lo
# que va detras es texto literal hasta el final del documento.
_RE_HAY_CRUDO = re.compile(r"<(?:xmp|listing|plaintext)\b", re.I)

_BASE_CRUDO = r"<(?:xmp|listing)\b" + _CUERPO + r">(.*?)</(?:xmp|listing)\s*>"
_BASE_CRUDO_ABIERTO = r"<(?:xmp|listing|plaintext)\b" + _CUERPO + r">(.*)\Z"

try:
    _RE_CRUDO = re.compile(_BASE_CRUDO.format("+"), re.I | re.S)
    _RE_CRUDO_ABIERTO = re.compile(_BASE_CRUDO_ABIERTO.format("+"), re.I | re.S)
except re.error:
    _RE_CRUDO = re.compile(_BASE_CRUDO.format(""), re.I | re.S)
    _RE_CRUDO_ABIERTO = re.compile(_BASE_CRUDO_ABIERTO.format(""), re.I | re.S)


def _apartar(texto, guardados, crudo=False):
    """Aparta el contenido preformateado y deja una marca en su lugar.

    Con crudo=False (<pre>) el contenido es marcado normal: se le quitan
    las etiquetas y se traducen las entidades, pero no se tocan los
    espacios.

    Con crudo=True (<xmp>, <listing>, <plaintext>) el contenido no es
    marcado en absoluto: se deja tal cual, que es lo que muestra un
    navegador.
    """
    def guardar(m):
        dentro = m.group(1)
        if not crudo:
            dentro = _RE_BR.sub("\n", dentro)
            dentro = _RE_ETIQUETA.sub("", dentro)
            dentro = _html.unescape(dentro)
        dentro = _RE_CONTROL.sub("", dentro)
        guardados.append(dentro)
        return "\n" + _MARCA_INI + str(len(guardados) - 1) + _MARCA_FIN + "\n"

    # Primero los que cierran bien; lo que quede abierto llega hasta el
    # final del documento, que es lo que hace un navegador.
    if crudo:
        texto = _RE_CRUDO.sub(guardar, texto)
        return _RE_CRUDO_ABIERTO.sub(guardar, texto)
    texto = _RE_PRE.sub(guardar, texto)
    return _RE_PRE_ABIERTO.sub(guardar, texto)


def limpiar(texto, max_chars=MAX_CHARS):
    """HTML en str -> (texto visible, error). Nunca lanza excepciones."""
    try:
        if texto is None:
            return None, "entrada nula"
        if not isinstance(texto, str):
            return None, "la entrada no es str (falta decodificar)"
        if not texto:
            return "", None
        if len(texto) > max_chars:
            return None, f"texto demasiado largo ({len(texto)} caracteres)"

        # El orden importa: primero lo que tiene contenido propio que hay
        # que eliminar entero, y solo despues las etiquetas sueltas.
        texto = _RE_COMENTARIO.sub("\n", texto)
        texto = _RE_SCRIPT_STYLE.sub("\n", texto)
        texto = _RE_SCRIPT_ABIERTO.sub("\n", texto)

        # El texto preformateado se aparta antes de tocar los espacios.
        # La busqueda previa evita el coste cuando no hay ningun <pre>,
        # que es el caso de la mayoria de los documentos.
        # El texto crudo va primero: un <xmp> puede contener un <pre>
        # literal que no hay que interpretar.
        pre = []
        if _RE_HAY_CRUDO.search(texto):
            texto = _apartar(texto, pre, crudo=True)
        if _RE_HAY_PRE.search(texto):
            texto = _apartar(texto, pre)

        # Una sola pasada: cada etiqueta se sustituye segun su nombre.
        texto = _RE_ETIQUETA.sub(_sustituir, texto)
        texto = _RE_RESTO.sub(_sustituir, texto)

        texto = _RE_DECLARACION.sub("\n", texto)
        texto = _RE_COLA.sub("\n", texto)

        # unescape va al FINAL y una SOLA vez. Antes del filtro, un
        # '&lt;script&gt;' del documento se convertiria en una etiqueta
        # real y quien escribio el archivo elegiria que ve el
        # sanitizador. Y volver a filtrar despues borraria texto
        # legitimo: '&lt;p&gt;esto no es un tag&lt;/p&gt;' debe llegar
        # entero a la salida.
        texto = _html.unescape(texto)

        texto = _RE_CONTROL.sub("", texto)
        texto = _RE_ESPACIOS.sub(" ", texto)
        texto = "\n".join(l.strip() for l in texto.split("\n"))
        texto = _RE_LINEAS.sub("\n\n", texto)

        if pre:
            texto = _RE_MARCA.sub(lambda m: pre[int(m.group(1))], texto)
            texto = _RE_LINEAS.sub("\n\n", texto)

        return texto.strip(), None

    except MemoryError:
        return None, "sin memoria al limpiar"


def esta_vacio(texto_limpio):
    """True si no queda ningun caracter visible."""
    return not (texto_limpio or "").strip()
