# Generated by Django 5.0.7 on 2024-08-05 20:06

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('boards', '0001_initial'),
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        migrations.CreateModel(
            name='BoardsPermissions',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ],
            options={
                'permissions': (('can_upload_canned_data', 'Can bulk upload canned data'), ('can_delete_canned_data', 'Can delete canned data')),
            },
        ),
        migrations.CreateModel(
            name='CannedKeycaps',
            fields=[
                ('keycaps_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='boards.keycaps')),
            ],
            options={
                'verbose_name': 'Canned keycaps',
                'verbose_name_plural': 'Canned keycaps',
            },
            bases=('boards.keycaps',),
        ),
        migrations.CreateModel(
            name='CannedKit',
            fields=[
                ('kit_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='boards.kit')),
            ],
            bases=('boards.kit',),
        ),
        migrations.CreateModel(
            name='CannedMod',
            fields=[
                ('mod_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='boards.mod')),
            ],
            bases=('boards.mod',),
        ),
        migrations.CreateModel(
            name='CannedPlate',
            fields=[
                ('plate_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='boards.plate')),
            ],
            bases=('boards.plate',),
        ),
        migrations.CreateModel(
            name='CannedStabilizer',
            fields=[
                ('stabilizer_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='boards.stabilizer')),
            ],
            bases=('boards.stabilizer',),
        ),
        migrations.CreateModel(
            name='CannedSwitch',
            fields=[
                ('switch_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='boards.switch')),
            ],
            options={
                'verbose_name_plural': 'Canned switches',
            },
            bases=('boards.switch',),
        ),
        migrations.AlterModelOptions(
            name='inventory',
            options={'verbose_name_plural': 'Inventories'},
        ),
        migrations.AlterModelOptions(
            name='keycaps',
            options={'verbose_name': 'Keycaps', 'verbose_name_plural': 'Keycaps'},
        ),
        migrations.AlterModelOptions(
            name='switch',
            options={'verbose_name_plural': 'Switches'},
        ),
        migrations.RemoveField(
            model_name='keyboard',
            name='keycaps',
        ),
        migrations.RemoveField(
            model_name='keyboard',
            name='kit',
        ),
        migrations.RemoveField(
            model_name='keyboard',
            name='plate',
        ),
        migrations.RemoveField(
            model_name='keyboard',
            name='stabilizer',
        ),
        migrations.RemoveField(
            model_name='keyboard',
            name='switch',
        ),
        migrations.AddField(
            model_name='keyboard',
            name='keycaps_content_type',
            field=models.ForeignKey(limit_choices_to=models.Q(models.Q(('app_label', 'boards'), ('model', 'keycaps')), models.Q(('app_label', 'boards'), ('model', 'cannedkeycaps')), _connector='OR'), null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='board_keycaps', to='contenttypes.contenttype'),
        ),
        migrations.AddField(
            model_name='keyboard',
            name='keycaps_object_id',
            field=models.PositiveIntegerField(null=True),
        ),
        migrations.AddField(
            model_name='keyboard',
            name='kit_content_type',
            field=models.ForeignKey(limit_choices_to=models.Q(models.Q(('app_label', 'boards'), ('model', 'kit')), models.Q(('app_label', 'boards'), ('model', 'cannedkit')), _connector='OR'), null=True, on_delete=django.db.models.deletion.CASCADE, related_name='board_kit', to='contenttypes.contenttype'),
        ),
        migrations.AddField(
            model_name='keyboard',
            name='kit_object_id',
            field=models.PositiveIntegerField(null=True),
        ),
        migrations.AddField(
            model_name='keyboard',
            name='plate_content_type',
            field=models.ForeignKey(limit_choices_to=models.Q(models.Q(('app_label', 'boards'), ('model', 'plate')), models.Q(('app_label', 'boards'), ('model', 'cannedplate')), _connector='OR'), null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='board_plate', to='contenttypes.contenttype'),
        ),
        migrations.AddField(
            model_name='keyboard',
            name='plate_object_id',
            field=models.PositiveIntegerField(null=True),
        ),
        migrations.AddField(
            model_name='keyboard',
            name='stabilizer_content_type',
            field=models.ForeignKey(limit_choices_to=models.Q(models.Q(('app_label', 'boards'), ('model', 'stabilizer')), models.Q(('app_label', 'boards'), ('model', 'cannedstabilizer')), _connector='OR'), null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='board_stabilizer', to='contenttypes.contenttype'),
        ),
        migrations.AddField(
            model_name='keyboard',
            name='stabilizer_object_id',
            field=models.PositiveIntegerField(null=True),
        ),
        migrations.AddField(
            model_name='keyboard',
            name='switch_content_type',
            field=models.ForeignKey(limit_choices_to=models.Q(models.Q(('app_label', 'boards'), ('model', 'switch')), models.Q(('app_label', 'boards'), ('model', 'cannedswitch')), _connector='OR'), null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='board_switch', to='contenttypes.contenttype'),
        ),
        migrations.AddField(
            model_name='keyboard',
            name='switch_object_id',
            field=models.PositiveIntegerField(null=True),
        ),
        migrations.AlterField(
            model_name='kit',
            name='layout',
            field=models.CharField(blank=True, help_text='Refers to physical layout, not the individual caps placed on each switch (e.g. Dvorak, QZERTY).', max_length=255, null=True),
        ),
    ]
