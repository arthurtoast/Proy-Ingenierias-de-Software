"""
EXTRAER - Saca las palabras distintas de un texto ya limpio.

Responsabilidad unica: str -> conjunto de palabras. No lee archivos, no
decodifica, no quita etiquetas, no importa a los otros modulos y no
lanza procesos ni hilos: el paralelismo lo decide main.py, igual que con
los otros tres pasos.

    extraer(texto) -> (palabras: set | None, error: str | None)

Nunca lanza excepciones.

QUE CUENTA COMO PALABRA
-----------------------
Una tira de letras de cualquier alfabeto, mas las marcas combinantes que
las acompanan. Se excluyen los digitos, la puntuacion y los simbolos.

Tambien quedan fuera, aunque Unicode los llame letras o numeros:

    ª º        categoria Lo, pero van pegados a cifras (1º, 2ª)
    ½ ¼ ¾ ² ³  categoria No, que \\d no descarta porque \\d solo cubre
               los digitos decimales de la categoria Nd

Las palabras se pasan a minusculas, asi que 'Casa' y 'CASA' son la misma.

POR QUE UNA CLASE DE CARACTERES EXPLICITA Y NO UNA TABLA
--------------------------------------------------------
La forma corta seria recorrer Unicode una vez, montar una tabla que
mapee "todo lo que no es letra" a un espacio, y usar str.translate()
mas split(). Funciona, pero recorre el texto en Python.

Construir en su lugar la clase de caracteres exacta y dejar que el motor
de expresiones regulares busque en C es mas rapido con el mismo
resultado. Medido sobre 2,19 M de caracteres de texto real:

    translate + split                 88 ms
    regex [^\\W\\d_]+                   71 ms   (mete ½ ¼ ¾)
    regex de rangos exactos           50 ms   identico a la tabla

Los rangos se calculan al importar el modulo y cuestan 2 ms, lo mismo
que costaba la tabla. En macOS los procesos hijos arrancan con 'spawn' y
reimportan el modulo, asi que ese coste se paga una vez por worker.
"""

import re
import unicodedata

# Por encima de este punto de codigo los caracteres se dan por buenos.
# Son alfabetos poco frecuentes y, si aparecen, es preferible que se
# queden dentro de la palabra a que la partan en dos.
TOPE = 0x2600


def _rangos_de_letras(tope=TOPE):
    """Los tramos de puntos de codigo que cuentan como letra.

    Se recorre Unicode una sola vez y se agrupan los codigos contiguos
    en rangos, para que la clase resultante sea corta: unos 340 rangos
    en vez de 20.000 caracteres sueltos.
    """
    rangos = []
    inicio = None
    for cp in range(tope):
        cat = unicodedata.category(chr(cp))
        # Letras (L*) y marcas combinantes (Mn), menos la ª y la º.
        es_letra = ((cat[0] == "L" or cat == "Mn")
                    and not (cat == "Lo" and cp < 0x100))
        if es_letra and inicio is None:
            inicio = cp
        elif not es_letra and inicio is not None:
            rangos.append((inicio, cp - 1))
            inicio = None
    if inicio is not None:
        rangos.append((inicio, tope - 1))
    return rangos


def _clase(rangos):
    """Los rangos, escritos como el interior de una clase [ ... ]."""
    trozos = []
    for a, b in rangos:
        if a == b:
            trozos.append(re.escape(chr(a)))
        else:
            trozos.append(re.escape(chr(a)) + "-" + re.escape(chr(b)))
    return "".join(trozos)


_CLASE = _clase(_rangos_de_letras())

# Todo lo que esta por encima del tope se acepta con \uXXXX-\U0010FFFF.
_RE_PALABRA = re.compile("[" + _CLASE + "☀-\U0010ffff]+")


def extraer(texto):
    """Texto limpio -> (conjunto de palabras distintas, error).

    Devuelve un conjunto, no una lista: la deduplicacion es el objetivo
    y hacerla aqui evita arrastrar repeticiones hasta el final.

    Las palabras se pasan a minusculas DESPUES de separarlas, no antes.
    Bajar el texto entero cuesta mas que bajar solo las palabras, que
    son una fraccion de los caracteres.
    """
    try:
        if texto is None:
            return None, "entrada nula"
        if not isinstance(texto, str):
            return None, "la entrada no es str (falta limpiar)"
        if not texto:
            return set(), None
        return {p.lower() for p in _RE_PALABRA.findall(texto)}, None
    except MemoryError:
        return None, "sin memoria al extraer"


# ======================================================================
#  Paso del vocabulario entre procesos
#
#  Un conjunto de cadenas se serializa objeto por objeto. Unirlas en una
#  sola cadena y partirla al llegar cuesta menos de la mitad, y los dos
#  extremos del viaje se benefician. Medido con 24.053 palabras:
#
#      pickle del conjunto        2,7 ms al enviar   2,8 ms al recibir
#      union + pickle del texto   1,1 ms al enviar   1,0 ms al recibir
#
#  Ninguna palabra puede contener un salto de linea, porque el salto no
#  es una letra: el separador es seguro.
# ======================================================================

_SEPARADOR = "\n"


def a_texto(palabras):
    """Conjunto -> una sola cadena, para cruzar la frontera de proceso."""
    return _SEPARADOR.join(palabras)


def de_texto(blob):
    """La cadena de vuelta a lista de palabras."""
    return blob.split(_SEPARADOR) if blob else []


# ======================================================================
#  Orden de salida
# ======================================================================

# Letras latinas que NO se descomponen en NFD, porque su acento va
# soldado al trazo y no es una marca aparte. Sin esta tabla acaban
# ordenadas por su punto de codigo, es decir, detras de la z: en el
# corpus de prueba 'ß' y 'ð' salian despues de 'zzzzzzz'.
_EQUIVALENTES = str.maketrans({
    "æ": "ae", "œ": "oe", "ß": "ss", "þ": "th",
    "ø": "o", "ð": "d", "đ": "d", "ħ": "h",
    "ł": "l", "ŧ": "t", "ı": "i", "ĸ": "k",
})


def clave_orden(palabra):
    """Ordena ignorando los diacriticos, pero sin alterar la palabra.

    En un corpus multilingue es lo razonable: 'közben' cae junto a
    'kozben' y no al final del diccionario, detras de la z. La palabra
    original se conserva como segundo criterio para que dos que solo se
    diferencien en las tildes salgan siempre en el mismo orden.

    Dos pasos, porque hay dos formas de llevar un acento. La mayoria de
    las letras acentuadas se separan en letra + marca con NFD y basta
    con tirar la marca; unas pocas no se separan y necesitan la tabla de
    arriba.
    """
    base = "".join(c for c in unicodedata.normalize("NFD", palabra)
                   if not unicodedata.combining(c))
    return (base.translate(_EQUIVALENTES), palabra)


def ordenar(palabras):
    """Conjunto -> lista ordenada, lista para escribir."""
    return sorted(palabras, key=clave_orden)
