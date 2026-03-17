from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("replacements", "0006_replacement_classroom"),
    ]

    operations = [
        migrations.AddField(
            model_name="replacement",
            name="production_necessity",
            field=models.BooleanField(default=False),
        ),
        migrations.CreateModel(
            name="SpecialReplacement",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("date", models.DateField()),
                ("class_group", models.CharField(max_length=50, verbose_name="Класс")),
                ("subject_name", models.CharField(max_length=100, verbose_name="Предмет")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "replacement_teacher",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="special_replacements",
                        to="replacements.teacher",
                    ),
                ),
            ],
            options={
                "db_table": "replacements_special_replacement",
            },
        ),
    ]
