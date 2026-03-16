"""
Script para generar una nueva SECRET_KEY de Django
Ejecuta este script para obtener una nueva clave secreta
"""

from django.core.management.utils import get_random_secret_key

if __name__ == "__main__":
    secret_key = get_random_secret_key()
    print("\n" + "="*60)
    print("NUEVA SECRET_KEY GENERADA:")
    print("="*60)
    print(secret_key)
    print("="*60)
    print("\nCopia esta clave y úsala en tu nuevo archivo .env")
    print("="*60 + "\n")
