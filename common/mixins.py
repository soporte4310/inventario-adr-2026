import os
import uuid
from PIL import Image
from django import forms
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from .utils import procesar_imagen_en_memoria, generar_thumbnail_en_memoria, MAX_PIXELS, MAX_UPLOAD_SIZE_MB
from .validators import validar_extension_imagen, validar_archivo_video


class ImageProcessingFormMixin:
    """
    Mixin para procesar imágenes (Main + 2 Thumbs) dentro del método save() de un ModelForm.
    Utiliza las funciones personalizadas: procesar_imagen_en_memoria y generar_thumbnail_en_memoria.
    Es dinámico: funciona para 'imagen', 'logo', 'foto_perfil', etc.
    """

    def clean(self):
        cleaned_data = super().clean()

        # Inspecciona automáticamente todos los campos del formulario
        for field_name, field in self.fields.items():
            if isinstance(field, forms.ImageField):
                archivo = self.files.get(field_name)

                # Solo validamos si es un archivo nuevo subido en el request
                # (evitamos validar instancias existentes FieldFile cuando no se cambia la imagen)
                if archivo and isinstance(archivo, UploadedFile):
                    try:
                        archivo.seek(0)
                        with Image.open(archivo) as img:
                            validar_extension_imagen(img)
                        archivo.seek(0)  # Rebobinar el puntero para el posterior procesamiento
                    except ValidationError as e:
                        # Extrae el texto limpio evitando listas anidadas
                        mensaje = e.messages[0] if hasattr(e, 'messages') else str(e)
                        self.add_error(field_name, mensaje)
                    except Exception:
                        self.add_error(field_name, "El archivo seleccionado está dañado o no es una imagen válida.")

        return cleaned_data
    

    def process_image_upload(self, instance, field_name='imagen', max_dim=(1024, 1024), crop=False, image_prefix=''):
        """
        Procesa la imagen subida, genera UUID, maneja transparencia, redimensiona y crea thumbnails.
        """
        # 1. Obtener el archivo del cleaned_data
        image_file = self.cleaned_data.get(field_name)

        # Si no hay nueva imagen, no hacemos nada
        if not image_file:
            return

        # 2. Generar nombres base con UUID
        ext = '.jpg'
        uuid_str = str(uuid.uuid4())
        # Construir el nombre base con el prefijo (si existe)
        base_name = f"{image_prefix}_{uuid_str}" if image_prefix else uuid_str
        
        main_name = f"{base_name}{ext}"
        medium_name = f"{base_name}_medium{ext}"
        small_name = f"{base_name}_small{ext}"

        # 3. Procesar Imagen Principal (Usando TU función)
        # Nota: procesar_imagen_en_memoria retorna un ContentFile
        processed_image = procesar_imagen_en_memoria(
            image_field=image_file,
            max_dimensions=max_dim,
            new_filename=main_name,
            crop_to_square=crop
        )

        # Asignamos la imagen procesada al campo cuyo nombre recibimos en 'field_name'
        # Equivalente a: instance.imagen = processed_image (pero dinámico)
        setattr(instance, field_name, processed_image)


        # 4. Generar Thumbnails
        image_file.seek(0)
        with Image.open(image_file) as img_obj:
            
            # --- THUMBNAIL MEDIUM ---
            # Construimos el nombre esperado del campo en el modelo
            field_med_name = f"{field_name}_thumb_medium"
            
            # Verificamos si el modelo realmente tiene ese campo antes de intentar guardar
            if hasattr(instance, field_med_name):
                thumb_med = generar_thumbnail_en_memoria(
                    image_obj=img_obj,
                    dimensions=(600, 600),
                    new_filename=medium_name
                )
                setattr(instance, field_med_name, thumb_med)

            # --- THUMBNAIL SMALL ---
            field_small_name = f"{field_name}_thumb_small"
            
            if hasattr(instance, field_small_name):
                thumb_small = generar_thumbnail_en_memoria(
                    image_obj=img_obj,
                    dimensions=(80, 80),
                    new_filename=small_name
                )
                setattr(instance, field_small_name, thumb_small)




class VideoValidationFormMixin:
    """
    Mixin para formularios que valida de forma automática cualquier
    campo FileField/CharField que reciba un archivo de video.
    """
    def clean(self):
        cleaned_data = super().clean()
        for field_name, field in self.fields.items():
            if isinstance(field, forms.FileField):
                archivo = self.files.get(field_name)
                if archivo and isinstance(archivo, UploadedFile):
                    try:
                        validar_archivo_video(archivo)
                    except ValidationError as e:
                        mensaje = e.messages[0] if hasattr(e, 'messages') else str(e)
                        self.add_error(field_name, mensaje)
        return cleaned_data




class DocumentProcessingFormMixin:
    """
    Mixin para procesar y renombrar documentos (PDF) dentro del método save() de un ModelForm.
    Garantiza nombres de archivo únicos mediante UUID.
    """

    def process_document_upload(self, instance, field_name, prefix=''):
        """
        Procesa el archivo subido, valida extensión y genera un nombre único con UUID.
        """
        doc_file = self.cleaned_data.get(field_name)

        # Si no hay un nuevo archivo, no hacemos nada
        if not doc_file:
            return

        # Validar extensión en el backend del Form por seguridad
        ext = os.path.splitext(doc_file.name)[1].lower()
        if ext != '.pdf':
            self.add_error(field_name, "El archivo debe ser estrictamente un formato PDF.")
            return

        # Generar nombre único con UUID
        uuid_str = str(uuid.uuid4())
        if prefix:
            new_filename = f"{prefix}_{uuid_str}{ext}"
        else:
            new_filename = f"{uuid_str}{ext}"

        # Sobrescribimos el nombre del archivo en memoria antes de guardarlo
        doc_file.name = new_filename

        # Asignamos dinámicamente el archivo procesado al campo de la instancia
        setattr(instance, field_name, doc_file)