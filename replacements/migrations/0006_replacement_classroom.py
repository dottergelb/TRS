from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('replacements', '0005_lesson_is_active_activitylog'),
    ]

    operations = [
        migrations.AddField(
            model_name='replacement',
            name='replacement_classroom',
            field=models.CharField(max_length=50, blank=True, null=True, verbose_name='Кабинет замещения'),
        ),
    ]