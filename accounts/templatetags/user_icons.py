from django import template

from accounts.icon_service import get_icon_for_user, get_icon_for_display_name


register = template.Library()


@register.filter(name="user_icon")
def user_icon(user):
    return get_icon_for_user(user)


@register.filter(name="name_icon")
def name_icon(display_name):
    return get_icon_for_display_name(display_name)
