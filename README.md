# Proyecto de Ingeniería de Software — Buscador de documentos HTML

Proyecto del curso CS13309: construcción por etapas de un buscador sobre un corpus
de 505 documentos HTML. Cada actividad vive en su propia carpeta.

## Fase 1

| Actividad | Qué hace | Log |
|---|---|---|
| [actividad1](actividad1/) | Abre los archivos HTML y mide el tiempo de apertura | `a1_AL02879741.txt` |
| [actividad2](actividad2/) | Remueve las etiquetas HTML y genera un `.txt` por documento | `a2_AL02879741.txt` |
| [actividad3](actividad3/) | Genera la lista de palabras únicas ordenada alfabéticamente | `a3_AL02879741.txt` |

**Reporte de la fase 1:** [docs/Reporte_Fase1_AL02879741.docx](docs/Reporte_Fase1_AL02879741.docx)
— cubre las tres actividades con diagramas, resultados, casos de prueba y el código
como anexo.

## Autoría

La **actividad 1** fue desarrollada por el autor de este repositorio. Las
**actividades 2 y 3** fueron desarrolladas por **[nombre del compañero]**, de otro
equipo, y se integran aquí para documentar la fase completa. Cada carpeta lo indica
en su README.

## Requisitos

Python 3.9 o superior. Los programas usan solo la biblioteca estándar.

Para regenerar el reporte hacen falta tres paquetes:

```bash
python3 -m pip install python-docx matplotlib pillow
python3 docs/partir_diagramas.py        # divide los diagramas altos en tramos
python3 docs/generar_reporte_fase1.py   # -> docs/Reporte_Fase1_AL02879741.docx
```

## El corpus

Los 505 archivos HTML no están en el repo. Se descargan de la plataforma
(`CS13309_archivos_HTML.zip`) y los programas reciben su ruta por parámetro; en las
corridas documentadas está en `~/Downloads/Files`.

La numeración empieza en `002.html` (no existe `001.html`) e incluye tres archivos
adicionales sin numerar: `hard.html`, `medium.html` y `simple.html`.
