from django import template

register = template.Library()


@register.filter
def descarga_forzada(url):
    """
    Convierte una URL de Cloudinary en una que fuerza la descarga del archivo
    (Content-Disposition: attachment) en vez de abrirlo/reproducirlo en el
    navegador. Funciona insertando el flag fl_attachment que entiende
    Cloudinary justo después de '/upload/'.

    En local (FileSystemStorage) la URL no tiene '/upload/', así que esta
    función simplemente la devuelve sin tocar — el enlace sigue funcionando
    normal, solo sin la descarga forzada.
    """
    if '/upload/' in url:
        return url.replace('/upload/', '/upload/fl_attachment/', 1)
    return url
