from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    A template filter to access dictionary items by key.
    Usage: {{ dictionary|get_item:key }}
    Returns None if the input is not a dictionary.
    """
    if not isinstance(dictionary, dict):
        return None
    return dictionary.get(key)