# Rediseña CicloRevision: de "un ciclo por mes calendario compartido" a
# "un ciclo por tipo de equipo, con fecha de inicio explícita", porque
# proyectores e impresoras se revisan con frecuencias distintas y una
# ronda puede saltarse (no siempre cae el mismo día del mes).
#
# La migración de datos abajo NO descarta nada: si un ciclo viejo llegara
# a tener revisiones de ambos tipos mezcladas, se separa en dos ciclos
# (uno por tipo) y se re-apuntan sus RevisionEquipo correspondientes.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def separar_ciclos_por_tipo(apps, schema_editor):
    CicloRevision = apps.get_model('mantencion', 'CicloRevision')
    RevisionEquipo = apps.get_model('mantencion', 'RevisionEquipo')

    for ciclo in CicloRevision.objects.all():
        tipos_presentes = list(
            RevisionEquipo.objects.filter(ciclo=ciclo)
            .values_list('equipo__tipo', flat=True)
            .distinct()
        )

        fecha_inicio = ciclo.fecha_generado.date() if ciclo.fecha_generado else None

        if not tipos_presentes:
            # Ciclo vacío (sin ninguna revisión asociada): lo dejamos como
            # PROY por convención, no afecta datos reales.
            ciclo.tipo = 'PROY'
            ciclo.fecha_inicio = fecha_inicio
            ciclo.save(update_fields=['tipo', 'fecha_inicio'])
            continue

        # El primer tipo reutiliza el ciclo original.
        ciclo.tipo = tipos_presentes[0]
        ciclo.fecha_inicio = fecha_inicio
        ciclo.save(update_fields=['tipo', 'fecha_inicio'])

        # Cualquier tipo adicional (ciclo viejo con proyectores E
        # impresoras mezclados) se separa a un ciclo nuevo propio.
        for tipo_extra in tipos_presentes[1:]:
            ciclo_nuevo = CicloRevision.objects.create(
                tipo=tipo_extra,
                fecha_inicio=fecha_inicio,
                generado_por_id=ciclo.generado_por_id,
            )
            RevisionEquipo.objects.filter(
                ciclo=ciclo, equipo__tipo=tipo_extra
            ).update(ciclo=ciclo_nuevo)


def revertir_separacion(apps, schema_editor):
    # No hay vuelta atrás sensata (fusionar ciclos separados podría violar
    # la unicidad anio/mes original); no se necesita en la práctica.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('mantencion', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # 1. Agregamos los campos nuevos, todavía opcionales.
        migrations.AddField(
            model_name='ciclorevision',
            name='fecha_inicio',
            field=models.DateField(null=True, verbose_name='Fecha de inicio'),
        ),
        migrations.AddField(
            model_name='ciclorevision',
            name='tipo',
            field=models.CharField(
                choices=[('PROY', 'Proyector'), ('IMPR', 'Impresora')],
                max_length=4, null=True, verbose_name='Tipo de equipo'
            ),
        ),
        migrations.RemoveConstraint(
            model_name='ciclorevision',
            name='unique_ciclo_anio_mes',
        ),

        # 2. Rellenamos los campos nuevos a partir de los datos existentes.
        migrations.RunPython(separar_ciclos_por_tipo, revertir_separacion),

        # 3. Ahora sí los dejamos obligatorios y quitamos anio/mes.
        migrations.AlterField(
            model_name='ciclorevision',
            name='fecha_inicio',
            field=models.DateField(verbose_name='Fecha de inicio'),
        ),
        migrations.AlterField(
            model_name='ciclorevision',
            name='tipo',
            field=models.CharField(
                choices=[('PROY', 'Proyector'), ('IMPR', 'Impresora')],
                max_length=4, verbose_name='Tipo de equipo'
            ),
        ),
        migrations.RemoveField(
            model_name='ciclorevision',
            name='anio',
        ),
        migrations.RemoveField(
            model_name='ciclorevision',
            name='mes',
        ),
        migrations.AlterField(
            model_name='ciclorevision',
            name='generado_por',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                to=settings.AUTH_USER_MODEL, verbose_name='Iniciado por',
                help_text='Vacío si el ciclo fue creado automáticamente por el comando programado.'
            ),
        ),
        migrations.AlterModelOptions(
            name='ciclorevision',
            options={'ordering': ['-fecha_inicio', '-fecha_generado'], 'verbose_name': 'Ciclo de Revisión', 'verbose_name_plural': 'Ciclos de Revisión'},
        ),
    ]
