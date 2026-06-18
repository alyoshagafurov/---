from django import template

register = template.Library()


@register.filter
def ru_plural(value, forms):
    """Русское склонение по числу.

    forms — три формы через запятую: «1,2-4,5+».
    Пример: {{ n|ru_plural:"публикация,публикации,публикаций" }}
    """
    try:
        n = int(value)
    except (TypeError, ValueError):
        return forms.split(",")[-1]
    one, few, many = (forms.split(",") + ["", "", ""])[:3]
    n = abs(n) % 100
    if 11 <= n <= 14:
        return many
    n %= 10
    if n == 1:
        return one
    if 2 <= n <= 4:
        return few
    return many
