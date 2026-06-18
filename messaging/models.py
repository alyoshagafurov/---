from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone


class Conversation(models.Model):
    """Диалог между двумя пользователями (один из них может быть админом).

    Пара участников уникальна: для пары (A, B) существует один диалог.
    Чтобы пара была однозначной, храним user_low/user_high по возрастанию id.
    """

    user_low = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="conversations_low",
    )
    user_high = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="conversations_high",
    )
    created_at = models.DateTimeField("Создан", default=timezone.now)
    last_message_at = models.DateTimeField("Последнее сообщение", default=timezone.now)

    class Meta:
        verbose_name = "Диалог"
        verbose_name_plural = "Диалоги"
        ordering = ["-last_message_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user_low", "user_high"], name="unique_conversation_pair"
            )
        ]

    def __str__(self):
        return f"Диалог {self.user_low} ↔ {self.user_high}"

    @staticmethod
    def normalize_pair(a, b):
        """Возвращает (low, high) по возрастанию id."""
        return (a, b) if a.pk < b.pk else (b, a)

    @classmethod
    def get_or_create_between(cls, a, b):
        low, high = cls.normalize_pair(a, b)
        obj, _ = cls.objects.get_or_create(user_low=low, user_high=high)
        return obj

    @classmethod
    def for_user(cls, user):
        return cls.objects.filter(Q(user_low=user) | Q(user_high=user))

    def other_user(self, user):
        return self.user_high if self.user_low_id == user.pk else self.user_low

    def unread_count_for(self, user):
        return self.messages.filter(is_read=False).exclude(sender=user).count()


class Message(models.Model):
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
        verbose_name="Диалог",
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_messages",
        verbose_name="Отправитель",
    )
    text = models.TextField("Текст")
    is_read = models.BooleanField("Прочитано", default=False)
    created_at = models.DateTimeField("Отправлено", default=timezone.now)

    class Meta:
        verbose_name = "Сообщение"
        verbose_name_plural = "Сообщения"
        ordering = ["created_at"]

    def __str__(self):
        return f"Сообщение от {self.sender}"
