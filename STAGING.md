# Staging local de Inventario ADR

**Autor:** Francisco Vera - Practicante Analista Programador
**Fecha de inicio:** 21-11-2026

Este documento explica cómo levantar una copia de la plataforma que funciona
entera dentro de tu computador, sin depender de Clever Cloud, Cloudinary,
SendGrid ni Render. La idea es simple: reemplazar cada servicio externo por algo
que ya vive en tu máquina, de modo que puedas trabajar aunque la red del
instituto bloquee puertos o el proveedor esté caído.

Antes de empezar, ten claro qué estás levantando. No es producción, aunque los
datos se parezcan. Es una copia desechable que puedes romper sin consecuencias.


## Qué reemplaza a qué

Cada servicio externo del proyecto tiene un sustituto local:

- **Clever Cloud (MySQL de producción).** Se reemplaza por tu MySQL local, cargado con el último volcado de datos que hayas descargado. Para conseguir ese volcado, el script pide las credenciales de producción y ejecuta `mysqldump`, que solo lee: nunca escribe ni borra en el servidor remoto.

- **SendGrid y Mailtrap (correo).** Ningún correo sale de la máquina. Un backend propio captura cada mensaje, lo guarda como archivo HTML en `staging/correos/` y lo muestra en pantalla. Lo importante de esto: cuando pides recuperar tu contraseña, la pantalla siguiente te dice "Esto es staging, aquí está el enlace" y te muestra el enlace real, clickeable. No tienes que ir a buscar nada a ninguna bandeja.

- **Cloudinary (logo de los correos).** La imagen se sirve desde `static/imagenes/` en lugar de la nube. El correo se ve igual, pero la imagen viene de tu disco.

- **Render (alojamiento).** Se usa `runserver` de Django, que ya viene con recarga automática al guardar archivos.

- **GitHub Actions (tareas programadas).** Los tres flujos automáticos del repositorio no corren en local. Si los necesitas, los ejecutas a mano con `manage.py`: `enviar_reporte_diario`, `enviar_reporte_semanal` y `generar_ciclo_revision`.


## Qué necesitas antes de arrancar

- Conexión a internet. Es obligatoria y el script lo verifica al inicio. Se usa para dos cosas: intentar el volcado de producción y permitir que las plantillas carguen sus estilos desde los CDN. Sin red, el script se detiene con un mensaje claro en vez de arrancar una página sin estilos.

- MySQL corriendo en tu máquina, con la base configurada en `.env` ya creada.

- El entorno virtual `venv/` del proyecto, con las dependencias instaladas.

- Opcional: las credenciales de Clever Cloud, si quieres traer datos frescos de producción.


## Cómo se usa

El punto de entrada es un solo archivo:

```
venv/bin/python iniciar_staging.py
```

Al ejecutarlo aparece un menú con tres opciones, y eliges tecleando el número:

- **1) Inicio con dumpeo.** Intenta conectarse a producción y descargar los datos. La primera vez muestra un banner que explica qué es el cluster de Clever Cloud, dónde están sus datos de conexión y por qué se necesitan. Después pide cinco datos, uno por uno: host, puerto, usuario, contraseña y nombre de la base. Si la conexión falla, el script lee el código de error de MySQL y **vuelve a preguntar solo los campos culpables**, no los cinco otra vez: si el error es de contraseña, repite usuario y contraseña; si es de base inexistente, repite solo el nombre de la base. Lo que aciertes se guarda en `staging/credenciales.env` para los próximos arranques.

- **2) Inicio sin dumpeo.** Se salta producción por completo y arranca con lo que ya tengas en tu base local o con el último volcado guardado. Enseguida te pregunta si quieres crear un usuario. Si respondes que sí, te pide nombre, correo y contraseña, y crea una cuenta administradora que entra al dashboard sin obligarte a cambiar la clave.

- **3) Salir.** Termina sin tocar nada.

Los flags existen para automatizar y tienen prioridad sobre el menú: `--sin-dump`, `--reimportar`, `--crear-superusuario` y `--puerto`. Si pasas cualquiera de ellos, el menú no aparece.


## Los flujos, en orden

**Flujo A: trayendo datos frescos desde producción.**

1. El script verifica que haya internet.
2. Si no hay credenciales guardadas, muestra el banner del primer dumpeo: explica que el cluster es el add-on MySQL de Clever Cloud, dónde están sus datos de conexión y que la operación es de solo lectura.
3. Pide los cinco datos uno por uno, en este orden: host, puerto, usuario, contraseña y nombre de la base. El puerto se valida como número entre 1 y 65535 antes de continuar.
4. Prueba la conexión contra el servidor remoto.
5. Si falla, traduce el código de error de MySQL a los campos concretos que hay que corregir y vuelve a preguntar solo esos. Un error de contraseña repite usuario y contraseña; una base inexistente repite solo el nombre; un puerto cerrado repite host y puerto. Hay cinco reintentos.
6. Cuando la conexión funciona, guarda los datos en `staging/credenciales.env`.
7. Ejecuta `mysqldump`, que solo lee, y guarda el resultado comprimido en `staging/dumps/`.
8. Respalda tu base de staging antes de tocarla, en `staging/dumps/respaldo_local_*.sql.gz`.
9. Vacía y recrea la base de staging.
10. Importa el volcado, descartando las sentencias `CREATE DATABASE` y `USE` para que las tablas caigan en tu base de staging y no en otra.
11. Aplica migraciones y reúne los estáticos.
12. Levanta el servidor.

**Flujo B: reutilizando el último volcado.**

1. El script verifica que haya internet.
2. No puede descargar nada, o elegiste la opción sin dumpeo.
3. Busca el volcado más reciente en `staging/dumps/`, ignorando los archivos `respaldo_local_*` porque esos son copias de tu propia base.
4. Si la base de staging está vacía, importa ese volcado. Si ya tiene datos y no pediste reimportar, la deja como está.
5. Aplica migraciones y levanta el servidor.

**Flujo C: sin volcado disponible.**

1. El script verifica que haya internet.
2. No hay credenciales válidas y no hay ningún volcado guardado.
3. Avisa que va a arrancar con la base de staging tal como esté.
4. Si la base no existe, la crea vacía. Si no tiene permiso para crearla, se detiene y te entrega el `CREATE DATABASE` exacto que debes ejecutar a mano.
5. Aplica migraciones y levanta el servidor.

**Flujo D: probando el correo de recuperación.**

1. Entras a la aplicación y pides recuperar tu contraseña.
2. El correo no sale de la máquina.
3. La pantalla siguiente te muestra el enlace de recuperación real, listo para hacer clic.
4. También queda una copia en `staging/correos/` como archivo HTML, por si quieres revisar el diseño del correo.


## Las salvaguardas que más importan

El script borra y recrea la base de datos, así que tiene tres candados.

**Primero, no arranca fuera de una rama de trabajo.** Antes de leer credenciales o tocar nada, comprueba tres cosas: que no exista la variable `RENDER`, que la rama git actual sea `staging`, `desarrollo`, `develop` o empiece con `practicantes-`, y que haya una terminal interactiva. Si alguna falla, se detiene con un mensaje que dice cuál. Así, aunque el archivo esté en producción, allí no se ejecuta.

**Segundo, el host tiene que ser local.** Antes de cualquier `DROP DATABASE`, revisa el host configurado en tu `.env`. Si no es `127.0.0.1`, `localhost` o `::1`, aborta sin tocar nada. Ese candado está justo antes del borrado, no al inicio del programa, para que ningún cambio hecho a mitad de ejecución pueda saltárselo.

**Tercero, el nombre de la base lleva sufijo.** El script nunca opera sobre el nombre que dice el `.env`. Siempre le añade `_staging`: si configuras `inventario_adr`, trabaja sobre `inventario_adr_staging`. Eso significa que la sentencia destructiva literalmente no puede nombrar la base de producción, ni siquiera si el host mintiera.

Los tres juntos: la rama impide arrancar en el lugar equivocado, el host impide apuntar a un servidor ajeno, y el sufijo impide que el borrado alcance el nombre real. El volcado de producción, además, va por una ruta de código que nunca pasa por la función que borra.

Por eso necesitas permisos sobre dos bases. `adr_dev` tiene privilegios sobre `inventario_adr` y sobre `inventario_adr_staging`, y Django apunta a la segunda cuando `ENTORNO=staging`.


## Qué se guarda y qué no se sube

El script deja tres cosas en disco, todas ignoradas por git:

- `staging/credenciales.env` con los datos de acceso a producción, con permisos de solo lectura y escritura para tu usuario.
- `staging/dumps/` con los volcados y los respaldos locales.
- `staging/correos/` con los correos capturados.

El `.gitignore` cubre `*.sql`, `*.sql.gz`, `*.gz` y las tres rutas anteriores. Un volcado de producción trae datos personales de funcionarios de INACAP, así que esto no es un detalle menor: si ese archivo llegara al repositorio compartido, sería una filtración. Si necesitas compartir un volcado, anonimízalo antes.


## Los archivos que componen el staging

- `iniciar_staging.py` en la raíz del proyecto. Es el orquestador y contiene toda la lógica.
- `core/settings/staging.py`. Hereda todo de `local.py` y solo cambia lo que difiere: backend de correo, carpeta de plantillas, logo y barra de depuración.
- `core/settings/__init__.py`. El selector que decide entre staging, local y producción según la variable `ENTORNO`.
- `staging/email_backend.py`. Captura los correos y los guarda en memoria y en disco.
- `staging/context_processors.py`. Expone el último correo capturado a las plantillas.
- `staging/templates/registration/password_reset_done.html`. La pantalla que muestra el enlace de recuperación.
- `adr/email_template.py`. Usa el logo local si el entorno de staging lo define.


## Detalles que conviene saber

- La variable `ENTORNO=staging` la exporta el propio script solo para el proceso del servidor. Tu `.env` de trabajo diario no se modifica, así que tu flujo normal con `manage.py` sigue intacto.

- Si abres otra terminal y corres `manage.py` mientras el staging está activo, esa terminal arranca en modo local normal, no en staging. Es el comportamiento esperado.

- La barra de depuración de Django está apagada en staging porque ocupaba media pantalla.

- El host `testserver` está permitido en staging para que la suite de pruebas pueda correr completa.

- Si la base de staging no existe, el script intenta crearla. Si el usuario de MySQL no tiene permiso para hacerlo, se detiene con instrucciones en vez de fallar más adelante con un error confuso.

- La base de staging es distinta de tu base de trabajo. Si configuras `inventario_adr`, el staging usa `inventario_adr_staging`. Tu base diaria queda intacta, pero tus usuarios no viajan con ella: hay que crearlos en la base nueva.


## Cuando algo sale mal

- **"sin conexión a internet".** El script se detiene a propósito. Conéctate y vuelve a intentarlo.

- **"EJECUCIÓN BLOQUEADA".** No estás en una rama permitida, o hay una variable `RENDER` definida, o no hay terminal interactiva. Cambia a `staging`, `desarrollo` o una rama `practicantes-*`.

- **"no se pudo conectar a producción".** Las credenciales están mal o la red bloquea el puerto 3306, algo común en redes institucionales. Prueba desde otra red o elige la opción sin dumpeo.

- **"la base configurada apunta a ... que no es esta máquina".** El `.env` tiene un `DB_HOST` remoto. Corrígelo a `127.0.0.1` antes de continuar. Esta es la salvaguarda funcionando.

- **La aplicación arranca pero no puedes entrar.** La base de staging no tiene usuarios. Usa la opción 2 del menú y responde que sí a "¿crear usuario?", o corre `ENTORNO=staging venv/bin/python manage.py createsuperuser`.

- **Los estilos se ven rotos.** Falta conexión o los CDN están bloqueados. La lógica de la aplicación sigue funcionando, pero Tailwind y Bootstrap no cargan.
