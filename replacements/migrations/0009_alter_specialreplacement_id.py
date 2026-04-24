                                               

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('replacements', '0008_special_replacement_lesson_meta'),
    ]

    operations = [
        migrations.AlterField(
            model_name='specialreplacement',
            name='id',
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'),
        ),
    ]
