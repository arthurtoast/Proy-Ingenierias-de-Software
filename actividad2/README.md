# Actividad 2 — Remover las etiquetas HTML

> **Autoría:** este programa fue desarrollado por **[nombre del compañero]**, de otro
> equipo. Se integra aquí para documentar la fase 1 completa; el código es suyo.

Elimina las etiquetas HTML de cada documento del corpus y genera un `.txt` con el
texto limpio, cronometrando lo que tarda la eliminación de etiquetas en cada archivo.

## Ejecución

```bash
python3 main.py ~/Downloads/Files --salida salida --tiempos a2_AL02879741.txt
```

El parámetro `--tiempos` es necesario: por defecto el programa escribe `a2.txt`, y el
enunciado pide que el log se llame `a2_matricula.txt`.

| Argumento | Por defecto | Descripción |
|---|---|---|
| `carpeta` | (obligatorio) | Fólder con los archivos HTML |
| `--salida` | `salida` | Fólder donde se escriben los `.txt` sin etiquetas |
| `--tiempos` | `a2.txt` | Informe de tiempos |
| `-w`, `--workers` | un proceso por núcleo | Procesos a lanzar |
| `--carga-en-worker` | desactivado | Cada worker lee su archivo en vez de recibir los bytes |
| `--limite-mb` | 20 | Tamaño máximo por archivo |
| `--timeout` | 30 | Segundos máximos por archivo |

Códigos de salida: `0` todo bien, `1` hubo archivos con error, `2` la ruta no es una carpeta.

## Estructura

```
main.py           orquestador: reparte el trabajo entre procesos y escribe el informe
cargar.py         ruta  -> bytes
decodificar.py    bytes -> str
limpiar.py        str   -> texto sin etiquetas   (esto es lo que se cronometra)
diagramas/        diagrama de flujo general y detalle por archivo
```

Los tres módulos de apoyo son funciones puras: sin estado, sin importarse entre sí,
devuelven `(resultado, error)` y no lanzan excepciones. `main.py` es el único que
decide el paralelismo.

## Resultado de la corrida

505 archivos del corpus, 0 errores, en una máquina de 10 núcleos:

```
tiempo total en eliminar las etiquetas HTML: 0.254410 segundos
tiempo total de ejecucion: 0.257614 segundos
```

La suma de CPU de la limpieza es 0.600868 s repartida entre 10 procesos, por eso el
tiempo real de la fase es menor que esa suma.

Los 505 `.txt` generados (8.4 MB) no se versionan: se regeneran al correr el programa.
El log `a2_AL02879741.txt` sí está en el repo.
