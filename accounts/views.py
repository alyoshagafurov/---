from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.tokens import default_token_generator
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.views.decorators.http import require_POST

from core.emails import (
    send_email_changed_email,
    send_password_changed_email,
    send_password_reset_done_email,
    send_password_reset_email,
    send_welcome_email,
)
from listings.models import Favorite, Listing

from .forms import (
    AvatarForm,
    ChangeEmailForm,
    ChangeNameForm,
    ChangePasswordForm,
    LoginForm,
    PasswordResetRequestForm,
    RegistrationForm,
    SetPasswordForm,
)
from .utils import get_client_ip, mask_email

User = get_user_model()

ACCOUNT_PER_PAGE = 50
FAVORITES_PER_PAGE = 100


# --- Регистрация / вход / выход --------------------------------------------


def register(request):
    if request.user.is_authenticated:
        return redirect("accounts:my_account")

    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.registration_ip = get_client_ip(request)
            user.last_login_ip = user.registration_ip
            user.save()
            send_welcome_email(user)
            login(request, user)
            return redirect("accounts:my_account")
    else:
        form = RegistrationForm()
    return render(request, "accounts/register.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("accounts:my_account")

    if request.method == "POST":
        form = LoginForm(request.POST, request=request)
        if form.is_valid():
            user = form.user
            user.last_login_ip = get_client_ip(request)
            user.save(update_fields=["last_login_ip"])
            login(request, user)
            next_url = request.GET.get("next") or request.POST.get("next")
            return redirect(next_url or "accounts:my_account")
    else:
        form = LoginForm(request=request)
    return render(request, "accounts/login.html", {"form": form})


@require_POST
def logout_view(request):
    logout(request)
    return redirect("core:home")


# --- Восстановление пароля --------------------------------------------------


def password_reset_request(request):
    sent = False
    if request.method == "POST":
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            user = form.get_user()
            if user:
                send_password_reset_email(request, user)
            sent = True
    else:
        form = PasswordResetRequestForm()
    return render(
        request,
        "accounts/password_reset_request.html",
        {"form": form, "sent": sent},
    )


def _get_user_from_uid(uidb64):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        return User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        return None


def password_reset_confirm(request, uidb64, token):
    user = _get_user_from_uid(uidb64)
    valid = user is not None and default_token_generator.check_token(user, token)

    if not valid:
        return render(
            request, "accounts/password_reset_confirm.html", {"valid": False}
        )

    done = False
    form = SetPasswordForm(user)
    if request.method == "POST":
        form = SetPasswordForm(user, request.POST)
        if form.is_valid():
            form.save()
            send_password_reset_done_email(user)
            done = True
            form = None

    return render(
        request,
        "accounts/password_reset_confirm.html",
        {"valid": True, "form": form, "done": done},
    )


# --- Профиль ----------------------------------------------------------------


def _paginate(request, queryset, per_page):
    paginator = Paginator(queryset, per_page)
    return paginator.get_page(request.GET.get("page"))


def my_account(request):
    if not request.user.is_authenticated:
        return redirect("accounts:login")
    return _render_profile(request, request.user, is_owner=True)


def user_profile(request, pk):
    profile = get_object_or_404(User, pk=pk)
    if request.user.is_authenticated and request.user.pk == profile.pk:
        return redirect("accounts:my_account")
    return _render_profile(request, profile, is_owner=False)


def _render_profile(request, profile, is_owner):
    viewer = request.user
    is_admin = viewer.is_authenticated and viewer.is_staff
    can_see_all = is_owner or is_admin

    tab = request.GET.get("tab", "published")
    if tab not in {"published", "queue", "deleted"}:
        tab = "published"
    if not can_see_all:
        tab = "published"

    status_map = {
        "published": Listing.Status.PUBLISHED,
        "queue": Listing.Status.QUEUE,
        "deleted": Listing.Status.DELETED,
    }
    listings_qs = profile.listings.filter(status=status_map[tab]).prefetch_related(
        "photos"
    )
    page = _paginate(request, listings_qs, ACCOUNT_PER_PAGE)

    context = {
        "profile": profile,
        "is_owner": is_owner,
        "is_admin_view": is_admin and not is_owner,
        "can_see_all": can_see_all,
        "can_see_reg_date": can_see_all,
        "tab": tab,
        "page_obj": page,
        "published_total": profile.listings.filter(
            status=Listing.Status.PUBLISHED
        ).count(),
    }
    return render(request, "accounts/profile.html", context)


# --- Настройки --------------------------------------------------------------


@login_required
def settings_index(request):
    return render(request, "accounts/settings/index.html")


@login_required
def settings_avatar(request):
    saved = False
    if request.method == "POST":
        form = AvatarForm(request.POST, request.FILES)
        if form.is_valid():
            request.user.avatar = form.cleaned_data["avatar"]
            request.user.save(update_fields=["avatar"])
            saved = True
    else:
        form = AvatarForm()
    return render(
        request, "accounts/settings/avatar.html", {"form": form, "saved": saved}
    )


@login_required
def settings_name(request):
    saved = False
    if request.method == "POST":
        form = ChangeNameForm(request.POST)
        if form.is_valid():
            request.user.display_name = form.cleaned_data["display_name"]
            request.user.save(update_fields=["display_name"])
            saved = True
    else:
        form = ChangeNameForm(initial={"display_name": request.user.display_name})
    return render(
        request, "accounts/settings/name.html", {"form": form, "saved": saved}
    )


@login_required
def settings_password(request):
    saved = False
    if request.method == "POST":
        form = ChangePasswordForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            send_password_changed_email(request.user)
            # Сохраняем сессию активной после смены пароля.
            from django.contrib.auth import update_session_auth_hash

            update_session_auth_hash(request, request.user)
            saved = True
            form = ChangePasswordForm(request.user)
    else:
        form = ChangePasswordForm(request.user)
    return render(
        request, "accounts/settings/password.html", {"form": form, "saved": saved}
    )


@login_required
def settings_email(request):
    saved = False
    if request.method == "POST":
        form = ChangeEmailForm(request.user, request.POST)
        if form.is_valid():
            new_email = form.cleaned_data["new_email"]
            form.save()
            send_email_changed_email(request.user, new_email)
            saved = True
            form = ChangeEmailForm(request.user)
    else:
        form = ChangeEmailForm(request.user)
    return render(
        request,
        "accounts/settings/email.html",
        {"form": form, "saved": saved, "current_email": mask_email(request.user.email)},
    )


# --- Избранное --------------------------------------------------------------


@login_required
def favorites(request):
    favs = (
        Favorite.objects.filter(user=request.user)
        .select_related("listing")
        .prefetch_related("listing__photos")
        .order_by("-created_at")
    )
    listings = [f.listing for f in favs]
    page = _paginate(request, listings, FAVORITES_PER_PAGE)
    return render(request, "accounts/favorites.html", {"page_obj": page})
