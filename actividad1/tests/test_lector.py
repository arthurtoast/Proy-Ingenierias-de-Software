"""Casos de prueba de la Actividad 1.

Ejecutar desde la raíz del repositorio:
    python3 -m unittest discover -s tests -v
"""

import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import main  # noqa: E402
from lector import ErrorLectura, abrir_archivo, abrir_todos, listar_archivos_html  # noqa: E402

HTML_DEMO = "<html><body><p>documento de prueba</p></body></html>"


class PruebaListarArchivos(unittest.TestCase):
    """Datos de entrada válidos e inválidos para el listado del fólder."""

    def test_lista_solo_html_y_en_orden(self):
        with TemporaryDirectory() as temporal:
            carpeta = Path(temporal)
            (carpeta / "002.html").write_text(HTML_DEMO)
            (carpeta / "001.html").write_text(HTML_DEMO)
            (carpeta / "notas.txt").write_text("no es html")
            (carpeta / "subcarpeta").mkdir()

            archivos = listar_archivos_html(carpeta)

            self.assertEqual([ruta.name for ruta in archivos], ["001.html", "002.html"])

    def test_acepta_extension_htm_y_mayusculas(self):
        with TemporaryDirectory() as temporal:
            carpeta = Path(temporal)
            (carpeta / "pagina.HTM").write_text(HTML_DEMO)

            self.assertEqual(len(listar_archivos_html(carpeta)), 1)

    def test_ruta_inexistente(self):
        with self.assertRaises(ErrorLectura):
            listar_archivos_html(Path("/ruta/que/no/existe"))

    def test_ruta_es_archivo_no_folder(self):
        with TemporaryDirectory() as temporal:
            archivo = Path(temporal) / "001.html"
            archivo.write_text(HTML_DEMO)

            with self.assertRaises(ErrorLectura):
                listar_archivos_html(archivo)

    def test_folder_sin_html(self):
        with TemporaryDirectory() as temporal:
            (Path(temporal) / "notas.txt").write_text("no es html")

            with self.assertRaises(ErrorLectura):
                listar_archivos_html(Path(temporal))


class PruebaAbrirArchivo(unittest.TestCase):
    """Apertura individual: caso normal, archivo vacío y archivo ilegible."""

    def test_archivo_valido(self):
        with TemporaryDirectory() as temporal:
            ruta = Path(temporal) / "001.html"
            ruta.write_text(HTML_DEMO)

            resultado = abrir_archivo(ruta)

            self.assertTrue(resultado.exitoso)
            self.assertEqual(resultado.bytes_leidos, len(HTML_DEMO))
            self.assertGreater(resultado.segundos, 0)

    def test_archivo_vacio(self):
        with TemporaryDirectory() as temporal:
            ruta = Path(temporal) / "vacio.html"
            ruta.write_text("")

            resultado = abrir_archivo(ruta)

            self.assertTrue(resultado.exitoso)
            self.assertEqual(resultado.bytes_leidos, 0)

    def test_archivo_inexistente_no_detiene_el_programa(self):
        resultado = abrir_archivo(Path("/ruta/que/no/existe/001.html"))

        self.assertFalse(resultado.exitoso)
        self.assertIn("No such file", resultado.error)

    def test_archivo_sin_permisos_de_lectura(self):
        with TemporaryDirectory() as temporal:
            ruta = Path(temporal) / "bloqueado.html"
            ruta.write_text(HTML_DEMO)
            ruta.chmod(0o000)
            try:
                resultado = abrir_archivo(ruta)
            finally:
                ruta.chmod(0o600)

            self.assertFalse(resultado.exitoso)


class PruebaAbrirTodos(unittest.TestCase):
    def test_tiempo_total_cubre_todas_las_aperturas(self):
        with TemporaryDirectory() as temporal:
            carpeta = Path(temporal)
            for indice in range(1, 4):
                (carpeta / f"00{indice}.html").write_text(HTML_DEMO)

            archivos = listar_archivos_html(carpeta)
            resultados, total = abrir_todos(archivos)

            self.assertEqual(len(resultados), 3)
            self.assertTrue(all(resultado.exitoso for resultado in resultados))
            self.assertGreaterEqual(total, sum(r.segundos for r in resultados) * 0.9)


class PruebaProgramaCompleto(unittest.TestCase):
    """Pruebas de extremo a extremo sobre `main`, incluyendo el log de salida."""

    def test_corrida_exitosa_genera_log(self):
        with TemporaryDirectory() as entrada, TemporaryDirectory() as salida:
            (Path(entrada) / "001.html").write_text(HTML_DEMO)
            (Path(entrada) / "002.html").write_text(HTML_DEMO)

            codigo = main.main(
                ["--carpeta", entrada, "--salida", salida, "--matricula", "AL02879741"]
            )

            log = Path(salida) / "a1_AL02879741.txt"
            contenido = log.read_text()
            self.assertEqual(codigo, 0)
            self.assertTrue(log.exists())
            self.assertIn("001.html", contenido)
            self.assertIn("archivos procesados: 2", contenido)
            self.assertIn("archivos con error: 0", contenido)
            self.assertIn("tiempo total en abrir los archivos:", contenido)
            self.assertIn("tiempo total de ejecucion:", contenido)

    def test_folder_invalido_regresa_codigo_1(self):
        with TemporaryDirectory() as salida:
            codigo = main.main(
                ["--carpeta", "/ruta/que/no/existe", "--salida", salida]
            )

            self.assertEqual(codigo, 1)

    def test_matricula_vacia_regresa_codigo_1(self):
        with TemporaryDirectory() as entrada, TemporaryDirectory() as salida:
            (Path(entrada) / "001.html").write_text(HTML_DEMO)

            codigo = main.main(
                ["--carpeta", entrada, "--salida", salida, "--matricula", "   "]
            )

            self.assertEqual(codigo, 1)

    def test_archivo_ilegible_regresa_codigo_2_y_lo_registra(self):
        with TemporaryDirectory() as entrada, TemporaryDirectory() as salida:
            bueno = Path(entrada) / "001.html"
            bueno.write_text(HTML_DEMO)
            malo = Path(entrada) / "002.html"
            malo.write_text(HTML_DEMO)
            malo.chmod(0o000)
            try:
                codigo = main.main(["--carpeta", entrada, "--salida", salida])
            finally:
                malo.chmod(0o600)

            contenido = (Path(salida) / "a1_AL02879741.txt").read_text()
            self.assertEqual(codigo, 2)
            self.assertIn("archivos con error: 1", contenido)
            self.assertIn("ERROR:", contenido)


if __name__ == "__main__":
    unittest.main()
