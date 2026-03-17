from django.apps import AppConfig


class ReplacementsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "replacements"

    def ready(self):
        # noqa: F401
        from . import signals  # ensures auth login/logout auditing is wired
