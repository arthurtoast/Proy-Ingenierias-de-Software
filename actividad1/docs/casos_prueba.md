# Casos de prueba — Actividad 1

Ejecución: `python3 -m unittest discover -s tests -v` (14 pruebas, todas OK).

## Entrada de datos normales

| # | Caso | Entrada | Resultado esperado | Prueba |
|---|---|---|---|---|
| 1 | Listado de un fólder mixto | fólder con `001.html`, `002.html`, `notas.txt` y una subcarpeta | solo los dos HTML, ordenados | `test_lista_solo_html_y_en_orden` |
| 2 | Extensiones alternas | archivo `pagina.HTM` | se reconoce como HTML | `test_acepta_extension_htm_y_mayusculas` |
| 3 | Apertura de un archivo válido | `001.html` con contenido | lectura exitosa, bytes correctos, tiempo > 0 | `test_archivo_valido` |
| 4 | Archivo vacío | `vacio.html` de 0 bytes | lectura exitosa con 0 bytes (no es error) | `test_archivo_vacio` |
| 5 | Tiempo total del ciclo | 3 archivos válidos | el total cubre las aperturas individuales | `test_tiempo_total_cubre_todas_las_aperturas` |
| 6 | Corrida completa | 2 archivos válidos | código 0 y log con renglones y ambos totales | `test_corrida_exitosa_genera_log` |
| 7 | Corpus real | 505 archivos de `~/Downloads/Files` | 505 renglones, 0 errores, log generado | corrida manual (ver README) |

## Validación de datos inválidos

| # | Caso | Entrada | Resultado esperado | Prueba |
|---|---|---|---|---|
| 8 | Ruta inexistente | `/ruta/que/no/existe` | error "la ruta no existe", código 1 | `test_ruta_inexistente`, `test_folder_invalido_regresa_codigo_1` |
| 9 | La ruta es un archivo | ruta de `001.html` como carpeta | error "no es un fólder" | `test_ruta_es_archivo_no_folder` |
| 10 | Fólder sin HTML | fólder solo con `notas.txt` | error "no contiene archivos HTML" | `test_folder_sin_html` |
| 11 | Matrícula vacía | `--matricula "   "` | mensaje de error, código 1 | `test_matricula_vacia_regresa_codigo_1` |
| 12 | Archivo inexistente | ruta directa a un HTML que no existe | resultado con error, sin excepción | `test_archivo_inexistente_no_detiene_el_programa` |
| 13 | Archivo sin permisos | `bloqueado.html` con permisos `000` | resultado con "Permission denied" | `test_archivo_sin_permisos_de_lectura` |
| 14 | Un archivo falla entre varios | 1 válido + 1 sin permisos | código 2, log con `archivos con error: 1` y renglón `ERROR:` | `test_archivo_ilegible_regresa_codigo_2_y_lo_registra` |

## Mensajes de error

```
Error: la ruta '/ruta/que/no/existe' no existe.
Error: la ruta '/.../001.html' no es un fólder.
Error: el fólder '/...' no contiene archivos HTML.
Error: la matrícula no puede estar vacía.
Error al abrir /.../002.html: [Errno 13] Permission denied: '/.../002.html'
Error: no se pudo escribir el log (...).
```
