from django.db import models


class SiteSettings(models.Model):
    """Единственная запись с редактируемыми текстами сайта (Правила, Контакты)."""

    rules_text = models.TextField(
        "Правила",
        blank=True,
        default="Здесь будут размещены правила сайта.",
    )
    contacts_text = models.TextField(
        "Контакты",
        blank=True,
        default=(
            "Служба поддержки. Если у вас есть вопросы, "
            "свяжитесь с Администрацией."
        ),
    )
    footer_year_start = models.PositiveIntegerField("Год начала (футер)", default=2021)

    class Meta:
        verbose_name = "Настройки сайта"
        verbose_name_plural = "Настройки сайта"

    def __str__(self):
        return "Настройки сайта"

    @classmethod
    def get(cls):
        obj = cls.objects.first()
        if obj is None:
            obj = cls.objects.create()
        return obj
