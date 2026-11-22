#!/usr/bin/env python3
"""
Levanta el entorno de staging local del proyecto Inventario ADR.

Reemplaza los servicios externos por equivalentes que viven en esta máquina:

    base de datos   Clever Cloud  ->  MySQL local (con el último dump conocido)
    correo          SendGrid      ->  capturado y mostrado en pantalla
    logo correo     Cloudinary    ->  imagen servida desde static/
    hosting         Render        ->  runserver

Requisito: conexión a internet. Se usa para intentar el dump de producción y
para que las plantillas carguen sus estilos desde los CDN.

Uso:
    python iniciar_staging.py
    python iniciar_staging.py --puerto 8080
    python iniciar_staging.py --sin-dump
"""

from __future__ import annotations

import argparse
import gzip
import os
import stat
import subprocess
import sys
from datetime import datetime
from getpass import getpass
from pathlib import Path

RAIZ_PROYECTO = Path(__file__).resolve().parent
DIRECTORIO_STAGING = RAIZ_PROYECTO / 'staging'
DIRECTORIO_DUMPS = DIRECTORIO_STAGING / 'dumps'
DIRECTORIO_CORREOS = DIRECTORIO_STAGING / 'correos'
ARCHIVO_CREDENCIALES = DIRECTORIO_STAGING / 'credenciales.env'

# Campos que se piden para conectarse a la base de producción.
# Cada campo lleva: nombre interno, etiqueta visible, valor por omisión y una
# ayuda breve que se muestra cuando el campo debe volver a preguntarse.
CAMPOS_CREDENCIALES = (
    ('PROD_DB_HOST', 'Host de la base de datos', '',
     'el servidor del cluster, algo como xxxxxx-mysql.services.clever-cloud.com'),
    ('PROD_DB_PORT', 'Puerto', '3306',
     'el puerto que aparece junto al host; MySQL remoto casi siempre usa 3306'),
    ('PROD_DB_USER', 'Usuario', '',
     'el usuario del add-on MySQL, formato corto tipo uXXXXXXXX'),
    ('PROD_DB_PASSWORD', 'Contraseña', '',
     'la clave del mismo add-on; se escribe sin mostrar caracteres'),
    ('PROD_DB_NAME', 'Nombre de la base de datos', '',
     'el nombre de la base dentro del cluster, por ejemplo la del inventario ADR'),
)

# Orden en que los campos dependen unos de otros, para saber cuál volver a
# preguntar cuando la conexión falla.
CAMPOS_REINTENTABLES = ('PROD_DB_HOST', 'PROD_DB_PORT', 'PROD_DB_USER',
                        'PROD_DB_PASSWORD', 'PROD_DB_NAME')

# Sentencias que un dump trae y que romperían la importación a la base local:
# crearían o seleccionarían una base con el nombre de producción.
PREFIJOS_IGNORADOS = ('CREATE DATABASE', 'USE ')


# ---------------------------------------------------------------------------
# Utilidades de consola
# ---------------------------------------------------------------------------

def informar(mensaje: str) -> None:
    print(f"[staging] {mensaje}")


def advertir(mensaje: str) -> None:
    print(f"[staging] AVISO: {mensaje}", file=sys.stderr)


def fallar(mensaje: str) -> None:
    print(f"[staging] ERROR: {mensaje}", file=sys.stderr)
    sys.exit(1)


def titulo(mensaje: str) -> None:
    print()
    print(f"=== {mensaje} ===")


# ---------------------------------------------------------------------------
# Entorno de Python
# ---------------------------------------------------------------------------

def ruta_python_venv() -> Path | None:
    """Ubica el intérprete del entorno virtual del proyecto, si existe."""
    candidatos = (
        RAIZ_PROYECTO / 'venv' / 'bin' / 'python',
        RAIZ_PROYECTO / 'venv' / 'Scripts' / 'python.exe',
    )
    for candidato in candidatos:
        if candidato.exists():
            return candidato
    return None


def asegurar_entorno_virtual() -> None:
    """
    Reinicia el script con el Python del entorno virtual.

    El Python del sistema no tiene las dependencias del proyecto, así que se
    relanza el proceso una sola vez con el intérprete correcto.
    """
    if os.environ.get('STAGING_YA_RELANZADO') == '1':
        return

    python_venv = ruta_python_venv()
    if python_venv is None:
        advertir('no se encontró la carpeta venv/; se usará el Python actual')
        return

    if Path(sys.executable).resolve() == python_venv.resolve():
        return

    entorno = dict(os.environ, STAGING_YA_RELANZADO='1')
    resultado = subprocess.run([str(python_venv), *sys.argv], env=entorno)
    sys.exit(resultado.returncode)


# ---------------------------------------------------------------------------
# Conexión a internet
# ---------------------------------------------------------------------------

def hay_conexion_internet() -> bool:
    """
    Comprueba conectividad abriendo un socket corto contra destinos conocidos.

    Se prueban varios destinos porque algunos proveedores bloquean solo ciertos
    puertos, y basta con que uno responda.
    """
    import socket

    destinos = (
        ('1.1.1.1', 443),
        ('8.8.8.8', 53),
        ('cdn.jsdelivr.net', 443),
    )
    for destino, puerto in destinos:
        try:
            with socket.create_connection((destino, puerto), timeout=3):
                return True
        except OSError:
            continue
    return False


# ---------------------------------------------------------------------------
# Credenciales de producción
# ---------------------------------------------------------------------------

def leer_credenciales_guardadas() -> dict:
    """Lee el archivo de credenciales si existe, sin fallar si está incompleto."""
    if not ARCHIVO_CREDENCIALES.exists():
        return {}

    guardadas = {}
    for linea in ARCHIVO_CREDENCIALES.read_text(encoding='utf-8').splitlines():
        linea = linea.strip()
        if not linea or linea.startswith('#') or '=' not in linea:
            continue
        nombre, valor = linea.split('=', 1)
        guardadas[nombre.strip()] = valor.strip()
    return guardadas


def guardar_credenciales(credenciales: dict) -> None:
    """
    Persiste las credenciales en staging/credenciales.env con permisos 600.

    El archivo está cubierto por .gitignore, de modo que nunca llega al
    repositorio compartido.
    """
    DIRECTORIO_STAGING.mkdir(parents=True, exist_ok=True)
    lineas = [
        '# Credenciales de la base de datos de producción.',
        '# Generado por iniciar_staging.py. No subir al repositorio.',
    ]
    for nombre, _etiqueta, _predeterminado in CAMPOS_CREDENCIALES:
        lineas.append(f"{nombre}={credenciales.get(nombre, '')}")

    ARCHIVO_CREDENCIALES.write_text('\n'.join(lineas) + '\n', encoding='utf-8')
    try:
        ARCHIVO_CREDENCIALES.chmod(stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass


def mostrar_banner_dumpeo() -> None:
    """
    Explica qué se necesita antes de pedir las credenciales por primera vez.

    Sin este aviso, el usuario no sabe de dónde salen los cinco datos que el
    script le va a pedir ni por qué son necesarios.
    """
    print()
    print('  ' + '-' * 66)
    print('  PRIMER DUMPEO: SE NECESITAN LAS CREDENCIALES DEL CLUSTER')
    print('  ' + '-' * 66)
    print()
    print('  Para traer los datos reales, este script se conecta al cluster')
    print('  de base de datos MySQL que usa la plataforma en producción:')
    print()
    print('  Esa conexión es de solo lectura. El script únicamente lee los')
    print('  datos con mysqldump; nunca escribe ni borra nada en producción.')
    print()
    print('  Donde encontrar los datos:')
    print('    Consola de Clever Cloud -> Personal Space -> add-on MySQL')
    print('    Los valores están en "Connection details" o en las variables')
    print('    de entorno del add-on.')
    print()
    print('  Se pedirán cinco datos, uno por uno:')
    print('    host, puerto, usuario, contraseña y nombre de la base.')
    print()
    print('  Si alguno falla, se vuelve a preguntar solo ese, no todos.')
    print('  Lo que escribas se guarda en staging/credenciales.env, que está')
    print('  fuera del repositorio, para no repetir esto en cada arranque.')
    print()


def _ayuda_de(nombre_campo: str) -> str:
    """Devuelve la ayuda asociada a un campo, o cadena vacía si no tiene."""
    for nombre, _etiqueta, _predeterminado, ayuda in CAMPOS_CREDENCIALES:
        if nombre == nombre_campo:
            return ayuda
    return ''


def _etiqueta_de(nombre_campo: str) -> str:
    """Devuelve la etiqueta visible de un campo."""
    for nombre, etiqueta, _predeterminado, _ayuda in CAMPOS_CREDENCIALES:
        if nombre == nombre_campo:
            return etiqueta
    return nombre_campo


def _leer_campo(nombre: str, valor_previo: str) -> str:
    """
    Lee un único campo de la terminal.

    La contraseña no se muestra al escribir; el resto sí, con el valor previo
    entre corchetes para poder aceptarlo pulsando Enter. El puerto se valida
    aquí mismo para no arrastrar un texto donde se espera un número.
    """
    if nombre == 'PROD_DB_PASSWORD':
        try:
            entrada = getpass(f'  {_etiqueta_de(nombre)}: ')
        except EOFError:
            fallar('la entrada se cerró mientras se pedían las credenciales')
        return entrada or valor_previo

    if nombre == 'PROD_DB_PORT':
        while True:
            try:
                crudo = input(f'  {_etiqueta_de(nombre)} [{valor_previo}]: ').strip()
            except EOFError:
                fallar('la entrada se cerró mientras se pedían las credenciales')
            candidato = crudo or valor_previo
            if candidato.isdigit() and 0 < int(candidato) < 65536:
                return candidato
            advertir(f'el puerto debe ser un número entre 1 y 65535, no "{candidato}"')

    sufijo = f' [{valor_previo}]' if valor_previo else ''
    try:
        entrada = input(f'  {_etiqueta_de(nombre)}{sufijo}: ').strip()
    except EOFError:
        fallar('la entrada se cerró mientras se pedían las credenciales')
    return entrada or valor_previo


def _preguntar_campo_suelto(nombre: str, credenciales: dict) -> None:
    """Pregunta un campo concreto mostrando su ayuda, y lo guarda en el dict."""
    ayuda = _ayuda_de(nombre)
    if ayuda:
        informar(f'({_etiqueta_de(nombre)}) se espera {ayuda}')
    credenciales[nombre] = _leer_campo(nombre, credenciales.get(nombre, ''))


def pedir_credenciales(anteriores: dict) -> dict:
    """
    Pregunta los cinco datos y reintenta solo el campo que cause el fallo.

    El primer contacto con producción suele fallar por un único dato mal
    copiado. Volver a pedir todo es incómodo y propenso a nuevos errores, así
    que cada vuelta pregunta nada más lo que haga falta.
    """
    mostrar_banner_dumpeo()

    credenciales = {}
    for nombre in CAMPOS_REINTENTABLES:
        predeterminado = anteriores.get(nombre)
        if not predeterminado:
            predeterminado = next(
                (p for n, _e, p, _a in CAMPOS_CREDENCIALES if n == nombre), ''
            )
        credenciales[nombre] = predeterminado

    # Se preguntan los cinco campos, como anuncia el banner. El puerto muestra
    # su 3306 entre corchetes para que baste pulsar Enter.
    for nombre in CAMPOS_REINTENTABLES:
        credenciales[nombre] = _leer_campo(nombre, credenciales.get(nombre, ''))

    # A partir de aquí solo se repite lo que impide conectar.
    for intento in range(1, 6):
        problema = _diagnosticar_conexion(credenciales)
        if problema is None:
            informar('conexión a producción verificada')
            guardar_credenciales(credenciales)
            informar('credenciales guardadas para el próximo arranque')
            return credenciales

        campos, mensaje = problema
        advertir(mensaje)
        if intento == 5:
            break
        informar(f'reintento {intento} de 5: se vuelve a preguntar solo lo necesario')

        if not campos:
            campos = ('PROD_DB_HOST', 'PROD_DB_PORT', 'PROD_DB_USER',
                      'PROD_DB_PASSWORD', 'PROD_DB_NAME')

        for nombre in campos:
            _preguntar_campo_suelto(nombre, credenciales)

    advertir('no se logró conectar a producción con los datos ingresados')
    return {}


def _diagnosticar_conexion(credenciales: dict) -> tuple[tuple, str] | None:
    """
    Intenta conectar y traduce el error en los campos culpables.

    Devuelve None si conectó, o una tupla con los campos a repreguntar y el
    mensaje que explica el problema.
    """
    import pymysql

    try:
        conexion = pymysql.connect(
            host=credenciales['PROD_DB_HOST'],
            port=int(credenciales['PROD_DB_PORT'] or 3306),
            user=credenciales['PROD_DB_USER'],
            password=credenciales['PROD_DB_PASSWORD'],
            database=credenciales['PROD_DB_NAME'],
            connect_timeout=10,
        )
    except Exception as error:
        return _traducir_error(error, credenciales)

    conexion.close()
    return None


def _traducir_error(error: Exception, credenciales: dict) -> tuple[tuple, str]:
    """
    Convierte el error de MySQL en los campos concretos que hay que corregir.

    Cada código de error señala una causa distinta, y apuntar al campo correcto
    evita que el usuario reescriba datos que ya estaban bien.
    """
    import pymysql

    codigo = None
    if isinstance(error, pymysql.err.OperationalError) and error.args:
        codigo = error.args[0]

    if codigo == 1045:
        return (('PROD_DB_USER', 'PROD_DB_PASSWORD'),
                'usuario o contraseña rechazados por el servidor')
    if codigo == 1049:
        return (('PROD_DB_NAME',),
                'el servidor respondió, pero esa base de datos no existe')
    if codigo == 1044:
        return (('PROD_DB_USER', 'PROD_DB_NAME'),
                'el usuario no tiene permiso sobre esa base de datos')
    if codigo in (2003, 2005):
        return (('PROD_DB_HOST', 'PROD_DB_PORT'),
                'no se pudo llegar al servidor: host o puerto incorrectos, '
                'o la red bloquea el puerto')
    if codigo == 2002:
        return (('PROD_DB_HOST',), 'el host no resolvió; revisa el nombre del servidor')

    texto = str(error)
    if 'timed out' in texto.lower() or 'timeout' in texto.lower():
        return (('PROD_DB_HOST', 'PROD_DB_PORT'),
                'la conexión expiró sin respuesta del servidor')

    return ((), f'error inesperado de conexión: {texto[:200]}')


def probar_conexion_remota(credenciales: dict) -> bool:
    """Verifica que las credenciales permitan abrir la base de producción."""
    problema = _diagnosticar_conexion(credenciales)
    if problema is None:
        informar('conexión a producción verificada')
        return True

    _campos, mensaje = problema
    advertir(f'no se pudo conectar a producción: {mensaje}')
    return False


def obtener_credenciales_validas(permitir_preguntar: bool) -> dict | None:
    """
    Devuelve credenciales que conectan, o None si no se lograron.

    Primero intenta con las guardadas; solo pregunta si esas fallan.
    """
    guardadas = leer_credenciales_guardadas()
    completas = all(
        guardadas.get(nombre)
        for nombre, _etiqueta, _predeterminado, _ayuda in CAMPOS_CREDENCIALES
        if nombre != 'PROD_DB_PORT'
    )
    if completas:
        informar('usando credenciales guardadas de staging/credenciales.env')
        if probar_conexion_remota(guardadas):
            return guardadas
        advertir('las credenciales guardadas ya no funcionan; se pedirán de nuevo')

    if not permitir_preguntar:
        return None

    nuevas = pedir_credenciales(guardadas)
    return nuevas or None


# ---------------------------------------------------------------------------
# Dump de producción
# ---------------------------------------------------------------------------

def descargar_dump(credenciales: dict) -> Path | None:
    """
    Ejecuta mysqldump contra producción y guarda el resultado comprimido.

    La contraseña viaja por la variable de entorno MYSQL_PWD para que no quede
    visible en la lista de procesos del sistema.
    """
    if shutil_which('mysqldump') is None:
        advertir('mysqldump no está instalado; se omite la descarga')
        return None

    DIRECTORIO_DUMPS.mkdir(parents=True, exist_ok=True)
    marca = datetime.now().strftime('%Y%m%d_%H%M%S')
    destino = DIRECTORIO_DUMPS / f"produccion_{marca}.sql.gz"

    comando = [
        'mysqldump',
        '--host', credenciales['PROD_DB_HOST'],
        '--port', str(credenciales['PROD_DB_PORT'] or 3306),
        '--user', credenciales['PROD_DB_USER'],
        '--single-transaction',
        '--quick',
        '--no-tablespaces',
        '--default-character-set=utf8mb4',
        credenciales['PROD_DB_NAME'],
    ]
    entorno = dict(os.environ, MYSQL_PWD=credenciales['PROD_DB_PASSWORD'])

    informar('descargando el dump de producción; puede tardar varios minutos')
    try:
        with gzip.open(destino, 'wb') as salida:
            resultado = subprocess.run(
                comando, stdout=salida, stderr=subprocess.PIPE, env=entorno
            )
    except OSError as error:
        advertir(f'no se pudo ejecutar mysqldump: {error}')
        destino.unlink(missing_ok=True)
        return None

    if resultado.returncode != 0:
        detalle = resultado.stderr.decode('utf-8', errors='ignore').strip()
        advertir(f'mysqldump falló: {detalle[:400]}')
        destino.unlink(missing_ok=True)
        return None

    tamano_mb = destino.stat().st_size / (1024 * 1024)
    informar(f'dump guardado en {destino.name} ({tamano_mb:.1f} MB)')
    return destino


def shutil_which(nombre: str) -> str | None:
    """Busca un ejecutable en el PATH sin depender de shutil en el resto del flujo."""
    import shutil

    return shutil.which(nombre)


def dump_mas_reciente() -> Path | None:
    """
    Devuelve el dump de producción más nuevo, recordando el anterior.

    Los archivos `respaldo_local_*` se excluyen a propósito: son copias de
    seguridad de la base local, no datos de producción.
    """
    if not DIRECTORIO_DUMPS.is_dir():
        return None

    candidatos = [
        ruta for ruta in DIRECTORIO_DUMPS.iterdir()
        if ruta.is_file()
        and ruta.name.endswith(('.sql', '.sql.gz'))
        and not ruta.name.startswith('respaldo_local_')
    ]
    if not candidatos:
        return None
    return max(candidatos, key=lambda ruta: ruta.stat().st_mtime)


# ---------------------------------------------------------------------------
# Base de datos local
# ---------------------------------------------------------------------------

def credenciales_locales() -> dict:
    """Toma los datos de la base local desde el .env del proyecto."""
    from decouple import config

    return {
        'HOST': config('DB_HOST', default='127.0.0.1'),
        'PORT': int(config('DB_PORT', default='3306')),
        'USER': config('DB_USER', default='root'),
        'PASSWORD': config('DB_PASSWORD', default=''),
        'NAME': config('DB_NAME', default='inventario_adr'),
    }


# Sufijo que se añade al nombre configurado. El script nunca opera sobre la
# base del .env: siempre sobre esta variante, de modo que una sentencia
# destructiva no puede nombrar la base que usa producción.
SUFIJO_BASE_STAGING = '_staging'


def nombre_base_staging(nombre_configurado: str) -> str:
    """
    Deriva el nombre de la base de staging a partir del configurado.

    `inventario_adr` pasa a `inventario_adr_staging`. Si el nombre ya trae el
    sufijo se deja igual, para que ejecutar dos veces no lo duplique.
    """
    nombre = (nombre_configurado or 'inventario_adr').strip()
    if nombre.endswith(SUFIJO_BASE_STAGING):
        return nombre
    return f'{nombre}{SUFIJO_BASE_STAGING}'


# Hosts que designan esta misma máquina. Cualquier otro valor significa que la
# base está en un servidor ajeno, y ahí no se borra nada bajo ninguna excusa.
HOSTS_LOCALES = ('127.0.0.1', 'localhost', '::1', '0.0.0.0', '')


def asegurar_base_local(locales: dict) -> None:
    """
    Aborta si la base configurada no está en esta máquina.

    Es la única condición que separa una limpieza legítima de la base de
    staging de un borrado accidental de producción. Se comprueba justo antes
    de borrar, no al arrancar, para que ningún cambio posterior en el .env
    pueda saltársela.
    """
    host = (locales.get('HOST') or '').strip().lower()

    if host in HOSTS_LOCALES:
        return

    fallar(
        f'la base configurada apunta a "{host}", que no es esta máquina. '
        'El script solo borra bases locales; revisa DB_HOST en tu .env.'
    )


def contar_tablas_locales(locales: dict) -> int:
    """Cuenta las tablas existentes en la base local para saber si está vacía."""
    import pymysql

    try:
        conexion = pymysql.connect(
            host=locales['HOST'],
            port=locales['PORT'],
            user=locales['USER'],
            password=locales['PASSWORD'],
            database=locales['NAME'],
            connect_timeout=8,
        )
    except Exception:
        return 0

    try:
        with conexion.cursor() as cursor:
            cursor.execute(
                'SELECT COUNT(*) FROM information_schema.tables '
                'WHERE table_schema = %s',
                (locales['NAME'],),
            )
            return int(cursor.fetchone()[0])
    finally:
        conexion.close()


def respaldar_base_local(locales: dict) -> Path | None:
    """
    Guarda un respaldo de la base local antes de borrarla.

    Si la importación falla, el respaldo permite volver al estado anterior en
    lugar de quedarse sin datos.
    """
    if shutil_which('mysqldump') is None:
        return None

    marca = datetime.now().strftime('%Y%m%d_%H%M%S')
    destino = DIRECTORIO_DUMPS / f"respaldo_local_{marca}.sql.gz"
    comando = [
        'mysqldump',
        '--host', locales['HOST'],
        '--port', str(locales['PORT']),
        '--user', locales['USER'],
        '--single-transaction',
        '--quick',
        '--no-tablespaces',
        '--default-character-set=utf8mb4',
        locales['NAME'],
    ]
    entorno = dict(os.environ, MYSQL_PWD=locales['PASSWORD'])

    try:
        with gzip.open(destino, 'wb') as salida:
            resultado = subprocess.run(
                comando, stdout=salida, stderr=subprocess.DEVNULL, env=entorno
            )
    except OSError:
        return None

    if resultado.returncode != 0:
        destino.unlink(missing_ok=True)
        return None

    informar(f'respaldo de la base local guardado en {destino.name}')
    return destino


def base_local_existe(locales: dict) -> bool:
    """Comprueba si la base configurada ya existe en el servidor local."""
    import pymysql

    try:
        conexion = pymysql.connect(
            host=locales['HOST'],
            port=locales['PORT'],
            user=locales['USER'],
            password=locales['PASSWORD'],
            connect_timeout=8,
        )
    except Exception:
        return False

    try:
        with conexion.cursor() as cursor:
            cursor.execute(
                'SELECT COUNT(*) FROM information_schema.schemata '
                'WHERE schema_name = %s',
                (locales['NAME'],),
            )
            return int(cursor.fetchone()[0]) > 0
    finally:
        conexion.close()


def crear_base_local(locales: dict) -> None:
    """
    Crea la base local vacía cuando todavía no existe.

    Sin este paso, `migrate` fallaría con "Access denied" porque la base no
    está entre los privilegios del usuario configurado.
    """
    import pymysql

    asegurar_base_local(locales)

    conexion = pymysql.connect(
        host=locales['HOST'],
        port=locales['PORT'],
        user=locales['USER'],
        password=locales['PASSWORD'],
        connect_timeout=8,
    )
    try:
        with conexion.cursor() as cursor:
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{locales['NAME']}` "
                'CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci'
            )
        conexion.commit()
    except Exception as error:
        fallar(
            f'no se pudo crear la base local "{locales["NAME"]}": {error}. '
            f'Créala a mano con: CREATE DATABASE {locales["NAME"]} '
            'CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;'
        )
    finally:
        conexion.close()


def recrear_base_local(locales: dict) -> None:
    """
    Vacía la base local para recibir el dump sin mezclar datos viejos.

    Esta es la única función del script que borra datos, y solo puede actuar
    sobre una base alojada en esta máquina.
    """
    import pymysql

    asegurar_base_local(locales)

    conexion = pymysql.connect(
        host=locales['HOST'],
        port=locales['PORT'],
        user=locales['USER'],
        password=locales['PASSWORD'],
        connect_timeout=8,
    )
    try:
        with conexion.cursor() as cursor:
            cursor.execute(f"DROP DATABASE IF EXISTS `{locales['NAME']}`")
            cursor.execute(
                f"CREATE DATABASE `{locales['NAME']}` "
                'CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci'
            )
        conexion.commit()
    finally:
        conexion.close()


def _sentencia_a_omitir(linea: str) -> bool:
    """Detecta las sentencias que cambiarían el destino de la importación."""
    mayusculas = linea.upper().lstrip()
    return any(mayusculas.startswith(prefijo) for prefijo in PREFIJOS_IGNORADOS)


def importar_dump(ruta_dump: Path, locales: dict) -> bool:
    """
    Carga el dump dentro de la base local.

    Las sentencias `CREATE DATABASE` y `USE` se descartan para que las tablas
    caigan siempre en la base configurada en el .env local.
    """
    cliente = shutil_which('mysql')
    if cliente is None:
        advertir('el cliente mysql no está instalado; no se puede importar')
        return False

    comando = [
        cliente,
        '--host', locales['HOST'],
        '--port', str(locales['PORT']),
        '--user', locales['USER'],
        '--default-character-set=utf8mb4',
        locales['NAME'],
    ]
    entorno = dict(os.environ, MYSQL_PWD=locales['PASSWORD'])

    abrir = gzip.open if ruta_dump.name.endswith('.gz') else open
    informar(f'importando {ruta_dump.name} en la base local {locales["NAME"]}')

    proceso = subprocess.Popen(
        comando,
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        env=entorno,
    )
    try:
        with abrir(ruta_dump, 'rb') as origen:
            for linea in origen:
                if _sentencia_a_omitir(linea.decode('utf-8', errors='ignore')):
                    continue
                proceso.stdin.write(linea)
    except BrokenPipeError:
        pass
    finally:
        try:
            proceso.stdin.close()
        except (BrokenPipeError, OSError):
            pass

    detalle = proceso.stderr.read().decode('utf-8', errors='ignore').strip()
    proceso.wait()

    if proceso.returncode != 0:
        advertir(f'la importación terminó con errores: {detalle[:400]}')
        return False

    informar('importación completada')
    return True


# ---------------------------------------------------------------------------
# Django
# ---------------------------------------------------------------------------

def ejecutar_manage(argumentos: list[str], variables_extra: dict) -> int:
    """Lanza un comando de manage.py con el entorno de staging activo."""
    entorno = dict(os.environ, ENTORNO='staging', **variables_extra)
    comando = [sys.executable, str(RAIZ_PROYECTO / 'manage.py'), *argumentos]
    return subprocess.run(comando, env=entorno, cwd=RAIZ_PROYECTO).returncode


def preparar_django() -> None:
    """Aplica migraciones y reúne los estáticos antes de servir la aplicación."""
    titulo('Preparando Django')

    variables = {}
    codigo = ejecutar_manage(['migrate', '--noinput'], variables)
    if codigo != 0:
        fallar('las migraciones fallaron; revisa el mensaje anterior')

    codigo = ejecutar_manage(['collectstatic', '--noinput', '--clear'], variables)
    if codigo != 0:
        advertir('collectstatic falló; los estáticos pueden verse incompletos')


def crear_superusuario(puerto: int) -> None:
    """
    Crea o actualiza una cuenta administradora en la base de staging.

    Se ejecuta en un proceso aparte con `ENTORNO=staging` para que use la misma
    base de datos que el servidor. La cuenta puede entrar aunque no pertenezca a
    ningún grupo, porque el dashboard acepta superusuarios.
    """
    titulo('Cuenta administradora')

    try:
        nombre = input('  Usuario [admin]: ').strip() or 'admin'
        correo = input('  Correo (opcional): ').strip()
        clave = getpass('  Contraseña: ')
    except EOFError:
        advertir('la entrada se cerró; no se creó ninguna cuenta')
        return

    if not clave:
        clave = 'staging2026'
        informar(f'sin contraseña se usa la predeterminada: {clave}')

    codigo_creacion = f'''
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from accounts.models import Profile

Usuario = get_user_model()
usuario, creado = Usuario.objects.get_or_create(username={nombre!r})
usuario.set_password({clave!r})
usuario.email = {correo!r}
usuario.is_staff = True
usuario.is_superuser = True
usuario.is_active = True
usuario.save()

perfil, _ = Profile.objects.get_or_create(user=usuario)
perfil.create_by_adr = False
perfil.save(update_fields=['create_by_adr'])

for nombre_grupo in ('ADR', 'Usuario'):
    grupo, _ = Group.objects.get_or_create(name=nombre_grupo)
    usuario.groups.add(grupo)

print('cuenta ' + ('creada' if creado else 'actualizada') + ': ' + usuario.username)
'''

    entorno = dict(os.environ, ENTORNO='staging',
                   STAGING_BASE_URL=f'http://127.0.0.1:{puerto}')
    resultado = subprocess.run(
        [sys.executable, '-c', codigo_creacion],
        env=entorno, cwd=RAIZ_PROYECTO, capture_output=True, text=True,
    )

    if resultado.returncode != 0:
        advertir(f'no se pudo crear la cuenta: {resultado.stderr.strip()[:300]}')
        return

    for linea in resultado.stdout.strip().splitlines():
        if linea.startswith('cuenta '):
            informar(linea)
    informar(f'usuario: {nombre}')


def preguntar_si_no(texto: str) -> bool:
    """Pregunta s/n y devuelve False como respuesta segura ante cualquier duda."""
    try:
        respuesta = input(f'  {texto} (s/n): ').strip().lower()
    except EOFError:
        return False
    return respuesta in ('s', 'si', 'sí', 'y', 'yes')


# Nombres de rama donde este script puede ejecutarse. Producción queda fuera a
# propósito: si la rama actual no está en esta lista, el script no arranca.
RAMAS_PERMITIDAS = ('staging', 'desarrollo', 'develop')


def _rama_actual() -> str | None:
    """Devuelve el nombre de la rama git actual, o None si no se puede leer."""
    try:
        resultado = subprocess.run(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
            cwd=RAIZ_PROYECTO, capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None

    if resultado.returncode != 0:
        return None
    return resultado.stdout.strip()


def verificar_entorno_seguro() -> None:
    """
    Se niega a continuar si no está en una rama de trabajo local.

    Este script borra y recrea la base de datos, así que solo debe correr en
    ramas donde los datos no son los de producción. La comprobación es la
    primera que se ejecuta, antes de leer credenciales o tocar la base.
    """
    problemas = []

    if os.environ.get('RENDER'):
        problemas.append('se detectó la variable RENDER: esto es producción')

    rama = _rama_actual()
    if rama is None:
        problemas.append('no se pudo determinar la rama git del proyecto')
    elif rama not in RAMAS_PERMITIDAS and not rama.startswith('practicantes-'):
        problemas.append(
            f'la rama actual es "{rama}" y el script solo corre en '
            f'{", ".join(RAMAS_PERMITIDAS)} o en ramas "practicantes-*"'
        )

    if not sys.stdin.isatty():
        problemas.append('no hay terminal interactiva: parece una ejecución remota')

    if problemas:
        print()
        print('[staging] EJECUCIÓN BLOQUEADA', file=sys.stderr)
        for problema in problemas:
            print(f'[staging]   - {problema}', file=sys.stderr)
        print(
            '[staging] este script borra y recrea la base de datos, así que '
            'solo se permite en ramas de trabajo local.',
            file=sys.stderr,
        )
        sys.exit(1)

    informar(f'entorno verificado: rama "{rama}", ejecución local')


def arrancar_servidor(puerto: int) -> None:
    """Levanta el servidor de desarrollo con la configuración de staging."""
    titulo('Servidor listo')
    informar(f'aplicación disponible en http://127.0.0.1:{puerto}/')
    informar(f'correos capturados en {DIRECTORIO_CORREOS}')
    print()

    variables = {'STAGING_BASE_URL': f'http://127.0.0.1:{puerto}'}
    codigo = ejecutar_manage(['runserver', f'127.0.0.1:{puerto}'], variables)
    sys.exit(codigo)


# ---------------------------------------------------------------------------
# Flujo principal
# ---------------------------------------------------------------------------

OPCIONES_MENU = (
    ('1', 'Inicio con dumpeo'),
    ('2', 'Inicio sin dumpeo'),
    ('3', 'Salir'),
)


def mostrar_menu() -> None:
    """Presenta las opciones disponibles para arrancar el staging."""
    print()
    print('Elija una opción:')
    for numero, descripcion in OPCIONES_MENU:
        print(f'  {numero}) {descripcion}')
    print()


def pedir_opcion() -> str:
    """Lee la opción del menú hasta recibir una válida."""
    validas = {numero for numero, _descripcion in OPCIONES_MENU}
    while True:
        try:
            respuesta = input('Opción: ').strip()
        except EOFError:
            fallar('la entrada se cerró; ejecuta el script en una terminal')
        if respuesta in validas:
            return respuesta
        advertir(f'opción no válida: "{respuesta}". Elige 1, 2 o 3.')


def elegir_modo(opciones: argparse.Namespace) -> tuple[bool, bool, bool]:
    """
    Decide si se descarga el dump, si se reimporta y si se crea una cuenta.

    Los flags saltan el menú, pero no la pregunta por la cuenta cuando se puede
    preguntar: arrancar sin datos y sin usuario deja la aplicación inaccesible,
    y esa pregunta es la que evita el callejón sin salida.
    """
    crear_cuenta = opciones.crear_superusuario
    interactivo = sys.stdin.isatty()

    if opciones.sin_dump or opciones.reimportar:
        sin_dump = opciones.sin_dump
        if sin_dump and interactivo and not crear_cuenta:
            crear_cuenta = preguntar_si_no('¿crear usuario?')
        return sin_dump, opciones.reimportar, crear_cuenta

    if not interactivo:
        informar('entrada no interactiva; se arranca con dumpeo')
        return False, False, False

    mostrar_menu()
    eleccion = pedir_opcion()

    if eleccion == '3':
        informar('hasta luego')
        sys.exit(0)

    sin_dump = eleccion == '2'
    if sin_dump and not crear_cuenta:
        crear_cuenta = preguntar_si_no('¿crear usuario?')

    return sin_dump, False, crear_cuenta


def main() -> None:
    analizador = argparse.ArgumentParser(
        description='Levanta el entorno de staging local de Inventario ADR.'
    )
    analizador.add_argument(
        '--puerto', type=int, default=8000, help='puerto del servidor (8000 por omisión)'
    )
    analizador.add_argument(
        '--sin-dump', action='store_true',
        help='no intenta descargar el dump de producción'
    )
    analizador.add_argument(
        '--reimportar', action='store_true',
        help='vuelve a cargar el último dump aunque la base local ya tenga datos'
    )
    analizador.add_argument(
        '--crear-superusuario', action='store_true',
        help='crea o actualiza una cuenta administradora antes de arrancar'
    )
    opciones = analizador.parse_args()

    asegurar_entorno_virtual()

    titulo('Inventario ADR - staging local')

    verificar_entorno_seguro()

    sin_dump, reimportar, crear_cuenta = elegir_modo(opciones)

    if not hay_conexion_internet():
        fallar(
            'sin conexión a internet. El staging la necesita para el dump de '
            'producción y para cargar los estilos desde los CDN.'
        )
    informar('conexión a internet verificada')

    DIRECTORIO_DUMPS.mkdir(parents=True, exist_ok=True)
    DIRECTORIO_CORREOS.mkdir(parents=True, exist_ok=True)

    locales = credenciales_locales()
    locales['NAME'] = nombre_base_staging(locales['NAME'])
    informar(f'base de staging: {locales["NAME"]}')

    dump_elegido = None
    dump_es_nuevo = False

    if sin_dump:
        informar('descarga del dump omitida')
    else:
        titulo('Base de datos de producción')
        credenciales = obtener_credenciales_validas(permitir_preguntar=True)
        if credenciales is None:
            advertir('sin credenciales válidas no se puede descargar el dump')
        else:
            dump_elegido = descargar_dump(credenciales)
            dump_es_nuevo = dump_elegido is not None

    if dump_elegido is None:
        dump_elegido = dump_mas_reciente()
        if dump_elegido is not None:
            informar(f'se reutiliza el dump anterior: {dump_elegido.name}')
        else:
            advertir(
                'no hay ningún dump disponible; se arranca con la base local '
                'tal como está'
            )

    if not base_local_existe(locales):
        informar(f'la base local "{locales["NAME"]}" no existe; se crea vacía')
        crear_base_local(locales)

    tablas_actuales = contar_tablas_locales(locales)
    necesita_importar = dump_elegido is not None and (
        dump_es_nuevo or tablas_actuales == 0 or reimportar
    )

    if necesita_importar:
        titulo('Cargando datos')
        if tablas_actuales > 0:
            respaldar_base_local(locales)
        try:
            recrear_base_local(locales)
        except Exception as error:
            fallar(f'no se pudo recrear la base local: {error}')
        if not importar_dump(dump_elegido, locales):
            advertir('la base local puede quedar incompleta')
    else:
        informar(
            f'la base local ya tiene {tablas_actuales} tablas y no hay dump nuevo; '
            'se conserva el contenido actual'
        )

    preparar_django()

    if crear_cuenta:
        crear_superusuario(opciones.puerto)

    arrancar_servidor(opciones.puerto)


if __name__ == '__main__':
    main()
