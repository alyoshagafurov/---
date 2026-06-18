from django import forms
from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.core.exceptions import ValidationError

from .validators import (
    validate_display_name,
    validate_site_email,
    validate_site_password,
)

User = get_user_model()


def _check_email_unique(email, exclude_pk=None):
    qs = User.objects.filter(email__iexact=email)
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)
    if qs.exists():
        raise ValidationError(
            "Данная почта уже Зарегистрирована, укажите другую почту."
        )


class RegistrationForm(forms.Form):
    display_name = forms.CharField(
        label="Имя на сайте",
        error_messages={"required": "Укажите имя на сайте."},
    )
    email = forms.CharField(
        label="Email",
        error_messages={"required": "Укажите правильную Почту."},
    )
    password1 = forms.CharField(
        label="Пароль",
        widget=forms.PasswordInput,
        error_messages={
            "required": "Пароль указан неверно. Укажите пароль в соответствии с Правилами."
        },
    )
    password2 = forms.CharField(
        label="Подтвердить пароль",
        widget=forms.PasswordInput,
        error_messages={"required": "Пароли не совпадают."},
    )
    terms = forms.BooleanField(
        label="С правилами ознакомлен",
        error_messages={
            "required": "Подтвердите, что ознакомлены с Правилами."
        },
    )

    def clean_display_name(self):
        value = (self.cleaned_data["display_name"] or "").strip()
        validate_display_name(value)
        return value

    def clean_email(self):
        value = (self.cleaned_data["email"] or "").strip()
        validate_site_email(value)
        _check_email_unique(value)
        return value

    def clean_password1(self):
        value = self.cleaned_data["password1"]
        validate_site_password(value)
        return value

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("password1")
        p2 = cleaned.get("password2")
        if p1 and p2 and p1 != p2:
            self.add_error("password2", "Пароли не совпадают.")
        return cleaned

    def save(self, commit=True):
        user = User(
            email=self.cleaned_data["email"],
            display_name=self.cleaned_data["display_name"],
        )
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class LoginForm(forms.Form):
    email = forms.CharField(label="Email")
    password = forms.CharField(label="Пароль", widget=forms.PasswordInput)

    def __init__(self, *args, request=None, **kwargs):
        self.request = request
        self.user = None
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        email = (cleaned.get("email") or "").strip()
        password = cleaned.get("password")
        if email and password:
            user = authenticate(self.request, username=email, password=password)
            if user is None:
                raise ValidationError("Логин или Пароль указан неверно.")
            self.user = user
        return cleaned


class PasswordResetRequestForm(forms.Form):
    email = forms.CharField(
        label="Адрес электронной почты",
        required=False,
    )

    def clean_email(self):
        value = (self.cleaned_data.get("email") or "").strip()
        if not value:
            raise ValidationError("Почта не указана. Укажите Почту.")
        # Неверный формат ИЛИ почта не зарегистрирована — один и тот же текст.
        try:
            validate_site_email(value)
        except ValidationError:
            raise ValidationError("Укажите верную Почту.")
        if not User.objects.filter(email__iexact=value).exists():
            raise ValidationError("Укажите верную Почту.")
        return value

    def get_user(self):
        return User.objects.filter(email__iexact=self.cleaned_data["email"]).first()


class SetPasswordForm(forms.Form):
    """Установка нового пароля (восстановление по ссылке)."""

    password1 = forms.CharField(
        label="Пароль",
        widget=forms.PasswordInput,
        error_messages={
            "required": "Пароль указан неверно. Укажите пароль в соответствии с Правилами."
        },
    )
    password2 = forms.CharField(
        label="Повторить пароль",
        widget=forms.PasswordInput,
        error_messages={"required": "Пароли не совпадают."},
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_password1(self):
        value = self.cleaned_data["password1"]
        validate_site_password(value)
        return value

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("password1")
        p2 = cleaned.get("password2")
        if p1 and p2 and p1 != p2:
            self.add_error("password2", "Пароли не совпадают.")
        return cleaned

    def save(self):
        self.user.set_password(self.cleaned_data["password1"])
        self.user.save()
        return self.user


# --- Настройки --------------------------------------------------------------


class AvatarForm(forms.Form):
    avatar = forms.ImageField(label="Аватарка")

    def clean_avatar(self):
        image = self.cleaned_data["avatar"]
        size = image.size
        if size < settings.AVATAR_MIN_SIZE:
            raise ValidationError("Минимальный размер 30 Кбайт.")
        if size > settings.AVATAR_MAX_SIZE:
            raise ValidationError("Максимальный 3 Мб.")
        return image


class ChangeNameForm(forms.Form):
    display_name = forms.CharField(
        label="Имя на сайте",
        error_messages={"required": "Укажите имя на сайте."},
    )

    def clean_display_name(self):
        value = (self.cleaned_data["display_name"] or "").strip()
        if not value:
            raise ValidationError("Укажите имя на сайте")
        validate_display_name(value)
        return value


class ChangePasswordForm(forms.Form):
    current_password = forms.CharField(
        label="Текущий пароль", widget=forms.PasswordInput
    )
    password1 = forms.CharField(label="Новый пароль", widget=forms.PasswordInput)
    password2 = forms.CharField(
        label="Подтвердить пароль", widget=forms.PasswordInput
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_current_password(self):
        value = self.cleaned_data["current_password"]
        if not self.user.check_password(value):
            raise ValidationError("Укажите ваш Текущий пароль.")
        return value

    def clean_password1(self):
        value = self.cleaned_data["password1"]
        validate_site_password(value)
        return value

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("password1")
        p2 = cleaned.get("password2")
        if p1 and p2 and p1 != p2:
            self.add_error("password2", "Пароли не совпадают.")
        return cleaned

    def save(self):
        self.user.set_password(self.cleaned_data["password1"])
        self.user.save()
        return self.user


class ChangeEmailForm(forms.Form):
    new_email = forms.CharField(label="Новая почта")
    current_password = forms.CharField(
        label="Текущий пароль", widget=forms.PasswordInput
    )
    confirm_password = forms.CharField(
        label="Подтвердить пароль", widget=forms.PasswordInput
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_new_email(self):
        value = (self.cleaned_data["new_email"] or "").strip()
        try:
            validate_site_email(value)
        except ValidationError:
            raise ValidationError("Укажите правильную Почту.")
        _check_email_unique(value, exclude_pk=self.user.pk)
        return value

    def clean_current_password(self):
        value = self.cleaned_data["current_password"]
        if not self.user.check_password(value):
            raise ValidationError("Укажите ваш Текущий пароль.")
        return value

    def clean(self):
        cleaned = super().clean()
        cur = cleaned.get("current_password")
        conf = cleaned.get("confirm_password")
        if cur and conf and cur != conf:
            self.add_error("confirm_password", "Пароли не совпадают.")
        return cleaned

    def save(self):
        self.user.email = self.cleaned_data["new_email"]
        self.user.save(update_fields=["email"])
        return self.user
