from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter
def stars(value):
    """Affiche n étoiles pleines (dorées) et 10-n étoiles vides (grises)."""
    try:
        value = int(value)
    except (ValueError, TypeError):
        value = 0
    full = '<span style="color:#ffca08;">&#9733;</span>' * max(0, min(value, 10))
    empty = '<span style="color:#ddd;">&#9734;</span>' * max(0, 10 - value)
    return mark_safe(full + empty)

@register.filter
def checkmark(value):
    """Retourne une coche verte ou une croix rouge selon le booléen."""
    if value:
        return mark_safe('<span style="color:green;font-size:18px;">&#10004;</span>')
    return mark_safe('<span style="color:red;font-size:18px;">&#10008;</span>')