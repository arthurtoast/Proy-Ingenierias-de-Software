"""Parte los diagramas verticales en secciones que caben en una página.

Los diagramas de las actividades 2 y 3 son muy altos (hasta 1:5.7). Metidos
enteros en una página quedan ilegibles, así que se cortan en tramos con un
pequeño solape para que se vea la continuidad entre uno y otro.

Requiere Pillow:  python3 -m pip install pillow
Uso:              python3 docs/partir_diagramas.py
Salida:           docs/diagramas/<actividad>_<diagrama>_<n>.png
"""

from math import ceil
from pathlib import Path

from PIL import Image

RAIZ = Path(__file__).resolve().parent.parent
DESTINO = RAIZ / "docs" / "diagramas"

# Proporción de una página con márgenes: 6.3 x 8.0 pulgadas.
PROPORCION_PAGINA = 8.0 / 6.3
SOLAPE = 40  # píxeles repetidos entre un tramo y el siguiente


def partir(origen: Path, prefijo: str) -> list[Path]:
    """Corta una imagen alta en tramos con proporción de página."""
    imagen = Image.open(origen)
    ancho, alto = imagen.size
    tramos = max(1, ceil((alto / ancho) / PROPORCION_PAGINA))
    if tramos == 1:
        return [origen]

    DESTINO.mkdir(parents=True, exist_ok=True)
    alto_tramo = ceil(alto / tramos)
    generados = []
    for indice in range(tramos):
        arriba = max(0, indice * alto_tramo - SOLAPE)
        abajo = min(alto, (indice + 1) * alto_tramo)
        recorte = imagen.crop((0, arriba, ancho, abajo))
        ruta = DESTINO / f"{prefijo}_{indice + 1}de{tramos}.png"
        recorte.save(ruta)
        generados.append(ruta)
    return generados


if __name__ == "__main__":
    for actividad in ("actividad2", "actividad3"):
        for diagrama in sorted((RAIZ / actividad / "diagramas").glob("*.png")):
            prefijo = f"{actividad}_{diagrama.stem}"
            partes = partir(diagrama, prefijo)
            print(f"{diagrama.relative_to(RAIZ)} -> {len(partes)} tramo(s)")
