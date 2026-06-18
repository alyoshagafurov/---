"""Валидаторы по ТЗ: имя на сайте, почта без кириллицы, пароль 6–15 без кириллицы."""

import re

from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator

# Имя на сайте: только буквы (любого алфавита) и цифры, 1–15 символов.
_DISPLAY_NAME_RE = re.compile(r"^[^\W_]+$", re.UNICODE)

_CYRILLIC_RE = re.compile(r"[Ѐ-ӿ]")


def validate_display_name(value):
    value = value or ""
    if not (1 <= len(value) <= 15):
        raise ValidationError("Имя на сайте должно быть от 1 до 15 символов.")
    if not _DISPLAY_NAME_RE.match(value):
        raise ValidationError("В имени на сайте можно использовать только буквы и цифры.")


def validate_site_email(value):
    """Корректная почта без символов кириллицы."""
    value = value or ""
    if _CYRILLIC_RE.search(value):
        raise ValidationError("В почте нельзя использовать символы на русском.")
    EmailValidator(message="Укажите правильную Почту.")(value)


def validate_site_password(value):
    """Пароль 6–15 символов, без кириллицы (только ASCII)."""
    value = value or ""
    if not (6 <= len(value) <= 15):
        raise ValidationError(
            "Пароль указан неверно. Укажите пароль в соответствии с Правилами."
        )
    if not value.isascii():
        raise ValidationError(
            "Пароль указан неверно. Укажите пароль в соответствии с Правилами."
        )
