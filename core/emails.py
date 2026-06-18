"""Отправка писем по ТЗ (регистрация, восстановление и смена пароля/почты)."""

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode


def _site_name():
    return settings.SITE_NAME


def _send(to_email, subject, body):
    send_mail(
        subject=subject,
        message=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[to_email],
        fail_silently=True,
    )


def send_welcome_email(user):
    """Письмо после регистрации. Тема: Аккаунт успешно зарегистрирован."""
    _send(
        user.email,
        "Аккаунт успешно зарегистрирован",
        f"Вы успешно зарегистрировали аккаунт на {_site_name()}.",
    )


def send_password_reset_email(request, user):
    """Письмо для восстановления пароля. Тема: Изменение пароля.

    Ссылка действительна 1 час (PASSWORD_RESET_TIMEOUT) и становится
    недействительной после смены пароля (генератор токена это учитывает).
    """
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    path = reverse("accounts:password_reset_confirm", args=[uidb64, token])
    url = request.build_absolute_uri(path)
    body = (
        "Приветствуем!\n\n"
        "Мы получили запрос на восстановление пароля.\n\n"
        "Чтобы восстановить пароль, перейдите по ссылке (действительна 1 час):\n"
        f"{url}\n\n"
        "Если вы не отправляли запрос на восстановление пароля, "
        "просто проигнорируйте это письмо."
    )
    _send(user.email, "Изменение пароля", body)


def send_password_reset_done_email(user):
    """Письмо после восстановления пароля. Тема: Пароль успешно изменен."""
    _send(
        user.email,
        "Пароль успешно изменен",
        "Ваш пароль был успешно изменён.\n\n"
        "Если вы не меняли ваш пароль, обратитесь в службу поддержки.",
    )


def send_password_changed_email(user):
    """Письмо при смене пароля в настройках. Тема: Пароль изменен."""
    _send(
        user.email,
        "Пароль изменен",
        "Пароль от вашего аккаунта успешно изменён.\n\n"
        "Если вы не вносили этого изменения, обратитесь в службу поддержки.",
    )


def send_email_changed_email(user, new_email):
    """Письмо при смене почты в настройках (на новую почту). Тема: Почта изменена."""
    _send(
        new_email,
        "Почта изменена",
        "Почта от вашего аккаунта успешно изменена.\n\n"
        "Если вы не вносили этого изменения, обратитесь в службу поддержки.",
    )
