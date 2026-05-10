from django.apps import AppConfig


class InventarioConfig(AppConfig):
    name = 'inventario'

    def ready(self):
        import inventario.signals
