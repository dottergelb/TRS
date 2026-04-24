from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver

from .audit import log_activity


@receiver(user_logged_in)
def _on_login(sender, request, user, **kwargs):
    log_activity(request, "auth_login", {"username": getattr(user, "username", ""), "user_id": getattr(user, "id", None)})


@receiver(user_logged_out)
def _on_logout(sender, request, user, **kwargs):
                      
    log_activity(request, "auth_logout", {"username": getattr(user, "username", "") if user else "", "user_id": getattr(user, "id", None) if user else None})
