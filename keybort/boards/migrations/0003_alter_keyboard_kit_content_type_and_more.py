# Generated by Django 5.0.7 on 2024-08-05 21:18

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('boards', '0002_boardspermissions_cannedkeycaps_cannedkit_cannedmod_and_more'),
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        migrations.AlterField(
            model_name='keyboard',
            name='kit_content_type',
            field=models.ForeignKey(limit_choices_to=models.Q(models.Q(('app_label', 'boards'), ('model', 'kit')), models.Q(('app_label', 'boards'), ('model', 'cannedkit')), _connector='OR'), on_delete=django.db.models.deletion.CASCADE, related_name='board_kit', to='contenttypes.contenttype'),
        ),
        migrations.AlterField(
            model_name='keyboard',
            name='kit_object_id',
            field=models.PositiveIntegerField(),
        ),
    ]
