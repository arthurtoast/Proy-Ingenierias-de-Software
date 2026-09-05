"""Genera el reporte de la Actividad 1 en formato Word (.docx).

Toma los datos reales de la última corrida (salida/a1_AL02879741.txt), el
diagrama de flujo (docs/diagrama_flujo.png) y el código fuente de src/ y
tests/, y arma el documento con todas las secciones del reporte.

Requiere python-docx:  python3 -m pip install python-docx
Uso:                   python3 docs/generar_reporte.py
Salida:                Reporte_A1_AL02879741.docx
"""

from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

RAIZ = Path(__file__).resolve().parent.parent
LOG = RAIZ / "salida" / "a1_AL02879741.txt"
DIAGRAMA = RAIZ / "docs" / "diagrama_flujo.png"
SALIDA = RAIZ / "Reporte_A1_AL02879741.docx"

MATRICULA = "AL02879741"
FECHA = "31 de agosto de 2026"
GRIS = RGBColor(0x59, 0x59, 0x59)
AZUL = RGBColor(0x1F, 0x38, 0x64)


# --------------------------------------------------------------------------
# Utilidades de formato
# --------------------------------------------------------------------------
def parrafo(documento, texto, tamano=11, cursiva=False, negrita=False,
            alineacion=None, color=None, espacio_despues=6):
    """Agrega un párrafo con formato básico y regresa el objeto párrafo."""
    p = documento.add_paragraph()
    p.paragraph_format.space_after = Pt(espacio_despues)
    if alineacion is not None:
        p.alignment = alineacion
    corrida = p.add_run(texto)
    corrida.font.size = Pt(tamano)
    corrida.italic = cursiva
    corrida.bold = negrita
    if color is not None:
        corrida.font.color.rgb = color
    return p


def bloque_codigo(documento, texto, tamano=8):
    """Agrega texto monoespaciado con fondo gris claro (código o salida)."""
    p = documento.add_paragraph()
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.line_spacing = 1.0
    sombreado = OxmlElement("w:shd")
    sombreado.set(qn("w:fill"), "F2F2F2")
    p._p.get_or_add_pPr().append(sombreado)
    for indice, linea in enumerate(texto.split("\n")):
        corrida = p.add_run(linea)
        corrida.font.name = "Consolas"
        corrida.font.size = Pt(tamano)
        corrida._element.rPr.rFonts.set(qn("w:eastAsia"), "Consolas")
        if indice < len(texto.split("\n")) - 1:
            corrida.add_break()
    return p


def tabla(documento, encabezados, filas, anchos=None):
    """Agrega una tabla con encabezado en negrita."""
    t = documento.add_table(rows=1, cols=len(encabezados))
    t.style = "Light Grid Accent 1"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for celda, titulo in zip(t.rows[0].cells, encabezados):
        celda.text = ""
        corrida = celda.paragraphs[0].add_run(titulo)
        corrida.bold = True
        corrida.font.size = Pt(9.5)
    for fila in filas:
        celdas = t.add_row().cells
        for celda, valor in zip(celdas, fila):
            celda.text = ""
            corrida = celda.paragraphs[0].add_run(str(valor))
            corrida.font.size = Pt(9.5)
    if anchos:
        for columna, ancho in enumerate(anchos):
            for fila_tabla in t.rows:
                fila_tabla.cells[columna].width = Inches(ancho)
    documento.add_paragraph().paragraph_format.space_after = Pt(4)
    return t


def espacio_captura(documento, descripcion, alto=2.6):
    """Inserta un recuadro vacío donde el alumno pegará la captura."""
    t = documento.add_table(rows=1, cols=1)
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    fila = t.rows[0]
    fila.height = Inches(alto)
    celda = fila.cells[0]
    celda.text = ""
    p = celda.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    corrida = p.add_run(f"[ Pega aquí la captura de pantalla: {descripcion} ]")
    corrida.italic = True
    corrida.font.size = Pt(10)
    corrida.font.color.rgb = GRIS
    return t


def pie_figura(documento, texto):
    parrafo(documento, texto, tamano=9, cursiva=True,
            alineacion=WD_ALIGN_PARAGRAPH.CENTER, color=GRIS, espacio_despues=12)


def titulo_seccion(documento, texto, nivel=1):
    encabezado = documento.add_heading(texto, level=nivel)
    for corrida in encabezado.runs:
        corrida.font.color.rgb = AZUL
    return encabezado


def anexar_archivo(documento, ruta_relativa):
    """Agrega el contenido de un archivo fuente al anexo de código."""
    titulo_seccion(documento, ruta_relativa, nivel=2)
    bloque_codigo(documento, (RAIZ / ruta_relativa).read_text(encoding="utf-8").rstrip())


# --------------------------------------------------------------------------
# Datos reales de la última corrida
# --------------------------------------------------------------------------
def leer_metricas():
    """Extrae del log los tiempos por archivo y los totales de la corrida."""
    lineas = LOG.read_text(encoding="utf-8").splitlines()
    tiempos = []
    primeras = []
    for linea in lineas:
        partes = linea.split()
        if len(partes) >= 2 and partes[0].endswith((".html", ".htm")):
            tiempos.append(float(partes[1]))
            if len(primeras) < 5:
                primeras.append(linea)
    totales = {}
    for linea in lineas:
        if linea.startswith("archivos procesados:"):
            totales["procesados"] = int(linea.split(":")[1])
        elif linea.startswith("archivos con error:"):
            totales["errores"] = int(linea.split(":")[1])
        elif linea.startswith("tiempo total en abrir"):
            totales["apertura"] = float(linea.split(":")[1].split()[0])
        elif linea.startswith("tiempo total de ejecucion"):
            totales["ejecucion"] = float(linea.split(":")[1].split()[0])
    return tiempos, primeras, lineas[-6:], totales


tiempos, primeras_lineas, ultimas_lineas, totales = leer_metricas()
promedio = sum(tiempos) / len(tiempos)

# --------------------------------------------------------------------------
# Documento
# --------------------------------------------------------------------------
documento = Document()
estilo = documento.styles["Normal"]
estilo.font.name = "Calibri"
estilo.font.size = Pt(11)

for seccion in documento.sections:
    seccion.top_margin = Inches(1.0)
    seccion.bottom_margin = Inches(1.0)
    seccion.left_margin = Inches(1.0)
    seccion.right_margin = Inches(1.0)

# --- Portada ---------------------------------------------------------------
for _ in range(4):
    documento.add_paragraph()
parrafo(documento, "Proyecto: Buscador de documentos HTML", tamano=14,
        alineacion=WD_ALIGN_PARAGRAPH.CENTER, color=GRIS)
titulo = documento.add_paragraph()
titulo.alignment = WD_ALIGN_PARAGRAPH.CENTER
corrida = titulo.add_run("Actividad 1\nApertura de archivos HTML y medición de tiempos")
corrida.bold = True
corrida.font.size = Pt(24)
corrida.font.color.rgb = AZUL
documento.add_paragraph()

datos = documento.add_table(rows=0, cols=2)
datos.alignment = WD_TABLE_ALIGNMENT.CENTER
for etiqueta, valor in [
    ("Alumno:", "[Escribe aquí tu nombre completo]"),
    ("Matrícula:", MATRICULA),
    ("Materia:", "CS13309 — [Nombre de la materia]"),
    ("Profesor:", "[Nombre del profesor]"),
    ("Lenguaje:", "Python 3"),
    ("Fecha:", FECHA),
]:
    celdas = datos.add_row().cells
    celdas[0].width = Inches(1.3)
    celdas[1].width = Inches(4.0)
    corrida_etiqueta = celdas[0].paragraphs[0].add_run(etiqueta)
    corrida_etiqueta.bold = True
    celdas[1].paragraphs[0].add_run(valor)

documento.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

# --- 1. Objetivo -----------------------------------------------------------
titulo_seccion(documento, "1. Objetivo")
parrafo(documento,
        "Desarrollar la primera etapa del proyecto del buscador: un programa que abra, de la "
        "manera más eficiente posible, todos los archivos HTML del corpus proporcionado, "
        "cronometre el tiempo que tarda en abrir cada archivo y registre los resultados en un "
        "archivo log de salida llamado a1_" + MATRICULA + ".txt. El programa debe medir "
        "también el tiempo total en abrir los archivos y el tiempo total de ejecución.")
parrafo(documento,
        "El lenguaje elegido es Python 3, que será el que se utilice durante todo el proyecto. "
        "La solución no usa dependencias externas: únicamente la biblioteca estándar.")

# --- 2. Descripción de la solución ----------------------------------------
titulo_seccion(documento, "2. Descripción de la solución")
parrafo(documento,
        "El programa se dividió en dos módulos para separar la lógica de la interfaz y poder "
        "probar la lógica de forma automatizada:")
tabla(documento,
      ["Archivo", "Responsabilidad"],
      [
          ("src/lector.py", "Lista los archivos HTML del fólder, abre cada uno y mide su tiempo de apertura."),
          ("src/main.py", "Interfaz de línea de comandos, validación de argumentos y generación del log."),
          ("tests/test_lector.py", "14 casos de prueba automatizados con unittest."),
          ("docs/", "Diagrama de flujo, documentación de casos de prueba y scripts de este reporte."),
          ("salida/", "Log generado: a1_" + MATRICULA + ".txt"),
      ],
      anchos=[1.7, 4.6])

titulo_seccion(documento, "2.1 Decisiones de diseño", nivel=2)
for encabezado, cuerpo in [
    ("Lectura binaria de un solo golpe.",
     "Cada archivo se abre con open(ruta, \"rb\") y se lee completo con un solo read(). Es la "
     "forma más eficiente de traer el documento a memoria: evita el costo de decodificar el "
     "texto y de iterar línea por línea. La decodificación e indexación se harán en etapas "
     "posteriores del proyecto, ya sobre los bytes en memoria."),
    ("Seis decimales en lugar de dos.",
     "La plantilla del enunciado muestra tiempos con dos decimales (0.10). En un equipo con "
     "disco de estado sólido cada archivo tarda menos de una centésima de segundo, por lo que "
     "todos los renglones aparecerían como 0.00 y la medición no aportaría información. Se "
     "conservó el formato de la plantilla pero con seis decimales."),
    ("Un archivo ilegible no detiene el programa.",
     "Si un archivo no se puede abrir (no existe, no hay permisos, etc.), el error se captura, "
     "se registra en el renglón correspondiente del log y la corrida continúa con los archivos "
     "restantes. Al final el programa reporta cuántos archivos fallaron."),
    ("El tiempo total no es la suma de los tiempos individuales.",
     "El tiempo total de apertura se mide con un cronómetro que envuelve todo el ciclo, por lo "
     "que incluye el trabajo del propio ciclo (recorrer la lista y construir los resultados). "
     "El tiempo total de ejecución envuelve además la lectura de argumentos, el listado del "
     "fólder y la escritura del log."),
    ("Orden alfabético.",
     "Los archivos se procesan ordenados por nombre para que la corrida sea reproducible y el "
     "log salga en el mismo orden que la plantilla del reporte."),
]:
    p = documento.add_paragraph(style="List Bullet")
    p.paragraph_format.space_after = Pt(6)
    corrida = p.add_run(encabezado + " ")
    corrida.bold = True
    corrida.font.size = Pt(11)
    corrida_cuerpo = p.add_run(cuerpo)
    corrida_cuerpo.font.size = Pt(11)

# --- 3. Diagrama de flujo --------------------------------------------------
documento.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
titulo_seccion(documento, "3. Diagrama de flujo")
documento.add_picture(str(DIAGRAMA), width=Inches(6.3))
documento.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
pie_figura(documento, "Figura 1. Diagrama de flujo del programa, incluyendo el manejo de errores.")

# --- 4. Instrucciones de ejecución ----------------------------------------
documento.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
titulo_seccion(documento, "4. Instrucciones de ejecución")
parrafo(documento, "Requisitos: Python 3.9 o superior. No se necesita instalar nada más.")
bloque_codigo(documento,
              "# Ejecutar el programa sobre el fólder con los archivos HTML\n"
              "python3 src/main.py --carpeta ~/Downloads/Files\n\n"
              "# Ejecutar los casos de prueba\n"
              "python3 -m unittest discover -s tests -v", tamano=9)
parrafo(documento, "Argumentos disponibles:", espacio_despues=4)
tabla(documento,
      ["Argumento", "Valor por defecto", "Descripción"],
      [
          ("--carpeta", "~/Downloads/Files", "Fólder que contiene los archivos HTML."),
          ("--matricula", MATRICULA, "Matrícula usada para nombrar el log de salida."),
          ("--salida", "salida/", "Fólder donde se escribe el archivo log."),
      ],
      anchos=[1.4, 1.8, 3.1])
parrafo(documento, "Códigos de salida del programa:", espacio_despues=4)
tabla(documento,
      ["Código", "Significado"],
      [
          ("0", "Todos los archivos se abrieron correctamente."),
          ("1", "Error irrecuperable: fólder inexistente, sin archivos HTML, o log no escribible."),
          ("2", "El programa terminó, pero uno o más archivos no se pudieron abrir."),
      ],
      anchos=[0.9, 5.4])

# --- 5. Evidencia de funcionamiento ---------------------------------------
documento.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
titulo_seccion(documento, "5. Evidencia de funcionamiento")

titulo_seccion(documento, "5.1 Corrida sobre el corpus completo", nivel=2)
parrafo(documento, "Salida en consola al procesar los "
        f"{totales['procesados']} archivos HTML del corpus:")
bloque_codigo(documento,
              "$ python3 src/main.py --carpeta ~/Downloads/Files\n"
              f"Abriendo {totales['procesados']} archivos HTML...\n"
              f"tiempo total en abrir los archivos: {totales['apertura']:.6f} segundos\n"
              f"tiempo total de ejecucion: {totales['ejecucion']:.6f} segundos\n"
              "Log generado en: .../salida/a1_" + MATRICULA + ".txt", tamano=9)
espacio_captura(documento, "ejecución del programa en la terminal")
pie_figura(documento, "Figura 2. Ejecución del programa sobre los "
           f"{totales['procesados']} archivos del corpus.")

titulo_seccion(documento, "5.2 Archivo log generado", nivel=2)
parrafo(documento, f"El programa genera el archivo a1_{MATRICULA}.txt con un renglón por "
        "archivo (ruta y tiempo de apertura) y los totales al final. Extracto:")
bloque_codigo(documento,
              "\n".join(primeras_lineas) + "\n...\n...\n" + "\n".join(ultimas_lineas), tamano=8)
espacio_captura(documento, f"archivo a1_{MATRICULA}.txt abierto")
pie_figura(documento, "Figura 3. Archivo log de salida.")

titulo_seccion(documento, "5.3 Manejo de datos inválidos", nivel=2)
parrafo(documento, "El programa valida la entrada e imprime mensajes de error claros sin "
        "interrumpirse con excepciones:")
bloque_codigo(documento,
              "$ python3 src/main.py --carpeta /ruta/que/no/existe\n"
              "Error: la ruta '/ruta/que/no/existe' no existe.\n\n"
              "$ python3 src/main.py --carpeta ~/Documentos/vacio\n"
              "Error: el fólder '/Users/.../vacio' no contiene archivos HTML.\n\n"
              "$ python3 src/main.py --matricula \"   \"\n"
              "Error: la matrícula no puede estar vacía.\n\n"
              "$ python3 src/main.py --carpeta ~/pruebas   # un archivo sin permisos\n"
              "Error al abrir /Users/.../002.html: [Errno 13] Permission denied", tamano=9)
espacio_captura(documento, "mensajes de error con entradas inválidas")
pie_figura(documento, "Figura 4. Validación de datos de entrada inválidos.")

titulo_seccion(documento, "5.4 Casos de prueba automatizados", nivel=2)
bloque_codigo(documento,
              "$ python3 -m unittest discover -s tests -v\n"
              "...\n"
              "Ran 14 tests in 0.006s\n\n"
              "OK", tamano=9)
espacio_captura(documento, "resultado de los 14 casos de prueba", alto=2.2)
pie_figura(documento, "Figura 5. Las 14 pruebas automatizadas pasan correctamente.")

# --- 6. Resultados ---------------------------------------------------------
documento.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
titulo_seccion(documento, "6. Resultados y medición de tiempos")
tabla(documento,
      ["Métrica", "Valor"],
      [
          ("Archivos HTML procesados", totales["procesados"]),
          ("Archivos con error", totales["errores"]),
          ("Tiempo mínimo de apertura", f"{min(tiempos):.6f} s"),
          ("Tiempo máximo de apertura", f"{max(tiempos):.6f} s"),
          ("Tiempo promedio por archivo", f"{promedio:.6f} s"),
          ("Suma de los tiempos individuales", f"{sum(tiempos):.6f} s"),
          ("Tiempo total en abrir los archivos", f"{totales['apertura']:.6f} s"),
          ("Tiempo total de ejecución", f"{totales['ejecucion']:.6f} s"),
      ],
      anchos=[3.4, 2.9])
parrafo(documento,
        f"El tiempo total en abrir los archivos ({totales['apertura']:.6f} s) es ligeramente "
        f"mayor que la suma de los tiempos individuales ({sum(tiempos):.6f} s) porque el "
        "cronómetro total incluye también el trabajo del ciclo que recorre la lista de "
        "archivos. A su vez, el tiempo total de ejecución "
        f"({totales['ejecucion']:.6f} s) agrega la lectura de argumentos, el listado del "
        "fólder y la escritura del archivo log.")
parrafo(documento,
        "Los tiempos individuales varían según el tamaño de cada documento HTML: entre el "
        f"archivo más rápido ({min(tiempos):.6f} s) y el más lento ({max(tiempos):.6f} s) hay dos "
        "órdenes de magnitud de diferencia, lo cual es consistente con una lectura secuencial "
        "del contenido completo de cada archivo.")

# --- 7. Casos de prueba ----------------------------------------------------
documento.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
titulo_seccion(documento, "7. Casos de prueba")
parrafo(documento, "Se documentaron 14 casos de prueba automatizados, todos con resultado "
        "satisfactorio.")

titulo_seccion(documento, "7.1 Entrada de datos normales", nivel=2)
tabla(documento,
      ["#", "Caso", "Entrada", "Resultado esperado"],
      [
          (1, "Listado de un fólder mixto", "HTML, TXT y una subcarpeta", "Solo los HTML, ordenados"),
          (2, "Extensiones alternas", "pagina.HTM", "Se reconoce como HTML"),
          (3, "Apertura de archivo válido", "001.html con contenido", "Lectura exitosa, bytes y tiempo correctos"),
          (4, "Archivo vacío", "vacio.html de 0 bytes", "Lectura exitosa con 0 bytes"),
          (5, "Tiempo total del ciclo", "3 archivos válidos", "El total cubre las aperturas individuales"),
          (6, "Corrida completa", "2 archivos válidos", "Código 0 y log con ambos totales"),
          (7, "Corpus real", f"{totales['procesados']} archivos", f"{totales['procesados']} renglones, 0 errores"),
      ],
      anchos=[0.3, 1.7, 1.9, 2.4])

titulo_seccion(documento, "7.2 Validación de datos inválidos", nivel=2)
tabla(documento,
      ["#", "Caso", "Entrada", "Resultado esperado"],
      [
          (8, "Ruta inexistente", "/ruta/que/no/existe", "Mensaje de error, código 1"),
          (9, "La ruta es un archivo", "Ruta de 001.html como carpeta", "Error: no es un fólder"),
          (10, "Fólder sin HTML", "Fólder solo con notas.txt", "Error: no contiene archivos HTML"),
          (11, "Matrícula vacía", "--matricula \"   \"", "Mensaje de error, código 1"),
          (12, "Archivo inexistente", "HTML que no existe", "Resultado con error, sin excepción"),
          (13, "Archivo sin permisos", "bloqueado.html (chmod 000)", "Resultado con Permission denied"),
          (14, "Un archivo falla entre varios", "1 válido + 1 sin permisos", "Código 2 y renglón ERROR en el log"),
      ],
      anchos=[0.3, 1.7, 1.9, 2.4])

# --- 8. Conclusiones -------------------------------------------------------
titulo_seccion(documento, "8. Conclusiones")
parrafo(documento,
        f"El programa cumple con el objetivo de la actividad: abre los {totales['procesados']} "
        "archivos HTML del corpus, mide el tiempo de apertura de cada uno y genera el archivo "
        f"log a1_{MATRICULA}.txt con el formato solicitado, incluyendo el tiempo total en abrir "
        "los archivos y el tiempo total de ejecución.")
parrafo(documento,
        "La lectura binaria completa resultó ser una estrategia eficiente: el corpus completo "
        f"se abre en {totales['apertura']:.6f} segundos, con un promedio de {promedio:.6f} "
        "segundos por archivo. Esta base servirá para las siguientes etapas del proyecto, donde "
        "sobre estos mismos bytes en memoria se realizará el análisis del HTML y la construcción "
        "del índice del buscador.")
parrafo(documento,
        "El manejo de errores por archivo (en lugar de detener todo el programa ante un archivo "
        "ilegible) es importante para las etapas siguientes, donde el corpus será más grande y "
        "un solo documento defectuoso no debe impedir procesar el resto.")

# --- Anexo -----------------------------------------------------------------
documento.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
titulo_seccion(documento, "Anexo A. Código fuente")
for ruta in ["src/lector.py", "src/main.py", "tests/test_lector.py"]:
    anexar_archivo(documento, ruta)

documento.save(SALIDA)
print(f"Reporte generado en: {SALIDA}")
