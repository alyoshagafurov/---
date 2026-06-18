from django.conf import settings

from listings.models import Category


def site_globals(request):
    """Глобальные данные для всех шаблонов: название сайта, категории, счётчик сообщений."""
    unread = 0
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated:
        from messaging.models import Message, Conversation

        unread = (
            Message.objects.filter(
                conversation__in=Conversation.for_user(user), is_read=False
            )
            .exclude(sender=user)
            .count()
        )

    return {
        "SITE_NAME": settings.SITE_NAME,
        "nav_categories": Category.objects.all(),
        "unread_messages": unread,
    }
