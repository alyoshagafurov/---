from django.conf import settings
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.db import models
from django.utils import timezone

from .validators import validate_display_name


class UserManager(BaseUserManager):
    """Менеджер пользователей: вход по e-mail вместо username."""

    use_in_migrations = True

    def _create_user(self, email, display_name, password, **extra):
        if not email:
            raise ValueError("Требуется e-mail.")
        email = self.normalize_email(email)
        user = self.model(email=email, display_name=display_name, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, display_name, password=None, **extra):
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._create_user(email, display_name, password, **extra)

    def create_superuser(self, email, display_name, password=None, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        if extra.get("is_staff") is not True:
            raise ValueError("У суперпользователя is_staff=True.")
        if extra.get("is_superuser") is not True:
            raise ValueError("У суперпользователя is_superuser=True.")
        return self._create_user(email, display_name, password, **extra)


def avatar_upload_to(instance, filename):
    return f"avatars/{instance.pk or 'new'}/{filename}"


class User(AbstractBaseUser, PermissionsMixin):
    """Пользователь сайта.

    Вход по e-mail и паролю (без подтверждения почты — по ТЗ).
    Имя на сайте — отдельное поле (1–15 символов, буквы и цифры).
    """

    email = models.EmailField("E-mail", unique=True)
    display_name = models.CharField(
        "Имя на сайте", max_length=15, validators=[validate_display_name]
    )
    avatar = models.ImageField(
        "Аватарка", upload_to=avatar_upload_to, blank=True, null=True
    )

    is_active = models.BooleanField("Активен", default=True)
    is_staff = models.BooleanField("Доступ в админку", default=False)

    date_joined = models.DateTimeField("Дата регистрации", default=timezone.now)
    last_seen = models.DateTimeField("Был онлайн", blank=True, null=True)
    registration_ip = models.GenericIPAddressField("IP регистрации", blank=True, null=True)
    last_login_ip = models.GenericIPAddressField("IP последнего входа", blank=True, null=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["display_name"]

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"
        ordering = ["date_joined"]

    def __str__(self):
        return self.display_name

    def get_short_name(self):
        return self.display_name

    def get_full_name(self):
        return self.display_name

    @property
    def is_online(self):
        if not self.last_seen:
            return False
        delta = timezone.now() - self.last_seen
        return delta.total_seconds() <= settings.ONLINE_TIMEOUT_SECONDS

    @property
    def avatar_url(self):
        if self.avatar:
            return self.avatar.url
        return None
