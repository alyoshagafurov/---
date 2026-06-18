from django.contrib.auth import get_user_model
from django.utils import timezone

from .utils import get_client_ip


class LastSeenMiddleware:
    """Обновляет «был онлайн» и IP при каждом запросе авторизованного пользователя.

    Чтобы не писать в БД на каждый запрос, обновляем не чаще раза в минуту.
    """

    UPDATE_EVERY_SECONDS = 60

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            now = timezone.now()
            last = user.last_seen
            if last is None or (now - last).total_seconds() >= self.UPDATE_EVERY_SECONDS:
                ip = get_client_ip(request)
                get_user_model().objects.filter(pk=user.pk).update(
                    last_seen=now, last_login_ip=ip
                )
                user.last_seen = now
                user.last_login_ip = ip
        return self.get_response(request)
