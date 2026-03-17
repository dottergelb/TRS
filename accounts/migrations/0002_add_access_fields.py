from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='can_calendar',
            field=models.BooleanField(default=False, verbose_name='Доступ к календарю'),
        ),
        migrations.AddField(
            model_name='customuser',
            name='can_teachers',
            field=models.BooleanField(default=False, verbose_name='Доступ к разделу «Учителя»'),
        ),
        migrations.AddField(
            model_name='customuser',
            name='can_editor',
            field=models.BooleanField(default=False, verbose_name='Доступ к разделу «Редактор»'),
        ),
        migrations.AddField(
            model_name='customuser',
            name='can_upload',
            field=models.BooleanField(default=False, verbose_name='Доступ к разделу «Загрузка»'),
        ),
        migrations.AddField(
            model_name='customuser',
            name='can_logs',
            field=models.BooleanField(default=False, verbose_name='Доступ к разделу «Логи»'),
        ),
        migrations.AddField(
            model_name='customuser',
            name='can_calls',
            field=models.BooleanField(default=False, verbose_name='Доступ к разделу «Звонки»'),
        ),
        migrations.AddField(
            model_name='customuser',
            name='can_users',
            field=models.BooleanField(default=False, verbose_name='Доступ к управлению пользователями'),
        ),
    ]