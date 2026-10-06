from decimal import Decimal, InvalidOperation

from django import forms, template

register = template.Library()

_CHECKBOX = (forms.CheckboxInput, forms.CheckboxSelectMultiple, forms.RadioSelect)


@register.filter
def bootstrap(campo: forms.BoundField) -> forms.BoundField:
    """Aplica as classes do Bootstrap 5 ao widget de um campo de formulário."""
    widget = campo.field.widget
    if isinstance(widget, _CHECKBOX):
        classe = "form-check-input"
    elif isinstance(widget, forms.Select):
        classe = "form-select"
    else:
        classe = "form-control"
    if campo.errors:
        classe += " is-invalid"
    return campo.as_widget(attrs={"class": classe})


@register.filter
def eh_checkbox(campo: forms.BoundField) -> bool:
    return isinstance(campo.field.widget, forms.CheckboxInput)


@register.filter
def moeda(valor) -> str:
    """Formata um valor numérico como moeda brasileira (R$ 1.234,56)."""
    if valor in (None, ""):
        return "—"
    try:
        numero = Decimal(valor)
    except (InvalidOperation, TypeError, ValueError):
        return str(valor)
    texto = f"{numero:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {texto}"
