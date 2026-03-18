"""
Módulo centralizado de templates HTML para correos de notificación.

Todas las notificaciones de la plataforma usan estas funciones para generar
correos HTML formales con el branding de Inventario ADR.
"""
from django.utils import timezone

# URL pública del logo ADR (alojado en Cloudinary)
LOGO_URL = "https://adr-inventario-tw1l.onrender.com/static/imagenes/adr_logo_email.png"


def _base_html(contenido_body: str) -> str:
    """
    Envuelve el contenido en la estructura base del email HTML.
    Incluye banner, contenido, y firma institucional.
    """
    return f"""\
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin:0; padding:0; background-color:#f4f4f7; font-family: 'Segoe UI', Arial, Helvetica, sans-serif;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#f4f4f7; padding:24px 0;">
    <tr>
      <td align="center">
        <!-- Contenedor principal -->
        <table role="presentation" width="600" cellpadding="0" cellspacing="0"
               style="max-width:600px; width:100%; background-color:#ffffff; border-radius:8px; overflow:hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.08);">

          <!-- Banner rojo -->
          <tr>
            <td style="background: linear-gradient(135deg, #dc2626, #991b1b); padding:20px 32px; text-align:center;">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td style="text-align:center;">
                    <span style="color:#ffffff; font-size:10px; letter-spacing:3px; text-transform:uppercase; font-weight:600;">
                      &#9632; Plataforma de Inventario ADR
                    </span>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Contenido -->
          <tr>
            <td style="padding:32px;">
              {contenido_body}
            </td>
          </tr>

          <!-- Separador -->
          <tr>
            <td style="padding:0 32px;">
              <hr style="border:none; border-top:1px solid #e5e7eb; margin:0;">
            </td>
          </tr>

          <!-- Firma -->
          <tr>
            <td style="padding:24px 32px;">
              <p style="margin:0 0 4px 0; font-size:14px; color:#374151;">
                <strong>Atte,</strong>
              </p>
              <p style="margin:0 0 2px 0; font-size:13px; color:#374151; font-weight:600;">
                Plataforma de Inventario ADR
              </p>
              <p style="margin:0 0 2px 0; font-size:12px; color:#6b7280;">
                Inacap Iquique
              </p>
              <p style="margin:0 0 12px 0; font-size:12px; color:#6b7280;">
                La Tirana #4310, Iquique
              </p>
              <img src="{LOGO_URL}" alt="ADR Logo" width="120"
                   style="display:block; max-width:120px; height:auto;">
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def _tabla_datos(datos: list[tuple[str, str]]) -> str:
    """
    Genera una tabla HTML estilizada con pares (etiqueta, valor).
    
    Args:
        datos: Lista de tuplas (etiqueta, valor), e.g. [('Activo', 'Mini PC'), ...]
    """
    filas = ""
    for i, (etiqueta, valor) in enumerate(datos):
        bg = "#f9fafb" if i % 2 == 0 else "#ffffff"
        filas += f"""\
          <tr style="background-color:{bg};">
            <td style="padding:10px 14px; font-size:13px; font-weight:600; color:#374151; border-bottom:1px solid #e5e7eb; width:40%;">
              {etiqueta}
            </td>
            <td style="padding:10px 14px; font-size:13px; color:#1f2937; border-bottom:1px solid #e5e7eb;">
              {valor or '—'}
            </td>
          </tr>"""

    return f"""\
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
           style="border:1px solid #e5e7eb; border-radius:6px; overflow:hidden; margin:16px 0;">
      {filas}
    </table>"""


def _badge_accion(accion: str) -> str:
    """Genera un badge de color según el tipo de acción."""
    colores = {
        'eliminación':   ('#fef2f2', '#991b1b', '#fecaca'),
        'eliminacion':   ('#fef2f2', '#991b1b', '#fecaca'),
        'restauración':  ('#f0fdf4', '#166534', '#bbf7d0'),
        'restauracion':  ('#f0fdf4', '#166534', '#bbf7d0'),
        'modificación':  ('#fefce8', '#854d0e', '#fef08a'),
        'modificacion':  ('#fefce8', '#854d0e', '#fef08a'),
        'creación':      ('#eff6ff', '#1e40af', '#bfdbfe'),
        'creacion':      ('#eff6ff', '#1e40af', '#bfdbfe'),
        'carga masiva':  ('#f5f3ff', '#5b21b6', '#ddd6fe'),
        'alerta':        ('#fff7ed', '#9a3412', '#fed7aa'),
        'backup':        ('#f0fdfa', '#115e59', '#99f6e4'),
    }

    bg, text, border = ('#f3f4f6', '#374151', '#d1d5db')  # default gris
    for key, colors in colores.items():
        if key in accion.lower():
            bg, text, border = colors
            break

    return f"""\
    <table role="presentation" cellpadding="0" cellspacing="0" style="margin:16px 0;">
      <tr>
        <td style="background-color:{bg}; border:1px solid {border}; border-radius:6px; padding:12px 20px;">
          <span style="font-size:14px; font-weight:700; color:{text};">{accion}</span>
        </td>
      </tr>
    </table>"""


# ─── Funciones públicas ──────────────────────────────────────


def notificacion_equipo(
    accion: str,
    usuario_nombre: str,
    usuario_grupo: str,
    modelo_nombre: str,
    datos_registro: list[tuple[str, str]],
    fecha: str | None = None,
) -> tuple[str, str]:
    """
    Genera HTML y texto plano para notificaciones de equipos
    (eliminar, restaurar, crear, editar).

    Returns:
        (html_content, plain_text_content)
    """
    if not fecha:
        fecha = timezone.localtime().strftime('%d/%m/%Y %H:%M')

    contenido = f"""\
    <p style="margin:0 0 8px 0; font-size:15px; color:#374151; line-height:1.6;">
      Estimados,
    </p>
    <p style="margin:0 0 16px 0; font-size:14px; color:#4b5563; line-height:1.6;">
      El usuario <strong>{usuario_nombre}</strong> (Grupo: <strong>{usuario_grupo}</strong>)
      ha realizado la siguiente acción en el inventario:
    </p>

    {_badge_accion(accion)}

    <table role="presentation" cellpadding="0" cellspacing="0" style="margin:0 0 8px 0;">
      <tr>
        <td style="font-size:12px; color:#6b7280; padding-right:16px;">
          <strong>Tipo de equipo:</strong> {modelo_nombre}
        </td>
        <td style="font-size:12px; color:#6b7280;">
          <strong>Fecha:</strong> {fecha}
        </td>
      </tr>
    </table>

    <p style="margin:16px 0 8px 0; font-size:14px; font-weight:600; color:#374151;">
      Datos del Registro:
    </p>

    {_tabla_datos(datos_registro)}"""

    html = _base_html(contenido)

    # Texto plano como fallback
    lineas_txt = [f"- {et}: {val}" for et, val in datos_registro]
    plain = (
        f"El usuario {usuario_nombre} (Grupo: {usuario_grupo}) ha realizado: {accion}\n"
        f"Tipo de equipo: {modelo_nombre}\n"
        f"Fecha: {fecha}\n\n"
        f"Datos del Registro:\n" + "\n".join(lineas_txt)
    )

    return html, plain


def notificacion_usuario(
    accion: str,
    ejecutor_nombre: str,
    datos_usuario: list[tuple[str, str]],
) -> tuple[str, str]:
    """
    Genera HTML y texto plano para notificaciones de gestión de usuarios
    (crear perfil, eliminar perfil, editar perfil).

    Returns:
        (html_content, plain_text_content)
    """
    fecha = timezone.localtime().strftime('%d/%m/%Y %H:%M')

    contenido = f"""\
    <p style="margin:0 0 8px 0; font-size:15px; color:#374151; line-height:1.6;">
      Estimados,
    </p>
    <p style="margin:0 0 16px 0; font-size:14px; color:#4b5563; line-height:1.6;">
      El usuario <strong>{ejecutor_nombre}</strong>
      ha realizado la siguiente acción:
    </p>

    {_badge_accion(accion)}

    <table role="presentation" cellpadding="0" cellspacing="0" style="margin:0 0 16px 0;">
      <tr>
        <td style="font-size:12px; color:#6b7280;">
          <strong>Fecha:</strong> {fecha}
        </td>
      </tr>
    </table>

    {_tabla_datos(datos_usuario)}"""

    html = _base_html(contenido)

    lineas_txt = [f"- {et}: {val}" for et, val in datos_usuario]
    plain = (
        f"El usuario {ejecutor_nombre} ha realizado: {accion}\n"
        f"Fecha: {fecha}\n\n"
        + "\n".join(lineas_txt)
    )

    return html, plain


def notificacion_carga_masiva(
    usuario_nombre: str,
    modelo_nombre: str,
    registros_nuevos: int,
) -> tuple[str, str]:
    """
    Genera HTML y texto plano para notificaciones de carga masiva (upload Excel).

    Returns:
        (html_content, plain_text_content)
    """
    fecha = timezone.localtime().strftime('%d/%m/%Y %H:%M')

    contenido = f"""\
    <p style="margin:0 0 8px 0; font-size:15px; color:#374151; line-height:1.6;">
      Estimados,
    </p>
    <p style="margin:0 0 16px 0; font-size:14px; color:#4b5563; line-height:1.6;">
      El usuario <strong>{usuario_nombre}</strong>
      ha realizado una carga masiva de datos:
    </p>

    {_badge_accion('Carga Masiva de Datos')}

    {_tabla_datos([
        ('Tipo de equipo', modelo_nombre),
        ('Registros añadidos', str(registros_nuevos)),
        ('Fecha', fecha),
    ])}"""

    html = _base_html(contenido)

    plain = (
        f"El usuario {usuario_nombre} ha realizado una carga masiva.\n"
        f"Modelo: {modelo_nombre}\n"
        f"Registros nuevos: {registros_nuevos}\n"
        f"Fecha: {fecha}\n"
    )

    return html, plain


def notificacion_alerta_login(
    intentos: int,
    username: str,
    ip: str,
    user_agent: str,
    fecha: str,
) -> tuple[str, str]:
    """
    Genera HTML y texto plano para alertas de intentos de login fallidos.

    Returns:
        (html_content, plain_text_content)
    """
    contenido = f"""\
    <p style="margin:0 0 8px 0; font-size:15px; color:#374151; line-height:1.6;">
      Estimados,
    </p>
    <p style="margin:0 0 16px 0; font-size:14px; color:#4b5563; line-height:1.6;">
      Se han detectado múltiples intentos fallidos de inicio de sesión en la plataforma:
    </p>

    {_badge_accion('Alerta de Seguridad')}

    {_tabla_datos([
        ('Intentos fallidos', str(intentos)),
        ('Usuario', username or '(vacío)'),
        ('Dirección IP', ip or 'desconocida'),
        ('Navegador', user_agent[:80] if user_agent else '—'),
        ('Fecha/Hora', fecha),
    ])}"""

    html = _base_html(contenido)

    plain = (
        f"ALERTA: {intentos} intentos fallidos de inicio de sesión\n"
        f"Usuario: {username or '(vacío)'}\n"
        f"IP: {ip or 'desconocida'}\n"
        f"User-Agent: {user_agent}\n"
        f"Fecha/Hora: {fecha}\n"
    )

    return html, plain


def notificacion_backup(
    fecha: str,
    categorias: list[tuple[str, int]],
    total_registros: int,
) -> tuple[str, str]:
    """
    Genera HTML y texto plano para el correo de backup/reporte semanal.

    Args:
        fecha: Fecha del backup (dd/mm/yyyy)
        categorias: Lista de tuplas (nombre_categoria, cantidad_registros)
        total_registros: Total de registros en todas las categorías

    Returns:
        (html_content, plain_text_content)
    """
    # Tabla de categorías con columnas Categoría | Registros
    filas = ""
    for i, (nombre, cantidad) in enumerate(categorias):
        bg = "#f9fafb" if i % 2 == 0 else "#ffffff"
        filas += f"""\
          <tr style="background-color:{bg};">
            <td style="padding:10px 14px; font-size:13px; color:#1f2937; border-bottom:1px solid #e5e7eb;">
              {nombre}
            </td>
            <td style="padding:10px 14px; font-size:13px; color:#1f2937; border-bottom:1px solid #e5e7eb; text-align:center; font-weight:600;">
              {cantidad}
            </td>
          </tr>"""

    # Fila total
    filas += f"""\
          <tr style="background-color:#dc2626;">
            <td style="padding:10px 14px; font-size:13px; color:#ffffff; font-weight:700;">
              Total de Registros
            </td>
            <td style="padding:10px 14px; font-size:13px; color:#ffffff; text-align:center; font-weight:700;">
              {total_registros}
            </td>
          </tr>"""

    tabla_categorias = f"""\
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
           style="border:1px solid #e5e7eb; border-radius:6px; overflow:hidden; margin:16px 0;">
      <tr style="background-color:#1f2937;">
        <td style="padding:10px 14px; font-size:12px; color:#ffffff; font-weight:700; text-transform:uppercase; letter-spacing:1px; border-bottom:2px solid #dc2626;">
          Categoría
        </td>
        <td style="padding:10px 14px; font-size:12px; color:#ffffff; font-weight:700; text-transform:uppercase; letter-spacing:1px; text-align:center; border-bottom:2px solid #dc2626;">
          Registros
        </td>
      </tr>
      {filas}
    </table>"""

    contenido = f"""\
    <p style="margin:0 0 8px 0; font-size:15px; color:#374151; line-height:1.6;">
      Estimados,
    </p>
    <p style="margin:0 0 16px 0; font-size:14px; color:#4b5563; line-height:1.6;">
      Adjunto encontrará el <strong>backup del inventario</strong> correspondiente al
      <strong>{fecha}</strong>, con el detalle de todos los equipos registrados en la plataforma.
    </p>

    {_badge_accion('Backup de Inventario')}

    <p style="margin:16px 0 8px 0; font-size:14px; font-weight:600; color:#374151;">
      Resumen por categoría:
    </p>

    {tabla_categorias}

    <p style="margin:16px 0 0 0; font-size:13px; color:#6b7280; line-height:1.5;">
      El archivo Excel adjunto contiene una hoja por cada categoría con el detalle completo de los registros.
    </p>"""

    html = _base_html(contenido)

    # Texto plano
    lineas_txt = [f"  - {nombre}: {cant} registros" for nombre, cant in categorias]
    plain = (
        f"Backup de Inventario — {fecha}\n\n"
        f"Adjunto encontrará el backup del inventario con {len(categorias)} categorías de equipos.\n\n"
        f"Resumen por categoría:\n" + "\n".join(lineas_txt) + "\n\n"
        f"Total de registros: {total_registros}\n"
    )

    return html, plain


def auto_html_from_plain_text(asunto: str, mensaje: str) -> str:
    """
    Convierte un mensaje de texto plano existente en HTML con el branding ADR.
    
    Parsea el texto plano buscando pares "campo: valor" (líneas con "-" o sin "-")
    y los presenta en una tabla estilizada. Cualquier texto que no sea un par
    se presenta como párrafo introductorio.

    Usado como fallback automático para notificaciones antiguas que no fueron
    migradas a las funciones dedicadas (notificacion_equipo, etc.).
    """
    import re

    lineas = mensaje.strip().splitlines()
    intro_lines = []
    datos = []

    for linea in lineas:
        linea_stripped = linea.strip()
        if not linea_stripped:
            continue

        # Detectar "- Campo: Valor" o "Campo: Valor"
        match = re.match(r'^-?\s*(.+?):\s*(.+)$', linea_stripped)
        if match:
            campo = match.group(1).strip()
            valor = match.group(2).strip()
            # Omitir campos repetitivos como "Acción" que ya van en el badge
            if campo.lower() in ('acción', 'accion'):
                datos.append(('__accion__', valor))
            else:
                datos.append((campo, valor))
        else:
            intro_lines.append(linea_stripped)

    # Extraer acción del badge si la tenemos
    accion_badge = asunto
    datos_filtrados = []
    for campo, valor in datos:
        if campo == '__accion__':
            accion_badge = valor
        else:
            datos_filtrados.append((campo, valor))

    # Construir el HTML
    intro_html = ""
    if intro_lines:
        for line in intro_lines:
            intro_html += f'<p style="margin:0 0 8px 0; font-size:14px; color:#4b5563; line-height:1.6;">{line}</p>\n'

    tabla_html = _tabla_datos(datos_filtrados) if datos_filtrados else ""

    contenido = f"""\
    <p style="margin:0 0 8px 0; font-size:15px; color:#374151; line-height:1.6;">
      Estimados,
    </p>

    {intro_html}

    {_badge_accion(accion_badge)}

    {tabla_html}"""

    return _base_html(contenido)
