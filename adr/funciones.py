import re
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.conf import settings
from django.contrib import messages

# AQUÍ CREAREMOS DIFERENTES FUNCIONES QUE NOS VALIDEN CIERTOS ATRIBUTOS DE LOS MODELOS
# VALIDAR LONGITUD DEL RUT Y EL DÍGITO VERIFICADOR
def validar_rut(rut):
    rut = rut.replace(".", "").replace("-", "").lower()
    rut = rut[:-1] + "-" + rut[-1]
    rut = rut.split("-")
    cuerpo_rut = rut[0]
    digito_verificador = rut[1]
    suma = 0
    multiplo = 2
    for i in reversed(cuerpo_rut):
        suma += int(i) * multiplo
        multiplo += 1
        if multiplo == 8:
            multiplo = 2
    digito_calculado = 11 - (suma % 11)
    if digito_calculado == 11:
        digito_calculado = 0
    elif digito_calculado == 10:
        digito_calculado = "k"
    return str(digito_calculado) == digito_verificador

# Ejemplo de uso:
if __name__ == "__main__":
    rut = "11111111-1"  # Aquí coloca el RUT que quieres validar
    if validar_rut(rut):
        print("El RUT es válido.")
    else:
        print("El RUT no es válido.")

# FUNCIÓN PARA PASAR DE PLURAL A SINGULAR LOS GRUPOS
def plural_singular(plural):
    plural_singular = {
        'Usuario': 'Usuario',
        'ADR': 'ADR',
        'Operadores ADR': 'Operador ADR',
        'Auxiliares Operadores ADR': 'Auxiliar Operador ADR',
        'Alumnos en Práctica': 'Alumno en Práctica',
    }
    return plural_singular.get(plural, "error")

# FUNCION DE FILTRADO Y PAGINADO
from django.db.models import Q # Asegúrate de importar Q

def filtrar_y_paginar(request, model_class, search_fields, paginate_by): # Cambiado queryset a model_class y añadido search_fields
    filter_ubicacion = request.GET.get('filter_ubicacion', '')
    search_query = request.GET.get('search', '').strip()
    
    queryset = model_class.objects.all() # Empezamos con todos los objetos del modelo

    if filter_ubicacion:
        queryset = queryset.filter(ubicacion=filter_ubicacion)

    if search_query:
        q_objects = Q()
        for field in search_fields:
            q_objects |= Q(**{f"{field}__icontains": search_query})
        queryset = queryset.filter(q_objects)
    
    paginator = Paginator(queryset, paginate_by)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Obtener la lista de ubicaciones únicas para el filtro
    ubicaciones = queryset.values_list('ubicacion', flat=True).distinct()
    
    return page_obj, filter_ubicacion, ubicaciones


def enviar_correo_activacion_nuevo_usuario(request, user):
    try:
        from django.core.mail import send_mail
        from django.template.loader import render_to_string
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes
        from django.contrib.auth.tokens import default_token_generator
        from django.contrib.sites.shortcuts import get_current_site

        # Generamos los componentes seguros del token nativo de Django
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        current_site = get_current_site(request)
                
        # Contexto para las plantillas que ya tienes creadas
        contexto_email = {
            'email': user.email,
            'domain': current_site.domain,
            'site_name': current_site.name,
            'uid': uid,
            'user': user,
            'token': token,
            'protocol': 'https' if request.is_secure() else 'http',
        }

        # Cargamos tus plantillas existentes que están en 'templates/registration/'
        asunto = render_to_string('registration/password_reset_subject.txt', contexto_email).strip()
        cuerpo_txt = render_to_string('registration/password_reset_email.txt', contexto_email)
        cuerpo_html = render_to_string('registration/password_reset_email.html', contexto_email)

        # Enviamos el correo directamente usando el backend activo (Mailtrap o SendGrid)
        send_mail(
            subject=asunto,
            message=cuerpo_txt,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'soporte4310@gmail.com'),
            recipient_list=[user.email],
            html_message=cuerpo_html,
            fail_silently=False  # Cambiar a False ayuda a ver el error real si el SMTP falla
        )

    except Exception as e:
        # Si hay un error real de conexión SMTP con Mailtrap, aquí sí lo atraparás en la consola
        messages.warning(request, f'Usuario creado, pero falló el envío del correo de bienvenida: {str(e)}')