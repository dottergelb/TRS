from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("replacements", "0010_replacement_ignore_in_reports"),
    ]

    operations = [
        migrations.AddField(
            model_name="specialreplacement",
            name="original_teacher",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="special_original_replacements",
                to="replacements.teacher",
            ),
        ),
    ]
