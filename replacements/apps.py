from django.apps import AppConfig


class ReplacementsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "replacements"

    def ready(self):
                    
        from . import signals                                               
