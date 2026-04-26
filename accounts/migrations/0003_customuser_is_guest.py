from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_add_access_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="customuser",
            name="is_guest",
            field=models.BooleanField(
                default=False,
                verbose_name="Статус «Гость» (только просмотр)",
            ),
        ),
    ]
