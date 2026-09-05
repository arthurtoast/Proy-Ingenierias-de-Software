# Actividad 1 — Apertura de archivos HTML y medición de tiempos

Proyecto del buscador (CS13309). Esta primera actividad abre todos los archivos
HTML del corpus, cronometra cada apertura y genera el log `a1_AL02879741.txt`.

- **Lenguaje:** Python 3 (sin dependencias externas)
- **Matrícula:** AL02879741

## Estructura

```
src/lector.py     lógica de listado, apertura y medición de tiempos
src/main.py       interfaz de línea de comandos y generación del log
tests/            14 casos de prueba automatizados (unittest)
docs/             diagrama de flujo, casos de prueba y scripts del reporte
salida/           log generado (a1_AL02879741.txt)
```

Los entregables generados (el reporte `Reporte_A1_AL02879741.docx` y el `.zip` de
entrega) no se versionan: se regeneran con los scripts de `docs/` (ver más abajo).

## Ejecución

```bash
python3 src/main.py --carpeta ~/Downloads/Files
```

Argumentos disponibles:

| Argumento | Por defecto | Descripción |
|---|---|---|
| `--carpeta` | `~/Downloads/Files` | fólder con los archivos HTML |
| `--matricula` | `AL02879741` | matrícula usada para nombrar el log |
| `--salida` | `salida/` | fólder donde se escribe el log |

Códigos de salida: `0` todo correcto, `1` error irrecuperable (fólder inválido,
sin HTML, log no escribible), `2` terminó pero algún archivo no se pudo abrir.

## Pruebas

```bash
python3 -m unittest discover -s tests -v
```

## Resultado de la corrida

Corpus de 505 archivos HTML en `~/Downloads/Files` (macOS, SSD):

```
archivos procesados: 505
archivos con error: 0
tiempo total en abrir los archivos: 0.055878 segundos
tiempo total de ejecucion: 0.063026 segundos
```

Tiempo mínimo por archivo 0.000028 s, máximo 0.003168 s, promedio 0.000110 s.

## Decisiones de diseño

- **Lectura binaria de un solo golpe** (`open(ruta, "rb").read()`): es la forma
  más eficiente de traer el documento a memoria. Evita el costo de decodificar
  texto y de iterar línea por línea; la decodificación se hará más adelante en
  el proyecto, ya sobre los bytes en memoria.
- **Seis decimales en lugar de dos.** La plantilla del enunciado muestra `0.10`,
  pero en un SSD moderno cada archivo tarda menos de una centésima de segundo y
  todos los renglones saldrían en `0.00`. Se conserva el formato de la plantilla
  con mayor precisión para que la medición sea informativa.
- **Un archivo ilegible no detiene el programa.** El error se registra en el
  renglón correspondiente del log y la corrida continúa con los demás archivos.
- **Tiempo total ≠ suma de tiempos individuales.** El total se mide con un
  cronómetro que envuelve todo el ciclo, por lo que incluye el trabajo del ciclo
  mismo (recorrer la lista, construir los resultados), tal como pide el enunciado.
- **Orden alfabético** del listado, para que la corrida sea reproducible y el log
  salga en el mismo orden que la plantilla del reporte.

## Documentación adicional

- [Diagrama de flujo](docs/diagrama_flujo.md) (fuente mermaid) y `docs/diagrama_flujo.png` (imagen)
- [Casos de prueba](docs/casos_prueba.md)

## Regenerar el reporte

El reporte de Word y el diagrama se generan con scripts. Solo hace falta si cambia
el código o se vuelve a correr el programa:

```bash
python3 -m pip install python-docx matplotlib
python3 docs/generar_diagrama.py   # -> docs/diagrama_flujo.png
python3 docs/generar_reporte.py    # -> Reporte_A1_AL02879741.docx
```
