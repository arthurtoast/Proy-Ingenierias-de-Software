"""
CARGAR - Lee un archivo a memoria de forma segura.

Responsabilidad unica: ruta -> bytes. No decodifica, no interpreta, no
importa a los otros modulos.

    cargar(ruta, raiz, max_bytes) -> (bytes | None, error: str | None)

Nunca lanza excepciones: cualquier fallo sale como texto en el segundo
elemento de la tupla. Un archivo problematico produce una linea de error
en el informe, nunca una traza ni un lote abortado.

Protecciones, con su identificador del catalogo CWE de MITRE:

  CWE-59  Symlink following ..... O_NOFOLLOW rechaza el enlace al abrir
  CWE-367 Carrera TOCTOU ........ fstat() sobre el descriptor, no la ruta
  CWE-22  Path traversal ........ realpath confinado a la carpeta raiz
  CWE-400 Agotar recursos ....... el tamano se comprueba ANTES de leer
  CWE-732 Descriptor heredado ... O_CLOEXEC
  CWE-775 Fuga de descriptores .. close() en un bloque finally
"""

import errno
import os
import stat

MAX_BYTES = 20 * 1024 * 1024

# O_NOFOLLOW hace la comprobacion de symlink de forma atomica, dentro de
# la propia llamada al sistema. Un lstat() previo dejaria una ventana
# entre la comprobacion y la apertura que otro proceso podria aprovechar.
_FLAGS = os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC


def cargar(ruta, raiz=None, max_bytes=MAX_BYTES):
    """Lee el archivo entero a memoria. Devuelve (bytes, error)."""

    # Confinamiento: se resuelve la ruta real y se comprueba que cuelgue
    # de la carpeta que el usuario indico, antes de tocar el disco.
    if raiz is not None:
        try:
            real = os.path.realpath(ruta)
            raiz_real = os.path.realpath(raiz)
            if not (real == raiz_real or real.startswith(raiz_real + os.sep)):
                return None, "fuera de la raiz permitida"
        except OSError as e:
            return None, f"no se pudo resolver la ruta: {e}"

    fd = None
    try:
        fd = os.open(ruta, _FLAGS)

        # fstat sobre el descriptor ya abierto: apunta al inodo real, asi
        # que nadie puede sustituir el archivo entre esta comprobacion y
        # la lectura de abajo.
        st = os.fstat(fd)

        if not stat.S_ISREG(st.st_mode):
            return None, "no es un archivo regular"

        # Se rechaza por tamano antes de reservar un solo byte de memoria.
        if st.st_size > max_bytes:
            return None, f"excede el limite ({st.st_size} > {max_bytes})"

        if st.st_size == 0:
            return b"", None

        # Lectura en trozos de 1 MiB, nunca mas alla de st_size: si otro
        # proceso esta escribiendo el archivo mientras lo leemos, no nos
        # arrastra a leer indefinidamente.
        trozos = []
        leidos = 0
        while leidos < st.st_size:
            trozo = os.read(fd, min(1 << 20, st.st_size - leidos))
            if not trozo:
                break                    # el archivo encogio: devolvemos lo leido
            trozos.append(trozo)
            leidos += len(trozo)

        return b"".join(trozos), None

    except FileNotFoundError:
        return None, "no existe"
    except IsADirectoryError:
        return None, "es un directorio"
    except PermissionError:
        return None, "sin permisos de lectura"
    except OSError as e:
        if e.errno == errno.ELOOP:
            return None, "es un symlink (rechazado por O_NOFOLLOW)"
        if e.errno == errno.EMFILE:
            return None, "demasiados descriptores abiertos"
        return None, f"error de E/S ({e.errno}): {e.strerror}"
    except MemoryError:
        return None, "sin memoria suficiente"
    finally:
        # Se ejecuta pase lo que pase: tambien si salta el timeout del
        # worker a mitad de lectura. Sin esto, cada archivo problematico
        # dejaria un descriptor colgado hasta agotar el limite del proceso.
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass
