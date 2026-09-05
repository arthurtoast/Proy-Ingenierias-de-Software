# Diagrama de flujo — Actividad 1

```mermaid
flowchart TD
    inicio([Inicio]) --> cronometro[Iniciar cronómetro de ejecución]
    cronometro --> args[Leer argumentos:<br/>carpeta, matrícula, salida]
    args --> valMat{¿Matrícula válida?}
    valMat -- No --> errMat[Imprimir error de matrícula] --> salida1([Salir con código 1])
    valMat -- Sí --> valCarpeta{¿La carpeta existe<br/>y es un fólder?}
    valCarpeta -- No --> errCarpeta[Imprimir error de ruta] --> salida1
    valCarpeta -- Sí --> listar[Listar archivos .html / .htm<br/>ordenados por nombre]
    listar --> hayArchivos{¿Hay archivos HTML?}
    hayArchivos -- No --> errVacio[Imprimir error de fólder vacío] --> salida1
    hayArchivos -- Sí --> cronoAper[Iniciar cronómetro de apertura]

    cronoAper --> ciclo{¿Quedan archivos<br/>por procesar?}
    ciclo -- Sí --> t1[Iniciar cronómetro del archivo]
    t1 --> abrir[Abrir y leer el archivo<br/>en modo binario]
    abrir --> ok{¿Se leyó<br/>correctamente?}
    ok -- Sí --> guardaOk[Guardar ruta, bytes y tiempo]
    ok -- No --> guardaErr[Guardar ruta, tiempo<br/>y mensaje de error]
    guardaOk --> ciclo
    guardaErr --> ciclo

    ciclo -- No --> totalAper[Detener cronómetro de apertura]
    totalAper --> totalEjec[Detener cronómetro de ejecución]
    totalEjec --> armar[Armar log: un renglón por archivo<br/>+ totales]
    armar --> escribir[Escribir salida/a1_matricula.txt]
    escribir --> escrito{¿Se pudo escribir?}
    escrito -- No --> errLog[Imprimir error de escritura] --> salida1
    escrito -- Sí --> imprimir[Imprimir totales y ruta del log]
    imprimir --> huboErr{¿Hubo archivos<br/>con error?}
    huboErr -- Sí --> salida2([Salir con código 2])
    huboErr -- No --> salida0([Salir con código 0])
```

## Correspondencia con el código

| Paso del diagrama | Implementación |
|---|---|
| Leer argumentos | `main.construir_parser` |
| Validar matrícula y carpeta | `main.main`, `lector.listar_archivos_html` |
| Listar archivos HTML | `lector.listar_archivos_html` |
| Ciclo de apertura y cronómetro por archivo | `lector.abrir_archivo` |
| Cronómetro total de apertura | `lector.abrir_todos` |
| Cronómetro total de ejecución | `main.main` |
| Armar y escribir el log | `main.construir_log`, `main.escribir_log` |
