from django.db import migrations

ESPECIALIDADES = [
    {'nombre': 'cardiologia', 'duracion_minutos': 30, 'requiere_referido': True},
    {'nombre': 'pediatria', 'duracion_minutos': 25, 'requiere_referido': False},
    {'nombre': 'dermatologia', 'duracion_minutos': 20, 'requiere_referido': False},
    {'nombre': 'medicina general', 'duracion_minutos': 20, 'requiere_referido': False},
]


def seed_especialidades(apps, schema_editor):
    Especialidad = apps.get_model('citas', 'Especialidad')
    for datos in ESPECIALIDADES:
        Especialidad.objects.get_or_create(
            nombre=datos['nombre'],
            defaults={
                'duracion_minutos': datos['duracion_minutos'],
                'requiere_referido': datos['requiere_referido'],
            },
        )


def eliminar_especialidades(apps, schema_editor):
    Especialidad = apps.get_model('citas', 'Especialidad')
    nombres = [datos['nombre'] for datos in ESPECIALIDADES]
    Especialidad.objects.filter(nombre__in=nombres).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('citas', '0004_especialidad'),
    ]

    operations = [
        migrations.RunPython(seed_especialidades, eliminar_especialidades),
    ]
