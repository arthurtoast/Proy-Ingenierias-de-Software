# Actividad 3 — Generar la lista de palabras

> **Autoría:** este programa fue desarrollado por **[nombre del compañero]**, de otro
> equipo. Se integra aquí para documentar la fase 1 completa; el código es suyo.

Extrae las palabras del texto ya sin etiquetas, las junta sin repetidos y las escribe
ordenadas alfabéticamente en `palabras.txt`.

## Ejecución

```bash
python3 main.py ~/Downloads/Files --palabras palabras.txt --tiempos a3_AL02879741.txt
```

Igual que en la actividad 2, `--tiempos` es necesario para que el log se llame
`a3_matricula.txt` en vez de `a3.txt`.

| Argumento | Por defecto | Descripción |
|---|---|---|
| `carpeta` | (obligatorio) | Fólder con los archivos HTML |
| `--palabras` | `palabras.txt` | Lista de palabras únicas, una por línea |
| `--tiempos` | `a3.txt` | Informe de tiempos |
| `-w`, `--workers` | un proceso por núcleo | Procesos a lanzar |

Códigos de salida: `0` todo bien, `1` hubo archivos con error, `2` la ruta no es una carpeta.

## Estructura

Misma arquitectura de la actividad 2 más un módulo:

```
main.py           orquestador; une los vocabularios, ordena y escribe palabras.txt
cargar.py         ruta  -> bytes
decodificar.py    bytes -> str
limpiar.py        str   -> texto sin etiquetas
extraer.py        texto -> conjunto de palabras
diagramas/        diagrama de flujo general y detalle por archivo
```

Cada worker devuelve solo su vocabulario, no el texto: es mucho más pequeño y ya
viene sin repetidos.

## Qué cuenta como palabra

Una tira de letras de cualquier alfabeto, más las marcas que las acompañan. Quedan
fuera los dígitos, la puntuación, los símbolos y los caracteres que Unicode llama
letras o números pero van pegados a cifras (`ª`, `º`, `½`, `²`, `³`). Todo se pasa a
minúsculas, así que `Casa` y `CASA` son la misma palabra.

## Resultado de la corrida

505 archivos, 0 errores, **92,962 palabras únicas**:

```
union del vocabulario         : 0.032367 s
ordenar y escribir palabras   : 0.109178 s
tiempo total de ejecucion     : 0.379278 s
```

## Pendiente

El enunciado pide en la plantilla del log la línea *"tiempo total en crear el nuevo
archivo"*. El programa reporta en su lugar *"tiempo total en eliminar las etiquetas
HTML"* (heredada de la actividad 2) y desglosa por separado la extracción, la unión
del vocabulario y el ordenamiento. Los datos están, pero el renglón exacto de la
plantilla no aparece.
