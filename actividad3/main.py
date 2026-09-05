#!/usr/bin/env python3
"""
MAIN - Orquestador. Es el unico archivo que importa a los demas, de
principio a fin del programa.

    main.py
      |-- cargar.py        ruta   -> bytes    (se ejecuta en el main)
      |-- decodificar.py   bytes  -> str      (en el worker)
      |-- limpiar.py       str    -> texto    (en el worker, CRONOMETRADO)
      `-- extraer.py       texto  -> palabras (en el worker)

Los cuatro modulos son funciones puras, sin estado y sin importarse
entre si. Todas devuelven (resultado, error) y ninguna lanza
excepciones. Ninguno lanza procesos ni hilos: el paralelismo lo decide
este archivo.

QUE HACE, EN ORDEN
    1. Recorre la carpeta y ordena los archivos de mayor a menor,
       consultando solo su tamano.
    2. Lanza un proceso por nucleo y mantiene una ventana de unos pocos
       archivos en vuelo: carga uno, lo envia, y en cuanto un worker
       devuelve un resultado carga y envia el siguiente.
    3. Cada worker decodifica su archivo, le quita las etiquetas y saca
       sus palabras. Solo la eliminacion de etiquetas entra en la
       columna de tiempos por archivo.
    4. El worker devuelve SOLO su vocabulario, no el texto. Es mucho
       mas pequeno y ya viene sin repetidos.
    5. El main junta los vocabularios, escribe la lista de palabras
       unicas y el informe de tiempos.

LA MEMORIA SE LIBERA SOBRE LA MARCHA
    Los bytes de un archivo dejan de estar en memoria en cuanto llega su
    resultado. Hasta ese momento hay dos referencias vivas: la del padre,
    que se suelta nada mas enviar, y la que el ejecutor retiene para
    poder reintentar, que se libera al recibir el resultado. Por eso el
    pico de memoria depende del tamano de la ventana y no del de la
    carpeta.

PROCESOS Y NO HILOS
    str.decode() y el modulo re no liberan el GIL, asi que N hilos se
    turnarian en un solo nucleo en vez de repartirse el trabajo.

    Los procesos ademas aislan los fallos: un archivo que agote la
    memoria o cuelgue una expresion regular mata al worker que le toco,
    el grupo levanta otro y el lote continua. Con hilos se caeria el
    programa entero.

    Tampoco se usan colas por etapa (un grupo cargando, otro
    decodificando, otro limpiando): la eliminacion de etiquetas se lleva
    la mayor parte del trabajo, asi que encadenar tres etapas queda
    limitado por esa unica etapa, mientras que repartir por archivo
    escala con el numero de nucleos. Y cada transicion entre etapas
    obligaria a mover los datos de un proceso a otro.

POR QUE CADA WORKER HACE LA CADENA ENTERA
    La alternativa seria dedicar un nucleo a leer, otro a extraer
    palabras y el resto a decodificar y limpiar. Con los tiempos reales
    de este corpus:

        cargar             1,0 %
        decodificar        7,8 %
        limpiar           56,5 %
        extraer palabras  34,6 %

    un nucleo por etapa tiene un techo de x1,77 -- lo que marca la etapa
    mas lenta -- por muchos nucleos que haya. Repartiendo por archivo el
    techo es el numero de nucleos. Ademas, cada frontera entre etapas
    obligaria a mover el texto de un proceso a otro.

    Que los workers "ayuden" a extraer cuando terminen de limpiar sale
    solo con este diseno: cada uno hace las cuatro etapas de SU archivo,
    asi que quien acaba antes coge el siguiente archivo sin que nadie
    tenga que coordinar nada.

EL ORDEN DEL REPARTO
    Los archivos grandes se envian primero (Longest Processing Time
    first). Con tamanos dispares, dejar el mayor para el final tiene a
    los demas nucleos parados esperandolo.

Escrito para macOS. Sale con 0 si todo fue bien, 1 si hubo errores y 2 si
la ruta no es una carpeta.
"""

import argparse
import os
import signal
import sys
import threading
import time
from concurrent.futures import (FIRST_COMPLETED, ProcessPoolExecutor,
                                wait)

# --- Unico punto de importacion de los modulos --------------------------
import cargar
import decodificar
import extraer
import limpiar

# --- Valores por defecto. Cambiar aqui cambia el comportamiento del
#     programa sin tener que pasar opciones por la linea de ordenes.
ARCHIVO_PALABRAS = "palabras.txt"   # las palabras unicas, una por linea
ARCHIVO_TIEMPOS = "a3.txt"          # informe con los tiempos por archivo

EXTENSIONES = (".html", ".htm", ".xhtml")   # extensiones que se procesan
TIMEOUT_ARCHIVO = 30                        # segundos maximos por archivo
LIMITE_MB_ARCHIVO = 20                      # tamano maximo de un archivo
LIMITE_MB_LOTE = 2048                       # memoria para los archivos en vuelo
LIMITE_MEM_WORKER = 4 * 1024 * 1024 * 1024  # espacio de direcciones por worker


# ======================================================================
#  Worker
# ======================================================================

def _init_worker(limite_mem):
    """Se ejecuta una vez al arrancar cada proceso hijo.

    Pone un techo al espacio de direcciones para que una asignacion
    desbocada acabe en un MemoryError que el propio worker captura, en
    vez de dejar que el sistema empiece a matar procesos. Y desactiva
    los volcados de memoria, que escribirian a disco el contenido de los
    documentos que estabamos procesando.
    """
    try:
        import resource
        resource.setrlimit(resource.RLIMIT_AS, (limite_mem, limite_mem))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    except (ValueError, OSError):
        pass


class _Timeout(Exception):
    pass


def _alarma(signum, frame):
    raise _Timeout()


def procesar(nombre, datos, timeout, raiz=None, limite=0):
    """Hace la cadena entera sobre un archivo. Corre en el proceso hijo.

    `datos` son los bytes que el main ya cargo. Si en su lugar llega una
    ruta (una str), el worker lee el archivo el mismo: es el modo
    --carga-en-worker, que evita mandar los bytes por la tuberia.

    Devuelve siempre un diccionario, nunca lanza: un archivo malo no
    puede tumbar el lote. Lo unico que viaja de vuelta es el vocabulario
    del archivo, ya sin repetidos y unido en una sola cadena; el texto
    limpio se queda aqui y se descarta.
    """
    r = {"nombre": nombre, "estado": "ok", "error": "", "vacio": False,
         "pid": os.getpid(), "bytes": 0, "palabras": "",
         "t_limpieza": 0.0, "t_extraccion": 0.0}

    if isinstance(datos, str):
        datos, err = cargar.cargar(datos, raiz=raiz, max_bytes=limite)
        if err:
            r.update(estado="error", error=f"cargar: {err}")
            return r

    # Red de seguridad por si algun paso se queda colgado. La alarma solo
    # funciona en el hilo principal de un proceso, que es donde corre esto.
    usar_alarma = threading.current_thread() is threading.main_thread()
    if usar_alarma:
        signal.signal(signal.SIGALRM, _alarma)
        signal.setitimer(signal.ITIMER_REAL, timeout)

    r["bytes"] = len(datos)

    try:
        # --- Decodificar: no se cronometra ---------------------------
        texto, err, _codec = decodificar.decodificar(datos)
        if err:
            r.update(estado="error", error=f"decodificar: {err}")
            return r

        # --- Quitar etiquetas: ESTO ES LO QUE SE MIDE ----------------
        t0 = time.perf_counter()
        limpio, err = limpiar.limpiar(texto)
        r["t_limpieza"] = time.perf_counter() - t0
        # --------------------------------------------------------------

        if err:
            r.update(estado="error", error=f"limpiar: {err}")
            return r

        r["vacio"] = limpiar.esta_vacio(limpio)

        # --- Extraer las palabras: se cronometra aparte ---------------
        # No entra en la columna por archivo del informe, que sigue
        # midiendo lo que dice su cabecera: quitar las etiquetas.
        t0 = time.perf_counter()
        palabras, err = extraer.extraer(limpio)
        if err:
            r.update(estado="error", error=f"extraer: {err}")
            return r
        # El texto limpio ya no hace falta: se suelta antes de volver.
        del limpio
        r["palabras"] = extraer.a_texto(palabras)
        r["t_extraccion"] = time.perf_counter() - t0
        return r

    except _Timeout:
        r.update(estado="timeout", error=f"excedio {timeout}s")
        return r
    except MemoryError:
        r.update(estado="error", error="sin memoria (limite del worker)")
        return r
    except Exception as e:
        r.update(estado="error", error=f"{type(e).__name__}: {e}")
        return r
    finally:
        if usar_alarma:
            signal.setitimer(signal.ITIMER_REAL, 0)


# ======================================================================
#  Orquestacion: todo lo que sigue ocurre en el main
# ======================================================================

def descubrir(raiz):
    """Busca los HTML bajo la carpeta, sin seguir symlinks de directorio."""
    encontrados = []
    for dirpath, dirnames, filenames in os.walk(raiz, followlinks=False):
        dirnames[:] = [d for d in dirnames
                       if not os.path.islink(os.path.join(dirpath, d))]
        for f in filenames:
            if f.lower().endswith(EXTENSIONES):
                encontrados.append(os.path.join(dirpath, f))
    return sorted(encontrados)


def nombre_corto(ruta, raiz):
    """Nombre para el informe: Files/503.html en vez de la ruta absoluta.

    Se conserva la ruta interna (Files/2024/007.html) para que no haya
    dos lineas iguales cuando hay subcarpetas.
    """
    rel = os.path.relpath(ruta, raiz)
    return os.path.basename(raiz) + "/" + rel


def repartir(ex, archivos, raiz, args, fallos, vocabulario):
    """Carga y reparte con una ventana limitada de archivos en vuelo.

    En vez de cargar la carpeta entera y luego repartirla, se mantienen
    como mucho unos pocos archivos vivos a la vez: se envia uno, y en
    cuanto un worker devuelve un resultado se carga y se envia el
    siguiente. Los bytes de un archivo ya procesado salen de la memoria
    en cuanto llega su resultado, porque para entonces nadie los
    referencia: ni la lista del padre (se suelta al enviar) ni el
    ejecutor (suelta los argumentos al recibir el resultado).

    El pico de memoria pasa a depender de la ventana, no del tamano de
    la carpeta: 500 archivos de 5 MB ya no son 2,5 GB.

    El orden sigue siendo de mayor a menor: los tamanos se consultan
    antes con os.path.getsize(), que no lee el contenido.

    Las palabras de cada archivo se van juntando en `vocabulario` segun
    llegan, y el resultado del worker se descarta enseguida: asi el
    vocabulario global crece pero no se acumulan copias por archivo.

    Devuelve (filas, bytes_leidos, segundos_de_lectura, segundos_de_union).
    """
    limite = args.limite_mb * 1024 * 1024
    limite_ram = args.ram_mb * 1024 * 1024
    ventana = max(2, args.workers_reales * 3)

    filas = []
    pendientes = {}          # future -> ruta
    bytes_vivos = 0          # bytes que el ejecutor aun retiene
    bytes_leidos = 0
    t_lectura = 0.0
    t_union = 0.0
    restantes = iter(archivos)
    hechos = 0
    total = len(archivos)

    def enviar_siguiente():
        """Carga y envia un archivo. False si ya no queda ninguno."""
        nonlocal bytes_vivos, bytes_leidos, t_lectura
        for ruta in restantes:
            if args.carga_en_worker:
                # El worker lee el archivo; aqui solo viaja la ruta.
                fut = ex.submit(procesar, nombre_corto(ruta, raiz), ruta,
                                args.timeout, raiz, limite)
                pendientes[fut] = ruta
                return True

            t0 = time.perf_counter()
            datos, err = cargar.cargar(ruta, raiz=raiz, max_bytes=limite)
            t_lectura += time.perf_counter() - t0
            if err:
                fallos.append((ruta, err))
                continue
            bytes_leidos += len(datos)
            bytes_vivos += len(datos)
            fut = ex.submit(procesar, nombre_corto(ruta, raiz), datos,
                            args.timeout, raiz, limite)
            pendientes[fut] = ruta
            # El padre suelta su copia aqui. A partir de este punto la
            # unica referencia viva es la que retiene el ejecutor hasta
            # que el worker devuelva el resultado.
            del datos
            return True
        return False

    # Llenar la ventana inicial.
    while len(pendientes) < ventana and bytes_vivos < limite_ram:
        if not enviar_siguiente():
            break

    while pendientes:
        listos, _ = wait(list(pendientes), return_when=FIRST_COMPLETED)
        for fut in listos:
            ruta = pendientes.pop(fut)
            hechos += 1
            try:
                r = fut.result()
            except Exception as e:
                # El worker murio del todo. Se anota y el lote sigue.
                fallos.append((ruta, f"worker muerto: {e}"))
            else:
                if r["estado"] != "ok":
                    fallos.append((ruta, r["error"]))
                else:
                    # Se une el vocabulario del archivo y se suelta su
                    # copia antes de seguir. El reloj cuenta aqui, que es
                    # donde ocurre el trabajo: partir la cadena que llego
                    # del worker y meter sus palabras en el conjunto.
                    if r["palabras"]:
                        t0 = time.perf_counter()
                        vocabulario.update(extraer.de_texto(r["palabras"]))
                        t_union += time.perf_counter() - t0
                    r["palabras"] = ""
                    r["ruta"] = ruta
                    filas.append(r)
                    bytes_vivos = max(0, bytes_vivos - r.get("bytes", 0))
            print(f"\r  procesados {hechos}/{total}", end="", flush=True)

        # Rellenar los huecos que acaban de quedar libres.
        while len(pendientes) < ventana and bytes_vivos < limite_ram:
            if not enviar_siguiente():
                break

    return filas, bytes_leidos, t_lectura, t_union


def escribir_tiempos(destino, filas, fallos, suma_cpu, t_fase, t_total,
                     info, raiz):
    """Escribe el informe: cada archivo con su tiempo enfrente y los totales."""
    cortos = [nombre_corto(f["ruta"], raiz) for f in filas]
    cortos_fallo = [nombre_corto(r, raiz) for r, _ in fallos]
    ancho = max([len(n) for n in cortos + cortos_fallo] + [24])

    lineas = []
    for f, nombre in zip(filas, cortos):
        lineas.append(f"{nombre.ljust(ancho)}  {f['t_limpieza']:12.6f}")
    for (_ruta, err), nombre in zip(fallos, cortos_fallo):
        lineas.append(f"{nombre.ljust(ancho)}  {'ERROR':>12}  ({err})")

    lineas += [
        "",
        f"tiempo total en eliminar las etiquetas HTML: {t_fase:.6f} segundos",
        f"tiempo total de ejecucion: {t_total:.6f} segundos",
        "",
        "-" * (ancho + 16),
        f"archivos procesados            : {len(filas)}",
        f"archivos con error             : {len(fallos)}",
        f"archivos vacios                : "
        f"{sum(1 for f in filas if f['vacio'])}",
        f"nucleos de la maquina          : {info['nucleos']}",
        f"procesos lanzados              : {info['workers']}",
        f"archivos en vuelo a la vez     : {info['ventana']}"
        f"   (limita el pico de memoria)",
        f"palabras unicas encontradas    : {info['palabras']:,}"
        f"   -> {info['archivo_palabras']}",
        "",
        "desglose:",
        f"  lectura de disco (sumada)     : {info['t_carga']:12.6f} s"
        f"   ({info['mb']:.1f} MB, intercalada con el proceso)",
        # Suma de lo que trabajo cada nucleo. Es mayor que el tiempo real
        # porque varios nucleos trabajan a la vez: N nucleos durante un
        # segundo consumen N segundos de CPU en un segundo de reloj.
        f"  limpieza pura (suma de CPU)   : {suma_cpu:12.6f} s"
        f"   repartida entre {info['workers']} procesos",
        f"  extraccion pura (suma de CPU) : {info['suma_extraccion']:12.6f} s"
        f"   repartida entre {info['workers']} procesos",
        f"  fase de limpieza (tiempo real): {t_fase:12.6f} s"
        f"   (incluye decodificar y extraer)",
        f"  union del vocabulario         : {info['t_union']:12.6f} s",
        f"  ordenar y escribir palabras   : {info['t_escritura']:12.6f} s",
        f"  sobrecoste de reparto         : {info['t_ipc']:12.6f} s",
        f"  ejecucion completa            : {t_total:12.6f} s",
    ]

    # Cuanto trabajo acabo haciendo cada proceso. Sale de los tiempos ya
    # medidos, sin coste anadido. Si un proceso tiene una media por
    # archivo muy distinta de los demas, es que su nucleo no rinde igual.
    grupos = {}
    for f in filas:
        g = grupos.setdefault(f["pid"], {"n": 0, "t": 0.0})
        g["n"] += 1
        g["t"] += f["t_limpieza"]

    if len(grupos) > 1:
        lineas += [
            "",
            "reparto real por proceso:",
            f"  {'pid':<12}{'archivos':>10}{'suma':>15}{'media/archivo':>16}",
        ]
        for pid, g in sorted(grupos.items(), key=lambda kv: -kv[1]["t"]):
            media = g["t"] / g["n"] if g["n"] else 0
            lineas.append(f"  {pid:<12}{g['n']:>10}{g['t']:>14.6f}s"
                          f"{media:>15.6f}s")

    with open(destino, "w", encoding="utf-8") as fh:
        fh.write("\n".join(l for l in lineas if l != "") + "\n")


def main(argv=None):
    t_programa = time.perf_counter()

    nucleos = os.cpu_count() or 1
    ap = argparse.ArgumentParser(
        description="Extrae el texto de los HTML de una carpeta")
    ap.add_argument("carpeta")
    ap.add_argument("--palabras", default=ARCHIVO_PALABRAS,
                    help=f"lista de palabras unicas "
                         f"(por defecto: {ARCHIVO_PALABRAS})")
    ap.add_argument("--tiempos", default=ARCHIVO_TIEMPOS,
                    help=f"informe de tiempos (por defecto: {ARCHIVO_TIEMPOS})")
    ap.add_argument("-w", "--workers", type=int, default=nucleos,
                    help="procesos; por defecto uno por nucleo")
    ap.add_argument("--reservar", type=int, default=0, metavar="N",
                    help="dejar N nucleos libres para el resto del sistema")
    ap.add_argument("--carga-en-worker", action="store_true",
                    help="cada worker lee su archivo en vez de recibir los "
                         "bytes del main: evita el paso por la tuberia")
    ap.add_argument("--limite-mb", type=int, default=LIMITE_MB_ARCHIVO,
                    help=f"tamano maximo por archivo "
                         f"(por defecto {LIMITE_MB_ARCHIVO})")
    ap.add_argument("--ram-mb", type=int, default=LIMITE_MB_LOTE,
                    help=f"memoria para los archivos en vuelo "
                         f"(por defecto {LIMITE_MB_LOTE})")
    ap.add_argument("--timeout", type=int, default=TIMEOUT_ARCHIVO,
                    help="segundos maximos por archivo (por defecto 30)")
    args = ap.parse_args(argv)

    raiz = os.path.realpath(args.carpeta)
    if not os.path.isdir(raiz):
        print(f"error: '{args.carpeta}' no es una carpeta", file=sys.stderr)
        return 2

    archivos = descubrir(raiz)
    if not archivos:
        print("no se encontraron archivos HTML")
        return 0

    # Nunca mas procesos que nucleos, ni mas que archivos que procesar.
    pedidos = max(1, args.workers - max(0, args.reservar))
    workers = max(1, min(pedidos, nucleos, len(archivos)))

    print(f"{len(archivos)} archivos")
    print(f"  nucleos de la maquina : {nucleos}")
    print(f"  procesos a lanzar     : {workers}")

    # Los grandes primero. getsize() consulta los metadatos del sistema
    # de archivos, no lee el contenido, asi que ordenar el lote entero no
    # cuesta memoria.
    def tamano(ruta):
        try:
            return os.path.getsize(ruta)
        except OSError:
            return 0

    archivos.sort(key=tamano, reverse=True)
    args.workers_reales = workers

    # ---------- Cargar, repartir y recoger ----------------------------
    # El vocabulario se va uniendo aqui segun llegan los resultados, no
    # al final: asi nunca hay 505 conjuntos vivos a la vez.
    vocabulario = set()
    fallos = []
    t0 = time.perf_counter()
    with ProcessPoolExecutor(workers, initializer=_init_worker,
                             initargs=(LIMITE_MEM_WORKER,)) as ex:
        filas, total_bytes, t_carga, t_union = repartir(
            ex, archivos, raiz, args, fallos, vocabulario)
    t_fase = time.perf_counter() - t0
    print()

    # La union se cronometro dentro del bucle, donde de verdad ocurre.
    # Aqui solo se descarta la cadena vacia que puede colarse de un
    # archivo sin texto.
    vocabulario.discard("")

    # ---------- Escribir la lista de palabras -------------------------
    t0 = time.perf_counter()
    palabras = extraer.ordenar(vocabulario)
    with open(args.palabras, "w", encoding="utf-8") as fh:
        fh.write("\n".join(palabras))
        if palabras:
            fh.write("\n")
    t_escritura = time.perf_counter() - t0

    filas.sort(key=lambda f: f["ruta"])
    suma_cpu = sum(f["t_limpieza"] for f in filas)
    suma_extraccion = sum(f["t_extraccion"] for f in filas)
    t_total = time.perf_counter() - t_programa

    escribir_tiempos(
        args.tiempos, filas, fallos, suma_cpu, t_fase, t_total,
        {"nucleos": nucleos, "workers": workers,
         "ventana": max(2, workers * 3),
         "t_carga": t_carga, "mb": total_bytes / 1024 / 1024,
         "palabras": len(palabras), "archivo_palabras": args.palabras,
         "suma_extraccion": suma_extraccion,
         "t_union": t_union, "t_escritura": t_escritura,
         # Lo que queda de la fase despues de descontar el trabajo util:
         # el de los workers, repartido entre ellos, y el que hizo el
         # padre uniendo vocabularios mientras tanto.
         "t_ipc": max(0.0, t_fase - (suma_cpu + suma_extraccion)
                      / max(1, workers) - t_union)},
        raiz)

    vacios = sum(1 for f in filas if f["vacio"])
    print(f"\npalabras  -> {args.palabras}  ({len(palabras):,} unicas)")
    print(f"tiempos   -> {args.tiempos}")
    if vacios:
        print(f"{vacios} archivos sin texto visible")
    if fallos:
        print(f"{len(fallos)} archivos con error (ver {args.tiempos})")
    print(f"tiempo total en eliminar las etiquetas HTML: {t_fase:.6f} s")
    print(f"tiempo total de ejecucion: {t_total:.6f} s")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
