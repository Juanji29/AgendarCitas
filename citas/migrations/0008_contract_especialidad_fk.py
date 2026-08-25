from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('citas', '0007_backfill_especialidad_fk'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='cita',
            name='especialidad',
        ),
        migrations.RenameField(
            model_name='cita',
            old_name='especialidad_fk',
            new_name='especialidad',
        ),
        migrations.AlterField(
            model_name='cita',
            name='especialidad',
            field=models.ForeignKey(
                null=False,
                on_delete=django.db.models.deletion.PROTECT,
                to='citas.especialidad',
            ),
        ),
    ]
