#!/usr/bin/env python3
"""
MAIN - Orquestador. Es el unico archivo que importa a los demas, de
principio a fin del programa.

    main.py
      |-- cargar.py        ruta   -> bytes   (se ejecuta en el main)
      |-- decodificar.py   bytes  -> str     (en el worker)
      `-- limpiar.py       str    -> texto   (en el worker, CRONOMETRADO)

Los tres modulos son funciones puras, sin estado y sin importarse entre
si. Todas devuelven (resultado, error) y ninguna lanza excepciones.

QUE HACE, EN ORDEN
    1. Recorre la carpeta y ordena los archivos de mayor a menor,
       consultando solo su tamano.
    2. Lanza un proceso por nucleo y mantiene una ventana de unos pocos
       archivos en vuelo: carga uno, lo envia, y en cuanto un worker
       devuelve un resultado carga y envia el siguiente.
    3. Cada worker decodifica su archivo y le quita las etiquetas. Solo
       la eliminacion de etiquetas entra en el cronometro.
    4. El worker escribe el .txt el mismo, para que el texto no tenga que
       volver por la tuberia hasta el main.
    5. El main escribe el informe de tiempos.

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
import limpiar

# --- Valores por defecto. Cambiar aqui cambia el comportamiento del
#     programa sin tener que pasar opciones por la linea de ordenes.
CARPETA_SALIDA = "salida"       # carpeta donde se escriben los .txt
ARCHIVO_TIEMPOS = "a2.txt"      # informe con los tiempos por archivo

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


def procesar(nombre, datos, dir_salida, timeout, raiz=None, limite=0):
    """Decodifica y limpia un archivo. Corre en el proceso hijo.

    `datos` son los bytes que el main ya cargo. Si en su lugar llega una
    ruta (una str), el worker lee el archivo el mismo: es el modo
    --carga-en-worker, que evita mandar los bytes por la tuberia.

    Devuelve siempre un diccionario pequeno, nunca lanza: un archivo malo
    no puede tumbar el lote. El texto limpio no viaja de vuelta, lo
    escribe el propio worker.
    """
    r = {"nombre": nombre, "estado": "ok", "error": "", "vacio": False,
         "pid": os.getpid(), "bytes": 0, "t_limpieza": 0.0}

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

        # La escritura queda fuera del cronometro a proposito: mide el
        # disco, no el trabajo de quitar etiquetas.
        destino = os.path.join(dir_salida, nombre + ".txt")
        os.makedirs(os.path.dirname(destino) or ".", exist_ok=True)
        with open(destino, "w", encoding="utf-8") as fh:
            fh.write(limpio)
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


def nombre_salida(ruta, raiz):
    """Nombre del .txt: a.html -> a, y sub/b.htm -> sub_b.

    Los subdirectorios se aplanan con guion bajo para que dos archivos
    con el mismo nombre en carpetas distintas no se pisen en salida/.
    """
    base, _ext = os.path.splitext(os.path.relpath(ruta, raiz))
    return base.replace(os.sep, "_")


def nombre_corto(ruta, raiz):
    """Nombre para el informe: Files/503.html en vez de la ruta absoluta.

    Se conserva la ruta interna (Files/2024/007.html) para que no haya
    dos lineas iguales cuando hay subcarpetas.
    """
    rel = os.path.relpath(ruta, raiz)
    return os.path.basename(raiz) + "/" + rel


def repartir(ex, archivos, raiz, dir_salida, args, fallos):
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

    Devuelve (filas, bytes_leidos, segundos_de_lectura).
    """
    limite = args.limite_mb * 1024 * 1024
    limite_ram = args.ram_mb * 1024 * 1024
    ventana = max(2, args.workers_reales * 3)

    filas = []
    pendientes = {}          # future -> ruta
    bytes_vivos = 0          # bytes que el ejecutor aun retiene
    bytes_leidos = 0
    t_lectura = 0.0
    restantes = iter(archivos)
    hechos = 0
    total = len(archivos)

    def enviar_siguiente():
        """Carga y envia un archivo. False si ya no queda ninguno."""
        nonlocal bytes_vivos, bytes_leidos, t_lectura
        for ruta in restantes:
            if args.carga_en_worker:
                # El worker lee el archivo; aqui solo viaja la ruta.
                fut = ex.submit(procesar, nombre_salida(ruta, raiz), ruta,
                                dir_salida, args.timeout, raiz, limite)
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
            fut = ex.submit(procesar, nombre_salida(ruta, raiz), datos,
                            dir_salida, args.timeout, raiz, limite)
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
                    r["ruta"] = ruta
                    filas.append(r)
                    bytes_vivos = max(0, bytes_vivos - r.get("bytes", 0))
            print(f"\r  procesados {hechos}/{total}", end="", flush=True)

        # Rellenar los huecos que acaban de quedar libres.
        while len(pendientes) < ventana and bytes_vivos < limite_ram:
            if not enviar_siguiente():
                break

    return filas, bytes_leidos, t_lectura


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
        "",
        "desglose:",
        f"  lectura de disco (sumada)     : {info['t_carga']:12.6f} s"
        f"   ({info['mb']:.1f} MB, intercalada con el proceso)",
        # Suma de lo que trabajo cada nucleo. Es mayor que el tiempo real
        # porque varios nucleos trabajan a la vez: N nucleos durante un
        # segundo consumen N segundos de CPU en un segundo de reloj.
        f"  limpieza pura (suma de CPU)   : {suma_cpu:12.6f} s"
        f"   repartida entre {info['workers']} procesos",
        f"  fase de limpieza (tiempo real): {t_fase:12.6f} s",
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
    ap.add_argument("--salida", default=CARPETA_SALIDA,
                    help=f"carpeta de los .txt (por defecto: {CARPETA_SALIDA})")
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

    os.makedirs(args.salida, exist_ok=True)

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
    fallos = []
    t0 = time.perf_counter()
    with ProcessPoolExecutor(workers, initializer=_init_worker,
                             initargs=(LIMITE_MEM_WORKER,)) as ex:
        filas, total_bytes, t_carga = repartir(
            ex, archivos, raiz, os.path.abspath(args.salida), args, fallos)
    t_fase = time.perf_counter() - t0
    print()

    filas.sort(key=lambda f: f["ruta"])
    suma_cpu = sum(f["t_limpieza"] for f in filas)
    t_total = time.perf_counter() - t_programa

    escribir_tiempos(
        args.tiempos, filas, fallos, suma_cpu, t_fase, t_total,
        {"nucleos": nucleos, "workers": workers,
         "ventana": max(2, workers * 3),
         "t_carga": t_carga, "mb": total_bytes / 1024 / 1024,
         "t_ipc": max(0.0, t_fase - suma_cpu / max(1, workers))},
        raiz)

    vacios = sum(1 for f in filas if f["vacio"])
    print(f"\ntexto     -> {args.salida}/  ({len(filas)} archivos .txt)")
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
