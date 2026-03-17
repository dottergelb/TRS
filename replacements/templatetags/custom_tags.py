from django import template

register = template.Library()

@register.filter(name="get_item")
def get_item(dictionary, key):
    """Позволяет получить значение из словаря по ключу."""
    return dictionary.get(key, set())