                                               

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('replacements', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='teacher',
            name='hours_per_week',
            field=models.PositiveIntegerField(default=0),
        ),
    ]
