from django.db import migrations


def backfill_especialidad_fk(apps, schema_editor):
    Cita = apps.get_model('citas', 'Cita')
    Especialidad = apps.get_model('citas', 'Especialidad')

    especialidades_por_nombre = {
        especialidad.nombre: especialidad
        for especialidad in Especialidad.objects.all()
    }

    sin_match = []
    for cita in Cita.objects.all():
        clave = (cita.especialidad or '').strip().lower()
        especialidad = especialidades_por_nombre.get(clave)
        if especialidad is None:
            sin_match.append((cita.pk, cita.especialidad))
            continue
        cita.especialidad_fk = especialidad
        cita.save(update_fields=['especialidad_fk'])

    if sin_match:
        print(
            '\n[0007_backfill_especialidad_fk] ADVERTENCIA: '
            f'{len(sin_match)} cita(s) sin Especialidad correspondiente:'
        )
        for pk, valor in sin_match:
            print(f'  - Cita pk={pk} especialidad={valor!r}')


def revertir_backfill(apps, schema_editor):
    Cita = apps.get_model('citas', 'Cita')
    Cita.objects.update(especialidad_fk=None)


class Migration(migrations.Migration):

    dependencies = [
        ('citas', '0006_cita_especialidad_fk'),
    ]

    operations = [
        migrations.RunPython(backfill_especialidad_fk, revertir_backfill),
    ]
