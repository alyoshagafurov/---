from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify

# Транслитерация кириллицы для адресов категорий (slug).
_TRANSLIT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
    "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "h", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sch",
    "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
}


def transliterate(text):
    result = []
    for ch in text.lower():
        result.append(_TRANSLIT.get(ch, ch))
    return "".join(result)


class Category(models.Model):
    """Категория публикаций. Управляется из админки (название можно менять)."""

    name = models.CharField("Название", max_length=80, unique=True)
    slug = models.SlugField("Адрес", max_length=120, unique=True, blank=True)
    position = models.PositiveIntegerField("Порядок", default=0)
    created_at = models.DateTimeField("Создана", default=timezone.now)

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"
        ordering = ["position", "name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(transliterate(self.name), allow_unicode=False) or "category"
            slug = base
            i = 2
            while Category.objects.exclude(pk=self.pk).filter(slug=slug).exists():
                slug = f"{base}-{i}"
                i += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("listings:category", args=[self.slug])

    @property
    def published_count(self):
        return self.listings.filter(status=Listing.Status.PUBLISHED).count()


class Listing(models.Model):
    """Публикация (объявление). Единая структура для всех категорий:
    название, описание, фото (по ТЗ)."""

    class Status(models.TextChoices):
        QUEUE = "queue", "В очереди"
        PUBLISHED = "published", "Опубликован"
        DELETED = "deleted", "Удалено"

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="listings",
        verbose_name="Автор",
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="listings",
        verbose_name="Категория",
    )
    title = models.CharField("Название", max_length=35)
    description = models.TextField("Описание")
    status = models.CharField(
        "Статус", max_length=12, choices=Status.choices, default=Status.QUEUE
    )

    created_at = models.DateTimeField("Опубликован", default=timezone.now)
    updated_at = models.DateTimeField("Изменён", auto_now=True)
    published_at = models.DateTimeField("Дата публикации", blank=True, null=True)
    deleted_at = models.DateTimeField("Дата удаления", blank=True, null=True)

    class Meta:
        verbose_name = "Публикация"
        verbose_name_plural = "Публикации"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("listings:detail", args=[self.pk])

    @property
    def is_published(self):
        return self.status == self.Status.PUBLISHED

    @property
    def cover(self):
        return self.photos.first()


def listing_photo_upload_to(instance, filename):
    return f"listings/{instance.listing_id}/{filename}"


class ListingPhoto(models.Model):
    listing = models.ForeignKey(
        Listing, on_delete=models.CASCADE, related_name="photos", verbose_name="Публикация"
    )
    image = models.ImageField("Фото", upload_to=listing_photo_upload_to)
    position = models.PositiveIntegerField("Порядок", default=0)
    uploaded_at = models.DateTimeField("Загружено", default=timezone.now)

    class Meta:
        verbose_name = "Фото публикации"
        verbose_name_plural = "Фото публикаций"
        ordering = ["position", "id"]

    def __str__(self):
        return f"Фото #{self.pk}"


class Favorite(models.Model):
    """Избранные публикации пользователя."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="favorites",
        verbose_name="Пользователь",
    )
    listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name="favorited_by",
        verbose_name="Публикация",
    )
    created_at = models.DateTimeField("Добавлено", default=timezone.now)

    class Meta:
        verbose_name = "Избранное"
        verbose_name_plural = "Избранное"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "listing"], name="unique_favorite"
            )
        ]

    def __str__(self):
        return f"{self.user} → {self.listing}"


class Complaint(models.Model):
    """Жалоба на публикацию."""

    listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name="complaints",
        verbose_name="Публикация",
    )
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="complaints",
        verbose_name="Кто пожаловался",
    )
    text = models.TextField("Текст жалобы")
    created_at = models.DateTimeField("Добавлена", default=timezone.now)

    class Meta:
        verbose_name = "Жалоба"
        verbose_name_plural = "Жалобы"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Жалоба на {self.listing} от {self.reporter}"
