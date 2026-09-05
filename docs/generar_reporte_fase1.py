"""Genera el reporte de la Fase 1 (actividades 1, 2 y 3) en formato Word.

Lee los datos reales de los tres logs generados por los programas, los
diagramas de flujo y el código fuente, y arma el documento completo.

Requiere python-docx:  python3 -m pip install python-docx
Uso:                   python3 docs/generar_reporte_fase1.py
Salida:                docs/Reporte_Fase1_AL02879741.docx
"""

from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

RAIZ = Path(__file__).resolve().parent.parent
DOCS = RAIZ / "docs"
SALIDA = DOCS / "Reporte_Fase1_AL02879741.docx"

MATRICULA = "AL02879741"
FECHA = "5 de septiembre de 2026"
AUTOR_A23 = "[Nombre del compañero que desarrolló las actividades 2 y 3]"

GRIS = RGBColor(0x59, 0x59, 0x59)
AZUL = RGBColor(0x1F, 0x38, 0x64)
ROJO = RGBColor(0x9C, 0x27, 0x27)


# ==========================================================================
#  Utilidades de formato
# ==========================================================================
def parrafo(doc, texto, tamano=11, cursiva=False, negrita=False,
            alineacion=None, color=None, espacio_despues=6):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(espacio_despues)
    if alineacion is not None:
        p.alignment = alineacion
    r = p.add_run(texto)
    r.font.size = Pt(tamano)
    r.italic = cursiva
    r.bold = negrita
    if color is not None:
        r.font.color.rgb = color
    return p


def vineta(doc, encabezado, cuerpo):
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.space_after = Pt(6)
    r = p.add_run(encabezado + " ")
    r.bold = True
    r.font.size = Pt(11)
    r2 = p.add_run(cuerpo)
    r2.font.size = Pt(11)
    return p


def bloque_codigo(doc, texto, tamano=8):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.line_spacing = 1.0
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), "F2F2F2")
    p._p.get_or_add_pPr().append(shd)
    lineas = texto.split("\n")
    for i, linea in enumerate(lineas):
        r = p.add_run(linea)
        r.font.name = "Consolas"
        r.font.size = Pt(tamano)
        r._element.rPr.rFonts.set(qn("w:eastAsia"), "Consolas")
        if i < len(lineas) - 1:
            r.add_break()
    return p


def tabla(doc, encabezados, filas, anchos=None, tamano=9.5):
    t = doc.add_table(rows=1, cols=len(encabezados))
    t.style = "Light Grid Accent 1"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for celda, titulo in zip(t.rows[0].cells, encabezados):
        celda.text = ""
        r = celda.paragraphs[0].add_run(titulo)
        r.bold = True
        r.font.size = Pt(tamano)
    for fila in filas:
        celdas = t.add_row().cells
        for celda, valor in zip(celdas, fila):
            celda.text = ""
            r = celda.paragraphs[0].add_run(str(valor))
            r.font.size = Pt(tamano)
    if anchos:
        for col, ancho in enumerate(anchos):
            for f in t.rows:
                f.cells[col].width = Inches(ancho)
    doc.add_paragraph().paragraph_format.space_after = Pt(4)
    return t


def espacio_captura(doc, descripcion, alto=2.5):
    t = doc.add_table(rows=1, cols=1)
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.rows[0].height = Inches(alto)
    celda = t.rows[0].cells[0]
    celda.text = ""
    p = celda.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(f"[ Pega aquí la captura de pantalla: {descripcion} ]")
    r.italic = True
    r.font.size = Pt(10)
    r.font.color.rgb = GRIS
    return t


def pie(doc, texto):
    parrafo(doc, texto, tamano=9, cursiva=True,
            alineacion=WD_ALIGN_PARAGRAPH.CENTER, color=GRIS, espacio_despues=12)


def seccion(doc, texto, nivel=1):
    h = doc.add_heading(texto, level=nivel)
    for r in h.runs:
        r.font.color.rgb = AZUL
    return h


def salto(doc):
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


def imagen(doc, ruta, ancho=6.3):
    doc.add_picture(str(ruta), width=Inches(ancho))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER


def anexar_codigo(doc, ruta_relativa):
    seccion(doc, ruta_relativa, nivel=2)
    bloque_codigo(doc, (RAIZ / ruta_relativa).read_text(encoding="utf-8").rstrip())


# ==========================================================================
#  Lectura de los datos reales de cada log
# ==========================================================================
def metricas_a1():
    lineas = (RAIZ / "actividad1" / "salida" / f"a1_{MATRICULA}.txt").read_text().splitlines()
    tiempos, primeras = [], []
    for linea in lineas:
        partes = linea.split()
        if len(partes) >= 2 and partes[0].endswith(".html"):
            tiempos.append(float(partes[1]))
            if len(primeras) < 4:
                primeras.append(linea)
    d = {"tiempos": tiempos, "primeras": primeras, "ultimas": lineas[-5:]}
    for linea in lineas:
        if ":" in linea:
            clave, valor = linea.split(":", 1)
            d[clave.strip()] = valor.strip()
    return d


def metricas_log(ruta):
    """Extrae los tiempos por archivo y los pares clave/valor de un log a2/a3."""
    lineas = Path(ruta).read_text().splitlines()
    tiempos, primeras = [], []
    for linea in lineas:
        partes = linea.split()
        if len(partes) >= 2 and partes[0].endswith(".html"):
            try:
                tiempos.append(float(partes[1]))
            except ValueError:
                continue
            if len(primeras) < 4:
                primeras.append(linea)
    d = {"tiempos": tiempos, "primeras": primeras, "lineas": lineas}
    for linea in lineas:
        if ":" in linea and not linea.split()[0].endswith(".html"):
            clave, valor = linea.split(":", 1)
            d[clave.strip()] = valor.strip().split()[0] if valor.strip() else ""
    return d


a1 = metricas_a1()
a2 = metricas_log(RAIZ / "actividad2" / f"a2_{MATRICULA}.txt")
a3 = metricas_log(RAIZ / "actividad3" / f"a3_{MATRICULA}.txt")

a1_apertura = float(a1["tiempo total en abrir los archivos"].split()[0])
a1_ejecucion = float(a1["tiempo total de ejecucion"].split()[0])
a1_t = a1["tiempos"]

a2_fase = float(a2["tiempo total en eliminar las etiquetas HTML"])
a2_ejec = float(a2["tiempo total de ejecucion"])
a2_t = a2["tiempos"]

a3_fase = float(a3["tiempo total en eliminar las etiquetas HTML"])
a3_ejec = float(a3["tiempo total de ejecucion"])
a3_union = float(a3["union del vocabulario"])
a3_orden = float(a3["ordenar y escribir palabras"])
a3_extrae = float(a3["extraccion pura (suma de CPU)"])
a3_palabras = a3["palabras unicas encontradas"]
a3_t = a3["tiempos"]

# ==========================================================================
#  Documento
# ==========================================================================
doc = Document()
doc.styles["Normal"].font.name = "Calibri"
doc.styles["Normal"].font.size = Pt(11)
for s in doc.sections:
    s.top_margin = s.bottom_margin = s.left_margin = s.right_margin = Inches(1.0)

# --- Portada --------------------------------------------------------------
for _ in range(3):
    doc.add_paragraph()
parrafo(doc, "Proyecto: Buscador de documentos HTML", tamano=14,
        alineacion=WD_ALIGN_PARAGRAPH.CENTER, color=GRIS)
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("Reporte de la Fase 1\nActividades 1, 2 y 3")
r.bold = True
r.font.size = Pt(24)
r.font.color.rgb = AZUL
parrafo(doc, "Abrir los archivos HTML · Remover las etiquetas HTML · "
             "Generar la lista de palabras", tamano=12,
        alineacion=WD_ALIGN_PARAGRAPH.CENTER, color=GRIS)
doc.add_paragraph()

datos = doc.add_table(rows=0, cols=2)
datos.alignment = WD_TABLE_ALIGNMENT.CENTER
for etiqueta, valor in [
    ("Alumno:", "[Escribe aquí tu nombre completo]"),
    ("Matrícula:", MATRICULA),
    ("Materia:", "CS13309 — [Nombre de la materia]"),
    ("Profesor:", "[Nombre del profesor]"),
    ("Lenguaje:", "Python 3 (biblioteca estándar)"),
    ("Fecha:", FECHA),
]:
    celdas = datos.add_row().cells
    celdas[0].width = Inches(1.3)
    celdas[1].width = Inches(4.2)
    re_ = celdas[0].paragraphs[0].add_run(etiqueta)
    re_.bold = True
    celdas[1].paragraphs[0].add_run(valor)

doc.add_paragraph()
parrafo(doc, "Nota de autoría", tamano=11, negrita=True, color=ROJO,
        espacio_despues=2)
parrafo(doc,
        f"La actividad 1 fue desarrollada por el autor de este reporte. Las "
        f"actividades 2 y 3 fueron desarrolladas por {AUTOR_A23}, de otro "
        f"equipo. En este reporte se integran, ejecutan y documentan las tres, "
        f"dejando constancia de su autoría original.", tamano=10, cursiva=True)

salto(doc)

# --- 1. Objetivo ----------------------------------------------------------
seccion(doc, "1. Objetivo de la fase 1")
parrafo(doc,
        "La fase 1 construye la base del buscador: llevar un corpus de documentos "
        "HTML desde el disco hasta una lista de palabras utilizable por un índice. "
        "Se divide en tres actividades encadenadas, cada una con su propia medición "
        "de tiempos:")
tabla(doc, ["Actividad", "Qué produce", "Log de salida"],
      [("1. Abrir los archivos HTML", "Los documentos leídos en memoria", f"a1_{MATRICULA}.txt"),
       ("2. Remover las etiquetas HTML", "Un archivo .txt por documento, sin etiquetas", f"a2_{MATRICULA}.txt"),
       ("3. Generar la lista de palabras", "Una lista de palabras únicas ordenada alfabéticamente", f"a3_{MATRICULA}.txt")],
      anchos=[2.2, 2.9, 1.8])
parrafo(doc,
        "Las tres actividades están escritas en Python 3 y usan únicamente la "
        "biblioteca estándar, como pide el enunciado de mantener el mismo lenguaje "
        "durante todo el proyecto.")

seccion(doc, "1.1 Entorno de pruebas", nivel=2)
tabla(doc, ["Concepto", "Valor"],
      [("Equipo", f"macOS, {a2['nucleos de la maquina']} núcleos, disco de estado sólido"),
       ("Lenguaje", "Python 3 (biblioteca estándar, sin dependencias externas)"),
       ("Corpus", f"{a2['archivos procesados']} archivos HTML, 11.4 MB en total"),
       ("Ubicación del corpus", "~/Downloads/Files")],
      anchos=[1.8, 4.5])
parrafo(doc,
        "El corpus entregado contiene 505 archivos. La numeración empieza en "
        "002.html (no existe 001.html) e incluye tres archivos adicionales sin "
        "numerar: hard.html, medium.html y simple.html.", tamano=10, cursiva=True)

# ==========================================================================
#  ACTIVIDAD 1
# ==========================================================================
salto(doc)
seccion(doc, "2. Actividad 1 — Abrir los archivos HTML")

seccion(doc, "2.1 Requerimiento", nivel=2)
parrafo(doc,
        "Abrir de la manera más eficiente posible todos los archivos HTML del "
        f"corpus, cronometrar el tiempo de apertura de cada archivo y generar el "
        f"log a1_{MATRICULA}.txt con esos tiempos, el tiempo total en abrir los "
        "archivos y el tiempo total de ejecución.")

seccion(doc, "2.2 Solución", nivel=2)
tabla(doc, ["Archivo", "Responsabilidad"],
      [("actividad1/src/lector.py", "Lista los HTML del fólder, abre cada uno y mide su tiempo de apertura."),
       ("actividad1/src/main.py", "Línea de comandos, validación de argumentos y generación del log."),
       ("actividad1/tests/test_lector.py", "14 casos de prueba automatizados (unittest).")],
      anchos=[2.3, 4.0])
vineta(doc, "Lectura binaria de un solo golpe.",
       "Cada archivo se abre con open(ruta, \"rb\") y se lee completo con un solo "
       "read(). Evita el costo de decodificar el texto y de iterar línea por línea; "
       "la decodificación se hace en la actividad 2, ya sobre los bytes en memoria.")
vineta(doc, "Seis decimales en lugar de dos.",
       "La plantilla del enunciado muestra 0.10, pero en un disco de estado sólido "
       "cada archivo tarda menos de una centésima de segundo y todos los renglones "
       "saldrían en 0.00. Se conserva el formato con mayor precisión.")
vineta(doc, "Un archivo ilegible no detiene el programa.",
       "El error se registra en el renglón correspondiente del log y la corrida "
       "continúa con los archivos restantes.")

seccion(doc, "2.3 Diagrama de flujo", nivel=2)
imagen(doc, RAIZ / "actividad1" / "docs" / "diagrama_flujo.png", 6.1)
pie(doc, "Figura 1. Diagrama de flujo de la actividad 1, incluyendo el manejo de errores.")

salto(doc)
seccion(doc, "2.4 Ejecución y salida", nivel=2)
bloque_codigo(doc,
              "$ cd actividad1\n"
              "$ python3 src/main.py --carpeta ~/Downloads/Files\n"
              f"Abriendo {a1['archivos procesados']} archivos HTML...\n"
              f"tiempo total en abrir los archivos: {a1_apertura:.6f} segundos\n"
              f"tiempo total de ejecucion: {a1_ejecucion:.6f} segundos\n"
              f"Log generado en: .../actividad1/salida/a1_{MATRICULA}.txt", 9)
parrafo(doc, f"Extracto del log a1_{MATRICULA}.txt:", espacio_despues=2)
bloque_codigo(doc, "\n".join(a1["primeras"]) + "\n...\n" + "\n".join(a1["ultimas"]), 8)
espacio_captura(doc, "ejecución de la actividad 1 en la terminal")
pie(doc, "Figura 2. Ejecución de la actividad 1.")

seccion(doc, "2.5 Resultados", nivel=2)
tabla(doc, ["Métrica", "Valor"],
      [("Archivos procesados", a1["archivos procesados"]),
       ("Archivos con error", a1["archivos con error"]),
       ("Tiempo mínimo por archivo", f"{min(a1_t):.6f} s"),
       ("Tiempo máximo por archivo", f"{max(a1_t):.6f} s"),
       ("Tiempo promedio por archivo", f"{sum(a1_t)/len(a1_t):.6f} s"),
       ("Suma de los tiempos individuales", f"{sum(a1_t):.6f} s"),
       ("Tiempo total en abrir los archivos", f"{a1_apertura:.6f} s"),
       ("Tiempo total de ejecución", f"{a1_ejecucion:.6f} s")],
      anchos=[3.4, 2.9])
parrafo(doc,
        f"El tiempo total ({a1_apertura:.6f} s) es mayor que la suma de los tiempos "
        f"individuales ({sum(a1_t):.6f} s) porque el cronómetro total incluye el "
        "trabajo del ciclo que recorre la lista. El tiempo de ejecución agrega la "
        "lectura de argumentos, el listado del fólder y la escritura del log.")

seccion(doc, "2.6 Casos de prueba", nivel=2)
parrafo(doc, "14 casos automatizados con unittest, todos con resultado satisfactorio "
             "(python3 -m unittest discover -s tests).", espacio_despues=4)
tabla(doc, ["#", "Caso", "Entrada", "Resultado obtenido"],
      [(1, "Fólder mixto", "HTML, TXT y una subcarpeta", "Solo los HTML, ordenados"),
       (2, "Extensiones alternas", "pagina.HTM", "Se reconoce como HTML"),
       (3, "Archivo válido", "001.html con contenido", "Lectura correcta, bytes y tiempo"),
       (4, "Archivo vacío", "0 bytes", "Lectura correcta con 0 bytes"),
       (5, "Corrida completa", "2 archivos válidos", "Código 0 y log con totales"),
       (6, "Corpus real", "505 archivos", "505 renglones, 0 errores"),
       (7, "Ruta inexistente", "/ruta/que/no/existe", "Mensaje de error, código 1"),
       (8, "La ruta es un archivo", "001.html como carpeta", "Error: no es un fólder"),
       (9, "Fólder sin HTML", "Solo notas.txt", "Error: no contiene archivos HTML"),
       (10, "Matrícula vacía", "--matricula \"   \"", "Mensaje de error, código 1"),
       (11, "Archivo sin permisos", "chmod 000", "Permission denied registrado"),
       (12, "Un archivo falla entre varios", "1 válido + 1 sin permisos", "Código 2 y renglón ERROR en el log")],
      anchos=[0.3, 1.7, 1.9, 2.4], tamano=9)

# ==========================================================================
#  ACTIVIDAD 2
# ==========================================================================
salto(doc)
seccion(doc, "3. Actividad 2 — Remover las etiquetas HTML")
parrafo(doc, f"Desarrollada por {AUTOR_A23}.", tamano=10, cursiva=True, color=ROJO)

seccion(doc, "3.1 Requerimiento", nivel=2)
parrafo(doc,
        "Eliminar las etiquetas HTML de los archivos de entrada y generar un archivo "
        "nuevo sin ellas, en el mismo lenguaje de la actividad anterior. Cronometrar "
        "el tiempo que tarda la función en eliminar las etiquetas de cada archivo y "
        f"el tiempo del proceso completo, en el log a2_{MATRICULA}.txt.")

seccion(doc, "3.2 Solución", nivel=2)
parrafo(doc,
        "El programa separa la responsabilidad en cuatro módulos. Los tres módulos "
        "de apoyo son funciones puras: no tienen estado, no se importan entre sí, "
        "devuelven (resultado, error) y no lanzan excepciones. main.py es el único "
        "que los importa y el único que decide el paralelismo.")
tabla(doc, ["Módulo", "Transformación", "Dónde corre"],
      [("cargar.py", "ruta → bytes", "En el proceso principal"),
       ("decodificar.py", "bytes → str", "En el worker"),
       ("limpiar.py", "str → texto sin etiquetas", "En el worker (cronometrado)"),
       ("main.py", "Orquestación, reparto y reporte de tiempos", "Proceso principal")],
      anchos=[1.5, 2.9, 1.9])
vineta(doc, "Procesos y no hilos.",
       "str.decode() y el módulo re no liberan el GIL, así que varios hilos se "
       "turnarían en un solo núcleo en vez de repartirse el trabajo. Los procesos "
       "además aíslan los fallos: un archivo que agote la memoria mata solo al "
       "worker que le tocó y el lote continúa.")
vineta(doc, "Los archivos grandes primero (Longest Processing Time first).",
       "Con tamaños dispares, dejar el archivo mayor para el final deja a los demás "
       "núcleos parados esperándolo. El orden se decide con os.path.getsize(), que "
       "consulta metadatos sin leer el contenido.")
vineta(doc, "Ventana de archivos en vuelo.",
       f"En vez de cargar la carpeta entera, mantiene {a2['archivos en vuelo a la vez']} "
       "archivos vivos a la vez: carga uno, lo envía y en cuanto un worker devuelve "
       "un resultado carga el siguiente. El pico de memoria depende de la ventana y "
       "no del tamaño de la carpeta.")
vineta(doc, "Solo se cronometra la eliminación de etiquetas.",
       "La decodificación y la escritura del .txt quedan fuera del cronómetro a "
       "propósito: medirían el disco y no el trabajo que pide la actividad.")

salto(doc)
seccion(doc, "3.3 Diagrama de flujo", nivel=2)
parrafo(doc, "El diagrama es muy alto, así que se presenta dividido en tres tramos "
             "consecutivos. El original completo está en "
             "actividad2/diagramas/1_flujo_general.png.", tamano=10, cursiva=True)
for i in range(1, 4):
    imagen(doc, DOCS / "diagramas" / f"actividad2_1_flujo_general_{i}de3.png", 6.0)
    pie(doc, f"Figura 3.{i}. Flujo general de la actividad 2 (tramo {i} de 3).")
    if i < 3:
        salto(doc)
parrafo(doc, "El detalle de lo que hace cada worker con un archivo está en el "
             "segundo diagrama del compañero: "
             "actividad2/diagramas/2_pipeline_archivo.png.", tamano=10, cursiva=True)

salto(doc)
seccion(doc, "3.4 Ejecución y salida", nivel=2)
bloque_codigo(doc,
              "$ cd actividad2\n"
              f"$ python3 main.py ~/Downloads/Files --salida salida --tiempos a2_{MATRICULA}.txt\n"
              f"{a2['archivos procesados']} archivos\n"
              f"  nucleos de la maquina : {a2['nucleos de la maquina']}\n"
              f"  procesos a lanzar     : {a2['procesos lanzados']}\n"
              f"  procesados {a2['archivos procesados']}/{a2['archivos procesados']}\n\n"
              f"texto     -> salida/  ({a2['archivos procesados']} archivos .txt)\n"
              f"tiempos   -> a2_{MATRICULA}.txt\n"
              f"tiempo total en eliminar las etiquetas HTML: {a2_fase:.6f} s\n"
              f"tiempo total de ejecucion: {a2_ejec:.6f} s", 9)
parrafo(doc, f"Extracto del log a2_{MATRICULA}.txt:", espacio_despues=2)
bloque_codigo(doc, "\n".join(a2["primeras"]) + "\n...\n" +
              "\n".join(l for l in a2["lineas"] if l.startswith("tiempo total")), 8)
espacio_captura(doc, "ejecución de la actividad 2 en la terminal")
pie(doc, "Figura 4. Ejecución de la actividad 2.")
parrafo(doc, "Ejemplo del texto resultante (salida/002.txt), ya sin etiquetas:",
        espacio_despues=2)
bloque_codigo(doc, (RAIZ / "actividad2" / "salida" / "002.txt")
              .read_text(encoding="utf-8")[:420].strip(), 8)

seccion(doc, "3.5 Resultados", nivel=2)
tabla(doc, ["Métrica", "Valor"],
      [("Archivos procesados", a2["archivos procesados"]),
       ("Archivos con error", a2["archivos con error"]),
       ("Archivos sin texto visible", a2["archivos vacios"]),
       ("Núcleos / procesos lanzados", f"{a2['nucleos de la maquina']} / {a2['procesos lanzados']}"),
       ("Tiempo mínimo por archivo", f"{min(a2_t):.6f} s"),
       ("Tiempo máximo por archivo", f"{max(a2_t):.6f} s"),
       ("Tiempo promedio por archivo", f"{sum(a2_t)/len(a2_t):.6f} s"),
       ("Limpieza pura (suma de CPU)", f"{a2['limpieza pura (suma de CPU)']} s"),
       ("Tiempo total en eliminar las etiquetas", f"{a2_fase:.6f} s"),
       ("Tiempo total de ejecución", f"{a2_ejec:.6f} s")],
      anchos=[3.4, 2.9])
parrafo(doc,
        f"La suma del trabajo de limpieza de todos los núcleos es "
        f"{a2['limpieza pura (suma de CPU)']} s, pero el tiempo real de esa fase es "
        f"{a2_fase:.6f} s: los {a2['procesos lanzados']} procesos trabajan a la vez, "
        f"así que el reloj avanza menos que la suma de CPU. Esa es exactamente la "
        f"ganancia del diseño con procesos.")

seccion(doc, "3.6 Casos de prueba", nivel=2)
parrafo(doc, "Casos ejecutados manualmente sobre el programa; se anota el "
             "comportamiento observado.", espacio_despues=4)
tabla(doc, ["#", "Caso", "Entrada", "Resultado obtenido"],
      [(1, "Corpus completo", "505 archivos HTML", "505 .txt generados, 0 errores"),
       (2, "Carpeta inexistente", "/ruta/que/no/existe", "\"no es una carpeta\", código 2"),
       (3, "La ruta es un archivo", "uso.txt", "\"no es una carpeta\", código 2"),
       (4, "Carpeta sin HTML", "Solo notas.txt", "\"no se encontraron archivos HTML\", código 0"),
       (5, "Archivo sin permisos", "chmod 000", "Renglón ERROR (sin permisos de lectura), código 1"),
       (6, "HTML malformado", "Etiquetas sin cerrar y anidadas", "Texto extraído correctamente"),
       (7, "Archivo vacío", "0 bytes", ".txt vacío, contado como \"sin texto visible\""),
       (8, "Codificación UTF-16", "BOM \\xff\\xfe", "Decodificado sin error")],
      anchos=[0.3, 1.7, 1.9, 2.4], tamano=9)

# ==========================================================================
#  ACTIVIDAD 3
# ==========================================================================
salto(doc)
seccion(doc, "4. Actividad 3 — Generar la lista de palabras")
parrafo(doc, f"Desarrollada por {AUTOR_A23}.", tamano=10, cursiva=True, color=ROJO)

seccion(doc, "4.1 Requerimiento", nivel=2)
parrafo(doc,
        "A partir de los archivos sin etiquetas, crear la lista de palabras del "
        "corpus y ordenarlas alfabéticamente. Cronometrar el tiempo que tarda la "
        "función en crear la lista y ordenarla, y el tiempo del proceso completo, "
        f"en el log a3_{MATRICULA}.txt.")

seccion(doc, "4.2 Solución", nivel=2)
parrafo(doc,
        "Es la misma arquitectura de la actividad 2 con un cuarto módulo, extraer.py, "
        "que convierte el texto limpio en un conjunto de palabras. Cada worker "
        "devuelve solo su vocabulario (sin repetidos y mucho más pequeño que el "
        "texto), y el proceso principal une todos los vocabularios, ordena y escribe "
        "palabras.txt.")
tabla(doc, ["Módulo", "Transformación", "Dónde corre"],
      [("cargar.py", "ruta → bytes", "En el proceso principal"),
       ("decodificar.py", "bytes → str", "En el worker"),
       ("limpiar.py", "str → texto sin etiquetas", "En el worker (cronometrado)"),
       ("extraer.py", "texto → conjunto de palabras", "En el worker"),
       ("main.py", "Orquestación, unión del vocabulario y ordenamiento", "Proceso principal")],
      anchos=[1.5, 2.9, 1.9])
vineta(doc, "Qué cuenta como palabra.",
       "Una tira de letras de cualquier alfabeto más las marcas que las acompañan. "
       "Se excluyen dígitos, puntuación y símbolos, y también los caracteres que "
       "Unicode llama letras o números pero van pegados a cifras (ª, º, ½, ², ³). "
       "Todo se pasa a minúsculas, así que \"Casa\" y \"CASA\" son la misma palabra.")
vineta(doc, "Expresión regular en vez de tabla de traducción.",
       "El autor midió las dos alternativas sobre 2.19 millones de caracteres de "
       "texto real: translate + split tardó 88 ms, la clase de caracteres exacta "
       "50 ms. El motor de expresiones regulares hace la búsqueda en C en vez de "
       "recorrer el texto en Python.")
vineta(doc, "Por qué cada worker hace la cadena entera.",
       "Dedicar un núcleo a cada etapa tendría un techo de ×1.77, marcado por la "
       "etapa más lenta (limpiar, 56.5 % del trabajo). Repartiendo por archivo el "
       "techo es el número de núcleos.")

salto(doc)
seccion(doc, "4.3 Diagrama de flujo", nivel=2)
parrafo(doc, "Dividido en cinco tramos consecutivos. El original completo está en "
             "actividad3/diagramas/1_flujo_general.png.", tamano=10, cursiva=True)
for i in range(1, 6):
    imagen(doc, DOCS / "diagramas" / f"actividad3_1_flujo_general_{i}de5.png", 5.4)
    pie(doc, f"Figura 5.{i}. Flujo general de la actividad 3 (tramo {i} de 5).")
    if i < 5:
        salto(doc)
parrafo(doc, "El detalle por archivo está en "
             "actividad3/diagramas/2_pipeline_archivo.png.", tamano=10, cursiva=True)

salto(doc)
seccion(doc, "4.4 Ejecución y salida", nivel=2)
bloque_codigo(doc,
              "$ cd actividad3\n"
              f"$ python3 main.py ~/Downloads/Files --palabras palabras.txt --tiempos a3_{MATRICULA}.txt\n"
              f"{a3['archivos procesados']} archivos\n"
              f"  procesados {a3['archivos procesados']}/{a3['archivos procesados']}\n\n"
              f"palabras  -> palabras.txt  ({a3_palabras} unicas)\n"
              f"tiempos   -> a3_{MATRICULA}.txt\n"
              f"tiempo total en eliminar las etiquetas HTML: {a3_fase:.6f} s\n"
              f"tiempo total de ejecucion: {a3_ejec:.6f} s", 9)
parrafo(doc, f"Extracto del log a3_{MATRICULA}.txt:", espacio_despues=2)
bloque_codigo(doc, "\n".join(a3["primeras"]) + "\n...\n" +
              "\n".join(l for l in a3["lineas"]
                        if l.startswith(("tiempo total", "palabras unicas",
                                         "  union", "  ordenar", "  extraccion"))), 8)
espacio_captura(doc, "ejecución de la actividad 3 en la terminal")
pie(doc, "Figura 6. Ejecución de la actividad 3.")
parrafo(doc, "Primeras y últimas palabras de palabras.txt, ya ordenadas:",
        espacio_despues=2)
_palabras = (RAIZ / "actividad3" / "palabras.txt").read_text(encoding="utf-8").split("\n")
bloque_codigo(doc, "\n".join(_palabras[:6]) + "\n...\n" + "\n".join(_palabras[-4:]), 8)

seccion(doc, "4.5 Resultados", nivel=2)
tabla(doc, ["Métrica", "Valor"],
      [("Archivos procesados", a3["archivos procesados"]),
       ("Archivos con error", a3["archivos con error"]),
       ("Palabras únicas encontradas", a3_palabras),
       ("Extracción de palabras (suma de CPU)", f"{a3_extrae:.6f} s"),
       ("Unión del vocabulario", f"{a3_union:.6f} s"),
       ("Ordenar y escribir palabras.txt", f"{a3_orden:.6f} s"),
       ("Fase de limpieza (tiempo real)", f"{a3_fase:.6f} s"),
       ("Tiempo total de ejecución", f"{a3_ejec:.6f} s")],
      anchos=[3.4, 2.9])
parrafo(doc,
        "Sobre el tiempo de crear la lista de palabras: el programa no imprime una "
        "sola línea con ese total, sino sus componentes por separado. Crear el "
        f"vocabulario y ordenarlo toma {a3_union:.6f} s (unión) + {a3_orden:.6f} s "
        f"(ordenar y escribir) = {a3_union + a3_orden:.6f} s de tiempo real en el "
        f"proceso principal, más {a3_extrae:.6f} s de CPU de extracción repartidos "
        f"entre los {a3['procesos lanzados']} workers, que ocurren en paralelo con "
        "la limpieza y por eso no se suman al reloj.")

seccion(doc, "4.6 Casos de prueba", nivel=2)
tabla(doc, ["#", "Caso", "Entrada", "Resultado obtenido"],
      [(1, "Corpus completo", "505 archivos HTML", f"{a3_palabras} palabras únicas, 0 errores"),
       (2, "Orden alfabético", "palabras.txt", "Verificado: de \"a\" a las últimas entradas"),
       (3, "Sin repetidos", "Vocabulario unido con conjuntos", "Cada palabra aparece una sola vez"),
       (4, "Mayúsculas y minúsculas", "\"Casa\" y \"CASA\"", "Se cuentan como la misma palabra"),
       (5, "Carpeta inexistente", "/ruta/que/no/existe", "\"no es una carpeta\", código 2"),
       (6, "Carpeta sin HTML", "Solo notas.txt", "\"no se encontraron archivos HTML\", código 0"),
       (7, "Archivo sin permisos", "chmod 000", "Renglón ERROR, código 1")],
      anchos=[0.3, 1.7, 1.9, 2.4], tamano=9)

# ==========================================================================
#  COMPARATIVA Y CUMPLIMIENTO
# ==========================================================================
salto(doc)
seccion(doc, "5. Comparativa de la fase 1")
tabla(doc, ["", "Actividad 1", "Actividad 2", "Actividad 3"],
      [("Trabajo medido", "Abrir y leer", "Quitar etiquetas", "Quitar etiquetas + palabras"),
       ("Archivos", a1["archivos procesados"], a2["archivos procesados"], a3["archivos procesados"]),
       ("Errores", a1["archivos con error"], a2["archivos con error"], a3["archivos con error"]),
       ("Tiempo de la operación", f"{a1_apertura:.6f} s", f"{a2_fase:.6f} s", f"{a3_fase:.6f} s"),
       ("Tiempo total de ejecución", f"{a1_ejecucion:.6f} s", f"{a2_ejec:.6f} s", f"{a3_ejec:.6f} s"),
       ("Estrategia", "Secuencial", f"{a2['procesos lanzados']} procesos", f"{a3['procesos lanzados']} procesos"),
       ("Salida", "Log de tiempos", "505 archivos .txt", f"palabras.txt ({a3_palabras})")],
      anchos=[1.7, 1.5, 1.5, 1.6], tamano=9)
parrafo(doc,
        f"Abrir los archivos ({a1_apertura:.6f} s) es la parte barata: los datos ya "
        f"están en memoria. Quitar las etiquetas cuesta unas {a2_fase / a1_apertura:.0f} "
        "veces más, y eso ya con diez procesos trabajando en paralelo. Agregar la "
        "extracción de palabras encima casi no cambia el tiempo de la fase "
        f"({a3_fase:.6f} s frente a {a2_fase:.6f} s) porque se hace dentro del mismo "
        "worker sobre un texto que ya está en memoria; lo que sí crece es el tiempo "
        f"total de ejecución ({a3_ejec:.6f} s), por ordenar y escribir "
        f"{a3_palabras} palabras al final.")

seccion(doc, "6. Cumplimiento de los requerimientos")
tabla(doc, ["Requerimiento", "A1", "A2", "A3"],
      [("Mismo lenguaje en todas las actividades (Python 3)", "Sí", "Sí", "Sí"),
       ("La función recibe el nombre del archivo como parámetro", "Sí", "Sí", "Sí"),
       ("Log con el nombre aN_matricula.txt", "Sí", "Sí *", "Sí *"),
       ("Tiempo cronometrado por archivo", "Sí", "Sí", "Sí"),
       ("Tiempo total de la operación", "Sí", "Sí", "Parcial"),
       ("Tiempo total de ejecución", "Sí", "Sí", "Sí"),
       ("Genera el archivo de salida sin etiquetas", "—", "Sí", "Sí"),
       ("Lista de palabras ordenada alfabéticamente", "—", "—", "Sí"),
       ("Maneja datos de entrada inválidos", "Sí", "Sí", "Sí"),
       ("Imprime mensajes de error apropiados", "Sí", "Sí", "Sí"),
       ("Diagrama de flujo completo", "Sí", "Sí", "Sí"),
       ("Documentación interna del código", "Sí", "Sí", "Sí"),
       ("Casos de prueba documentados", "Sí", "Manual", "Manual"),
       ("Pruebas automatizadas", "14", "No", "No")],
      anchos=[3.9, 0.8, 0.8, 0.8], tamano=9)

seccion(doc, "6.1 Observaciones pendientes", nivel=2)
vineta(doc, "(*) El nombre del log hay que pasarlo por parámetro.",
       "Las actividades 2 y 3 guardan por defecto en a2.txt y a3.txt. Para cumplir "
       f"el nombre que pide el enunciado hay que ejecutarlas con "
       f"--tiempos a2_{MATRICULA}.txt y --tiempos a3_{MATRICULA}.txt, como se hizo "
       "en este reporte.")
vineta(doc, "La actividad 3 no imprime la línea de la plantilla.",
       "El enunciado pide \"tiempo total en crear el nuevo archivo\". El log de la "
       "actividad 3 reporta en su lugar \"tiempo total en eliminar las etiquetas "
       "HTML\" (heredado de la actividad 2) y desglosa por separado la extracción, "
       "la unión del vocabulario y el ordenamiento. Los datos están, pero el "
       "renglón exacto de la plantilla no aparece.")
vineta(doc, "Las actividades 2 y 3 no traen pruebas automatizadas.",
       "Los casos de prueba de este reporte se ejecutaron a mano. Convendría "
       "agregarles una suite como la de la actividad 1 antes de que el proyecto "
       "crezca.")

seccion(doc, "7. Conclusiones")
parrafo(doc,
        "La fase 1 deja la base del buscador terminada: de 505 documentos HTML en "
        f"disco se llega a una lista de {a3_palabras} palabras únicas ordenadas "
        "alfabéticamente, con los tiempos medidos en cada paso y sin un solo archivo "
        "fallido en las tres actividades.")
parrafo(doc,
        "La medición muestra dónde está el costo real: abrir los archivos es "
        "prácticamente gratis comparado con procesar su contenido. Por eso la "
        "actividad 1 se resuelve bien de forma secuencial, mientras que quitar "
        "etiquetas y extraer palabras justifican repartir el trabajo entre procesos.")
parrafo(doc,
        "Para las siguientes fases, la lista de palabras es la entrada natural del "
        "índice invertido: sobre ella se construirá la estructura que permita "
        "responder consultas sin volver a leer los documentos.")

# --- Anexos ---------------------------------------------------------------
salto(doc)
seccion(doc, "Anexo A. Código fuente de la actividad 1")
for ruta in ["actividad1/src/lector.py", "actividad1/src/main.py",
             "actividad1/tests/test_lector.py"]:
    anexar_codigo(doc, ruta)

salto(doc)
seccion(doc, "Anexo B. Código fuente de la actividad 2")
parrafo(doc, f"Autoría: {AUTOR_A23}.", tamano=10, cursiva=True, color=ROJO)
for ruta in ["actividad2/main.py", "actividad2/cargar.py",
             "actividad2/decodificar.py", "actividad2/limpiar.py"]:
    anexar_codigo(doc, ruta)

salto(doc)
seccion(doc, "Anexo C. Código fuente de la actividad 3")
parrafo(doc, f"Autoría: {AUTOR_A23}.", tamano=10, cursiva=True, color=ROJO)
for ruta in ["actividad3/main.py", "actividad3/cargar.py",
             "actividad3/decodificar.py", "actividad3/limpiar.py",
             "actividad3/extraer.py"]:
    anexar_codigo(doc, ruta)

doc.save(SALIDA)
print(f"Reporte generado en: {SALIDA}")
