                                               

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Subject',
            fields=[
                ('id_subject', models.AutoField(primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=100)),
            ],
            options={
                'db_table': 'replacements_subject',
            },
        ),
        migrations.CreateModel(
            name='Teacher',
            fields=[
                ('id', models.AutoField(db_column='teacher_id', primary_key=True, serialize=False)),
                ('full_name', models.CharField(max_length=255, unique=True)),
                ('specialization', models.CharField(blank=True, max_length=255, null=True, verbose_name='Специализации')),
            ],
            options={
                'db_table': 'replacements_teacher',
            },
        ),
        migrations.CreateModel(
            name='Lesson',
            fields=[
                ('id', models.AutoField(db_column='lesson_id', primary_key=True, serialize=False)),
                ('lesson_number', models.IntegerField(verbose_name='Номер урока')),
                ('class_group', models.CharField(default='-', max_length=50, verbose_name='Класс')),
                ('classroom', models.CharField(default='---', max_length=50, verbose_name='Кабинет')),
                ('start_time', models.TimeField(verbose_name='Начало')),
                ('end_time', models.TimeField(verbose_name='Конец')),
                ('shift', models.IntegerField(verbose_name='Смена')),
                ('day_of_week', models.CharField(max_length=3, verbose_name='День недели')),
                ('subject', models.ForeignKey(db_column='subject_id_subject', on_delete=django.db.models.deletion.CASCADE, to='replacements.subject', verbose_name='Предмет')),
                ('teacher', models.ForeignKey(db_column='teacher_id', on_delete=django.db.models.deletion.CASCADE, to='replacements.teacher')),
            ],
            options={
                'ordering': ['day_of_week', 'lesson_number'],
            },
        ),
        migrations.CreateModel(
            name='Replacement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('confirmed', models.BooleanField(default=False)),
                ('lesson', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='replacements.lesson')),
                ('original_teacher', models.ForeignKey(db_column='original_teacher_id', on_delete=django.db.models.deletion.CASCADE, related_name='original_replacements', to='replacements.teacher')),
                ('replacement_teacher', models.ForeignKey(db_column='replacement_teacher_id', on_delete=django.db.models.deletion.CASCADE, related_name='replacement_replacements', to='replacements.teacher')),
            ],
            options={
                'db_table': 'replacements_replacement',
                'unique_together': {('lesson', 'date')},
            },
        ),
    ]
