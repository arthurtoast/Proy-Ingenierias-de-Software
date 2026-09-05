"""Actividad 1 - Apertura de archivos HTML y medición de tiempos.

Uso típico:
    python3 src/main.py --carpeta ~/Downloads/Files

El programa abre todos los archivos HTML del fólder indicado, cronometra
cada apertura y genera el log `a1_<matricula>.txt` con el detalle y los
tiempos totales.

Códigos de salida:
    0  todos los archivos se abrieron correctamente
    1  error irrecuperable (fólder inválido, vacío o log no escribible)
    2  el programa terminó, pero uno o más archivos no se pudieron abrir
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from time import perf_counter

from lector import ErrorLectura, ResultadoArchivo, abrir_todos, listar_archivos_html

MATRICULA_POR_DEFECTO = "AL02879741"
CARPETA_POR_DEFECTO = Path.home() / "Downloads" / "Files"
# La plantilla del reporte usa 2 decimales, pero en un SSD moderno cada archivo
# tarda menos de una centésima y todo saldría en 0.00; 6 decimales conservan
# el formato de la plantilla sin perder la información de la medición.
DECIMALES = 6


def construir_parser() -> argparse.ArgumentParser:
    """Define los argumentos de línea de comandos del programa."""
    parser = argparse.ArgumentParser(
        description="Abre todos los archivos HTML de un fólder y mide los tiempos."
    )
    parser.add_argument(
        "--carpeta",
        type=Path,
        default=CARPETA_POR_DEFECTO,
        help=f"fólder con los archivos HTML (por defecto: {CARPETA_POR_DEFECTO})",
    )
    parser.add_argument(
        "--matricula",
        default=MATRICULA_POR_DEFECTO,
        help="matrícula usada para nombrar el log de salida",
    )
    parser.add_argument(
        "--salida",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "salida",
        help="fólder donde se escribe el log de salida",
    )
    return parser


def formatear_linea(resultado: ResultadoArchivo, ancho_ruta: int) -> str:
    """Da formato a un renglón del log: ruta, tiempo y error si lo hubo."""
    tiempo = f"{resultado.segundos:.{DECIMALES}f}"
    linea = f"{str(resultado.ruta):<{ancho_ruta}}  {tiempo:>12}"
    if not resultado.exitoso:
        linea += f"  ERROR: {resultado.error}"
    return linea


def construir_log(
    resultados: list[ResultadoArchivo],
    segundos_apertura: float,
    segundos_ejecucion: float,
) -> str:
    """Arma el contenido completo del archivo de log."""
    ancho_ruta = max(len(str(resultado.ruta)) for resultado in resultados)
    lineas = [formatear_linea(resultado, ancho_ruta) for resultado in resultados]

    fallidos = [resultado for resultado in resultados if not resultado.exitoso]
    lineas.append("")
    lineas.append(f"archivos procesados: {len(resultados)}")
    lineas.append(f"archivos con error: {len(fallidos)}")
    lineas.append(
        f"tiempo total en abrir los archivos: {segundos_apertura:.{DECIMALES}f} segundos"
    )
    lineas.append(
        f"tiempo total de ejecucion: {segundos_ejecucion:.{DECIMALES}f} segundos"
    )
    return "\n".join(lineas) + "\n"


def escribir_log(contenido: str, carpeta_salida: Path, matricula: str) -> Path:
    """Escribe el log en `carpeta_salida/a1_<matricula>.txt` y regresa su ruta."""
    carpeta_salida.mkdir(parents=True, exist_ok=True)
    ruta_log = carpeta_salida / f"a1_{matricula}.txt"
    ruta_log.write_text(contenido, encoding="utf-8")
    return ruta_log


def main(argumentos: list[str] | None = None) -> int:
    """Punto de entrada: regresa el código de salida del programa."""
    inicio_ejecucion = perf_counter()
    opciones = construir_parser().parse_args(argumentos)

    matricula = opciones.matricula.strip()
    if not matricula:
        print("Error: la matrícula no puede estar vacía.", file=sys.stderr)
        return 1

    try:
        archivos = listar_archivos_html(opciones.carpeta.expanduser())
    except ErrorLectura as excepcion:
        print(f"Error: {excepcion}.", file=sys.stderr)
        return 1

    print(f"Abriendo {len(archivos)} archivos HTML...")
    resultados, segundos_apertura = abrir_todos(archivos)
    segundos_ejecucion = perf_counter() - inicio_ejecucion
    contenido = construir_log(resultados, segundos_apertura, segundos_ejecucion)

    try:
        ruta_log = escribir_log(contenido, opciones.salida.expanduser(), matricula)
    except OSError as excepcion:
        print(f"Error: no se pudo escribir el log ({excepcion}).", file=sys.stderr)
        return 1

    fallidos = [resultado for resultado in resultados if not resultado.exitoso]
    for resultado in fallidos:
        print(f"Error al abrir {resultado.ruta}: {resultado.error}", file=sys.stderr)

    print(f"tiempo total en abrir los archivos: {segundos_apertura:.{DECIMALES}f} segundos")
    print(f"tiempo total de ejecucion: {segundos_ejecucion:.{DECIMALES}f} segundos")
    print(f"Log generado en: {ruta_log}")
    return 2 if fallidos else 0


if __name__ == "__main__":
    sys.exit(main())
