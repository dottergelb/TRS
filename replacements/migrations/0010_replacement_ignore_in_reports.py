from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("replacements", "0009_alter_specialreplacement_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="replacement",
            name="ignore_in_reports",
            field=models.BooleanField(default=False, verbose_name="Не учитывать в замещениях"),
        ),
    ]
