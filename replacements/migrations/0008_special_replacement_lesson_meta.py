from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("replacements", "0007_replacement_production_and_special"),
    ]

    operations = [
        migrations.AddField(
            model_name="specialreplacement",
            name="lesson",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="special_replacements",
                to="replacements.lesson",
            ),
        ),
        migrations.AddField(
            model_name="specialreplacement",
            name="lesson_number",
            field=models.IntegerField(blank=True, null=True, verbose_name="Номер урока"),
        ),
        migrations.AddField(
            model_name="specialreplacement",
            name="start_time",
            field=models.TimeField(blank=True, null=True, verbose_name="Начало"),
        ),
        migrations.AddField(
            model_name="specialreplacement",
            name="end_time",
            field=models.TimeField(blank=True, null=True, verbose_name="Конец"),
        ),
        migrations.AddField(
            model_name="specialreplacement",
            name="classroom",
            field=models.CharField(blank=True, max_length=50, null=True, verbose_name="Кабинет"),
        ),
    ]
