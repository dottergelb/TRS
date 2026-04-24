                                               

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('replacements', '0002_teacher_hours_per_week'),
    ]

    operations = [
        migrations.CreateModel(
            name='ClassSchedule',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('class_group', models.CharField(max_length=10, verbose_name='Класс')),
                ('lesson_number', models.IntegerField(verbose_name='Номер урока')),
                ('start_time', models.TimeField(blank=True, null=True, verbose_name='Начало')),
                ('end_time', models.TimeField(blank=True, null=True, verbose_name='Конец')),
            ],
            options={
                'db_table': 'replacements_class_schedule',
                'unique_together': {('class_group', 'lesson_number')},
            },
        ),
    ]
