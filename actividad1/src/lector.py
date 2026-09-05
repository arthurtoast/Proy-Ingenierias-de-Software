"""Lectura y medición de tiempos de archivos HTML.

Este módulo concentra la lógica de la Actividad 1 del proyecto del buscador:
localizar los archivos HTML de un fólder y abrirlos midiendo cuánto tarda
cada apertura. Se mantiene separado de la interfaz de línea de comandos
(`main.py`) para poder probarlo de forma automatizada.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from time import perf_counter

# Extensiones que el buscador considera documentos HTML válidos.
EXTENSIONES_HTML = (".html", ".htm")


class ErrorLectura(Exception):
    """Error irrecuperable al preparar la lectura (fólder inválido o vacío)."""


@dataclass(frozen=True)
class ResultadoArchivo:
    """Resultado de intentar abrir un archivo.

    Atributos:
        ruta: ruta del archivo procesado.
        bytes_leidos: cantidad de bytes leídos (0 si hubo error).
        segundos: tiempo que tardó el intento de apertura.
        error: mensaje de error, o None si la lectura fue exitosa.
    """

    ruta: Path
    bytes_leidos: int
    segundos: float
    error: str | None = None

    @property
    def exitoso(self) -> bool:
        """True cuando el archivo se pudo abrir y leer completo."""
        return self.error is None


def listar_archivos_html(carpeta: Path) -> list[Path]:
    """Devuelve, ordenados por nombre, los archivos HTML de `carpeta`.

    El orden alfabético hace que la corrida sea reproducible y que el log
    salga en el mismo orden que la plantilla del reporte (001.html, 002.html...).

    Lanza:
        ErrorLectura: si la ruta no existe, no es un fólder o no tiene HTML.
    """
    if not carpeta.exists():
        raise ErrorLectura(f"la ruta '{carpeta}' no existe")
    if not carpeta.is_dir():
        raise ErrorLectura(f"la ruta '{carpeta}' no es un fólder")

    archivos = sorted(
        ruta
        for ruta in carpeta.iterdir()
        if ruta.is_file() and ruta.suffix.lower() in EXTENSIONES_HTML
    )
    if not archivos:
        raise ErrorLectura(f"el fólder '{carpeta}' no contiene archivos HTML")
    return archivos


def abrir_archivo(ruta: Path) -> ResultadoArchivo:
    """Abre un archivo y mide el tiempo que toma leerlo completo.

    Se lee en modo binario y de un solo golpe: es la forma más eficiente de
    traer el documento a memoria, porque evita el costo de decodificar texto
    y de iterar línea por línea. La decodificación se hará más adelante en el
    proyecto, ya sobre los bytes en memoria.

    Nunca lanza excepciones por archivos individuales: un archivo ilegible se
    reporta dentro del resultado para que el programa siga con los demás.
    """
    inicio = perf_counter()
    try:
        with open(ruta, "rb") as archivo:
            contenido = archivo.read()
    except OSError as excepcion:
        # errno + mensaje del sistema: suficiente para diagnosticar sin traceback.
        transcurrido = perf_counter() - inicio
        return ResultadoArchivo(ruta, 0, transcurrido, str(excepcion))
    transcurrido = perf_counter() - inicio
    return ResultadoArchivo(ruta, len(contenido), transcurrido)


def abrir_todos(archivos: list[Path]) -> tuple[list[ResultadoArchivo], float]:
    """Abre la lista completa de archivos y mide el tiempo total del recorrido.

    Devuelve los resultados individuales y el tiempo total del ciclo, que no
    es exactamente la suma de los tiempos individuales porque incluye el
    trabajo del propio ciclo.
    """
    inicio = perf_counter()
    resultados = [abrir_archivo(ruta) for ruta in archivos]
    return resultados, perf_counter() - inicio
