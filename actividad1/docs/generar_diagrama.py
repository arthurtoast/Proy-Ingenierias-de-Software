"""Genera la imagen del diagrama de flujo de la Actividad 1.

Requiere matplotlib:  python3 -m pip install matplotlib
Uso:                  python3 docs/generar_diagrama.py
Salida:               docs/diagrama_flujo.png
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Polygon

SALIDA = Path(__file__).resolve().parent / "diagrama_flujo.png"

AZUL_BORDE = "#1f3864"
AZUL_RELLENO = "#dce6f4"
VERDE_RELLENO = "#d8ecdd"
AMBAR_RELLENO = "#fdeecf"
GRIS_TEXTO = "#12203a"

# Columnas del diagrama.
COL_ERROR = 2.0
COL_FIN = 2.4
COL_PRINCIPAL = 6.8
COL_CICLO = 11.8

figura, ejes = plt.subplots(figsize=(11.0, 11.4))
ejes.set_xlim(-0.3, 15.3)
ejes.set_ylim(0.0, 16.0)
ejes.axis("off")


def _texto(x, y, etiqueta, tamano=9.5):
    ejes.text(
        x, y, etiqueta, ha="center", va="center", fontsize=tamano,
        color=GRIS_TEXTO, zorder=3, linespacing=1.35,
    )


def proceso(x, y, etiqueta, ancho=3.6, alto=0.78, relleno=AZUL_RELLENO):
    """Rectángulo: un paso de procesamiento."""
    ejes.add_patch(FancyBboxPatch(
        (x - ancho / 2, y - alto / 2), ancho, alto,
        boxstyle="round,pad=0,rounding_size=0.06",
        linewidth=1.4, edgecolor=AZUL_BORDE, facecolor=relleno, zorder=2,
    ))
    _texto(x, y, etiqueta)


def terminador(x, y, etiqueta, ancho=2.6, alto=0.72):
    """Óvalo: inicio o fin del programa."""
    ejes.add_patch(FancyBboxPatch(
        (x - ancho / 2, y - alto / 2), ancho, alto,
        boxstyle=f"round,pad=0,rounding_size={alto / 2}",
        linewidth=1.4, edgecolor=AZUL_BORDE, facecolor=VERDE_RELLENO, zorder=2,
    ))
    _texto(x, y, etiqueta)


def decision(x, y, etiqueta, ancho=4.0, alto=1.3):
    """Rombo: una bifurcación del flujo."""
    vertices = [
        (x, y + alto / 2), (x + ancho / 2, y),
        (x, y - alto / 2), (x - ancho / 2, y),
    ]
    ejes.add_patch(Polygon(
        vertices, closed=True, linewidth=1.4,
        edgecolor=AZUL_BORDE, facecolor=AMBAR_RELLENO, zorder=2,
    ))
    _texto(x, y, etiqueta, tamano=9.0)


def entrada_salida(x, y, etiqueta, ancho=4.0, alto=0.78):
    """Paralelogramo: entrada o salida de datos."""
    sesgo = 0.34
    vertices = [
        (x - ancho / 2 + sesgo, y + alto / 2), (x + ancho / 2, y + alto / 2),
        (x + ancho / 2 - sesgo, y - alto / 2), (x - ancho / 2, y - alto / 2),
    ]
    ejes.add_patch(Polygon(
        vertices, closed=True, linewidth=1.4,
        edgecolor=AZUL_BORDE, facecolor=AZUL_RELLENO, zorder=2,
    ))
    _texto(x, y, etiqueta)


def flecha(puntos, etiqueta=None, desplazamiento=(0.0, 0.22)):
    """Dibuja una polilínea con punta de flecha al final."""
    for inicio, fin in zip(puntos, puntos[1:-1]):
        ejes.plot([inicio[0], fin[0]], [inicio[1], fin[1]],
                  color=AZUL_BORDE, linewidth=1.3, zorder=1,
                  solid_capstyle="round")
    penultimo, ultimo = puntos[-2], puntos[-1]
    ejes.annotate(
        "", xy=ultimo, xytext=penultimo, zorder=1,
        arrowprops=dict(arrowstyle="-|>", color=AZUL_BORDE, linewidth=1.3,
                        shrinkA=0, shrinkB=0),
    )
    if etiqueta:
        ejes.text(
            puntos[0][0] + desplazamiento[0], puntos[0][1] + desplazamiento[1],
            etiqueta, fontsize=8.5, color=AZUL_BORDE, ha="center", va="center",
            fontweight="bold", zorder=4,
        )


# --- Columna principal ------------------------------------------------------
terminador(COL_PRINCIPAL, 15.2, "Inicio")
proceso(COL_PRINCIPAL, 14.1, "Iniciar cronómetro\nde ejecución total")
entrada_salida(COL_PRINCIPAL, 13.0, "Leer argumentos: carpeta,\nmatrícula y fólder de salida")
decision(COL_PRINCIPAL, 11.7, "¿Matrícula y carpeta\nválidas?")
proceso(COL_PRINCIPAL, 10.4, "Listar archivos .html del\nfólder, ordenados por nombre")
decision(COL_PRINCIPAL, 9.1, "¿Hay archivos HTML?")
proceso(COL_PRINCIPAL, 7.9, "Iniciar cronómetro\nde apertura")
decision(COL_PRINCIPAL, 6.6, "¿Quedan archivos\npor procesar?")

flecha([(COL_PRINCIPAL, 14.84), (COL_PRINCIPAL, 14.49)])
flecha([(COL_PRINCIPAL, 13.71), (COL_PRINCIPAL, 13.39)])
flecha([(COL_PRINCIPAL, 12.61), (COL_PRINCIPAL, 12.35)])
flecha([(COL_PRINCIPAL, 11.05), (COL_PRINCIPAL, 10.79)], "Sí", (0.28, -0.18))
flecha([(COL_PRINCIPAL, 10.01), (COL_PRINCIPAL, 9.75)])
flecha([(COL_PRINCIPAL, 8.45), (COL_PRINCIPAL, 8.29)], "Sí", (0.28, -0.02))
flecha([(COL_PRINCIPAL, 7.51), (COL_PRINCIPAL, 7.25)])

# --- Rama de error ----------------------------------------------------------
proceso(COL_ERROR, 8.5, "Imprimir mensaje\nde error", ancho=3.2)
terminador(COL_ERROR, 7.4, "Fin (código 1)")

flecha([(COL_PRINCIPAL - 2.0, 11.7), (COL_ERROR, 11.7), (COL_ERROR, 8.89)],
       "No", (-0.3, 0.22))
flecha([(COL_PRINCIPAL - 2.0, 9.1), (COL_ERROR + 0.001, 9.1), (COL_ERROR, 8.89)],
       "No", (-0.3, 0.22))
flecha([(COL_ERROR, 8.11), (COL_ERROR, 7.76)])

# --- Cuerpo del ciclo -------------------------------------------------------
proceso(COL_CICLO, 5.4, "Abrir y leer el archivo completo\nen modo binario, midiendo\nsu tiempo de apertura", ancho=4.6, alto=1.0)
decision(COL_CICLO, 4.0, "¿Lectura exitosa?", ancho=3.6, alto=1.2)
proceso(10.2, 2.7, "Registrar ruta,\nbytes y tiempo", ancho=2.9)
proceso(13.6, 2.7, "Registrar ruta, tiempo\ny mensaje de error", ancho=3.0)

flecha([(COL_PRINCIPAL + 2.0, 6.6), (COL_CICLO, 6.6), (COL_CICLO, 5.91)],
       "Sí", (0.3, 0.22))
flecha([(COL_CICLO, 4.9), (COL_CICLO, 4.61)])
flecha([(COL_CICLO - 1.8, 4.0), (10.2, 4.0), (10.2, 3.10)], "Sí", (-0.3, 0.22))
flecha([(COL_CICLO + 1.8, 4.0), (13.6, 4.0), (13.6, 3.10)], "No", (0.3, 0.22))
# Ambas ramas se unen y regresan al inicio del ciclo.
flecha([(10.2, 2.31), (10.2, 1.7), (COL_PRINCIPAL, 1.7), (COL_PRINCIPAL, 5.94)])
ejes.plot([13.6, 13.6, 10.2], [2.31, 1.7, 1.7], color=AZUL_BORDE,
          linewidth=1.3, zorder=1, solid_capstyle="round")

# --- Cierre del programa ----------------------------------------------------
proceso(COL_FIN, 5.5, "Detener cronómetros de\napertura y de ejecución")
entrada_salida(COL_FIN, 4.3, "Escribir el log\na1_matricula.txt", ancho=3.8)
entrada_salida(COL_FIN, 3.1, "Imprimir totales\nen pantalla", ancho=3.8)
decision(COL_FIN, 1.75, "¿Hubo archivos\ncon error?", ancho=3.6, alto=1.2)
terminador(1.0, 0.45, "Fin (código 2)", ancho=2.3, alto=0.66)
terminador(4.6, 0.45, "Fin (código 0)", ancho=2.3, alto=0.66)

flecha([(COL_PRINCIPAL - 2.0, 6.6), (COL_FIN, 6.6), (COL_FIN, 5.91)],
       "No", (-0.3, 0.22))
flecha([(COL_FIN, 5.11), (COL_FIN, 4.71)])
flecha([(COL_FIN, 3.91), (COL_FIN, 3.51)])
flecha([(COL_FIN, 2.71), (COL_FIN, 2.37)])
flecha([(COL_FIN - 1.8, 1.75), (1.0, 1.75), (1.0, 0.80)], "Sí", (-0.3, 0.22))
flecha([(COL_FIN + 1.8, 1.75), (4.6, 1.75), (4.6, 0.80)], "No", (0.3, 0.22))

figura.tight_layout(pad=0.3)
figura.savefig(SALIDA, dpi=200, facecolor="white")
print(f"Diagrama generado en: {SALIDA}")
