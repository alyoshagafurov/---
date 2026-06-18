from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Conversation, Message

User = get_user_model()

DIALOGS_PER_PAGE = 200
MESSAGES_PER_PAGE = 100


@login_required
def inbox(request):
    convs = list(
        Conversation.for_user(request.user)
        .select_related("user_low", "user_high")
        .order_by("-last_message_at")
    )
    # Готовим данные диалога: собеседник, последнее сообщение, непрочитанные.
    items = []
    for c in convs:
        other = c.other_user(request.user)
        last = c.messages.order_by("-created_at").first()
        items.append(
            {
                "conversation": c,
                "other": other,
                "last": last,
                "unread": c.unread_count_for(request.user),
            }
        )
    page = Paginator(items, DIALOGS_PER_PAGE).get_page(request.GET.get("page"))
    return render(
        request,
        "messaging/inbox.html",
        {"page_obj": page, "dialogs_total": len(convs)},
    )


@login_required
def conversation(request, pk):
    conv = get_object_or_404(
        Conversation.objects.select_related("user_low", "user_high"), pk=pk
    )
    if request.user.pk not in (conv.user_low_id, conv.user_high_id):
        raise Http404()

    other = conv.other_user(request.user)

    if request.method == "POST":
        text = (request.POST.get("text") or "").strip()
        if text:
            Message.objects.create(
                conversation=conv, sender=request.user, text=text
            )
            conv.last_message_at = timezone.now()
            conv.save(update_fields=["last_message_at"])
        return redirect("messaging:conversation", pk=conv.pk)

    # Отмечаем входящие сообщения как прочитанные.
    conv.messages.filter(is_read=False).exclude(sender=request.user).update(
        is_read=True
    )

    msgs_qs = conv.messages.select_related("sender").order_by("created_at")
    page = Paginator(msgs_qs, MESSAGES_PER_PAGE).get_page(request.GET.get("page"))
    return render(
        request,
        "messaging/conversation.html",
        {"conversation": conv, "other": other, "page_obj": page},
    )


@login_required
def start_with(request, user_id):
    """Открыть (или создать) диалог с пользователем."""
    other = get_object_or_404(User, pk=user_id)
    if other.pk == request.user.pk:
        return redirect("messaging:inbox")
    conv = Conversation.get_or_create_between(request.user, other)
    return redirect("messaging:conversation", pk=conv.pk)


@login_required
def contact_admin(request):
    """«Связаться с администрацией» — диалог с администратором."""
    admin = (
        User.objects.filter(is_superuser=True).order_by("pk").first()
        or User.objects.filter(is_staff=True).order_by("pk").first()
    )
    if admin is None or admin.pk == request.user.pk:
        return redirect("messaging:inbox")
    conv = Conversation.get_or_create_between(request.user, admin)
    return redirect("messaging:conversation", pk=conv.pk)
