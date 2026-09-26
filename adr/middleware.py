import threading
from django.urls import reverse
from django.shortcuts import redirect
_user = threading.local()

class CurrentUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _user.value = request.user
        response = self.get_response(request)
        return response

def get_current_user():
    """
    Devuelve el usuario autenticado de la request actual, o None.

    request.user puede ser un AnonymousUser (no autenticado); como los
    consumidores de esta función lo asignan directo a FKs nullable como
    AuditoriaActivo.usuario, hay que normalizarlo a None acá para no romper
    el guardado (AnonymousUser no es una instancia válida de User).
    """
    user = getattr(_user, 'value', None)
    if user is not None and not user.is_authenticated:
        return None
    return user
class ForcePasswordChangeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user
        path = request.path

        if user.is_authenticated:
            profile = getattr(user, "profile", None)
            if profile and profile.create_by_adr:
                allow = {
                    reverse("profile_password_change"),
                    reverse("logout"),
                }
                if path not in allow and not path.startswith(("/static/", "/media/")):
                    return redirect("profile_password_change")

        return self.get_response(request)