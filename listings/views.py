from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import ListingForm
from .models import Category, Complaint, Favorite, Listing, ListingPhoto

CATEGORY_PER_PAGE = 100


# --- Вспомогательные функции ------------------------------------------------


def _validate_photo_files(files):
    """Проверяет список загруженных фото. Возвращает текст ошибки или None."""
    if len(files) < settings.LISTING_MIN_PHOTOS:
        return "Добавьте хотя бы 1 Фото"
    if len(files) > settings.LISTING_MAX_PHOTOS:
        return "Можно добавить не более 15 фото."
    for f in files:
        if f.size < settings.PHOTO_MIN_SIZE:
            return "Размер фото должен быть не менее 30 Кбайт."
        if f.size > settings.PHOTO_MAX_SIZE:
            return "Размер фото должен быть не более 3 Мб."
    return None


def _paginate(request, queryset, per_page):
    return Paginator(queryset, per_page).get_page(request.GET.get("page"))


# --- Категории --------------------------------------------------------------


def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug)
    qs = (
        category.listings.filter(status=Listing.Status.PUBLISHED)
        .select_related("author")
        .prefetch_related("photos")
    )
    page = _paginate(request, qs, CATEGORY_PER_PAGE)
    return render(
        request,
        "listings/category.html",
        {"category": category, "page_obj": page},
    )


# --- Добавление публикации --------------------------------------------------


@login_required
def listing_create(request):
    photo_error = None
    if request.method == "POST":
        form = ListingForm(request.POST)
        files = request.FILES.getlist("photos")
        photo_error = _validate_photo_files(files)
        terms_ok = bool(request.POST.get("terms"))
        terms_error = None if terms_ok else "Укажите что с правилами ознакомлены"

        if form.is_valid() and photo_error is None and terms_error is None:
            listing = form.save(commit=False)
            listing.author = request.user
            listing.status = Listing.Status.QUEUE
            listing.save()
            for i, f in enumerate(files):
                ListingPhoto.objects.create(listing=listing, image=f, position=i)
            return render(
                request,
                "listings/create_done.html",
                {"listing": listing},
            )
    else:
        form = ListingForm()
        terms_error = None

    return render(
        request,
        "listings/create.html",
        {"form": form, "photo_error": photo_error, "terms_error": terms_error},
    )


# --- Просмотр публикации ----------------------------------------------------


def listing_detail(request, pk):
    listing = get_object_or_404(
        Listing.objects.select_related("author", "category").prefetch_related("photos"),
        pk=pk,
    )
    viewer = request.user
    is_owner = viewer.is_authenticated and viewer.pk == listing.author_id
    is_admin = viewer.is_authenticated and viewer.is_staff

    # Доступ к не опубликованным публикациям — только автору и админу.
    if listing.status != Listing.Status.PUBLISHED and not (is_owner or is_admin):
        from django.http import Http404

        raise Http404()

    is_favorite = False
    if viewer.is_authenticated:
        is_favorite = Favorite.objects.filter(
            user=viewer, listing=listing
        ).exists()

    context = {
        "listing": listing,
        "is_owner": is_owner,
        "is_admin_view": is_admin and not is_owner,
        "can_see_date": is_owner or is_admin,
        "is_favorite": is_favorite,
        "photos": listing.photos.all(),
    }
    return render(request, "listings/detail.html", context)


# --- Редактирование / удаление ----------------------------------------------


def _can_edit(user, listing):
    return user.is_authenticated and (user.pk == listing.author_id or user.is_staff)


@login_required
def listing_edit(request, pk):
    listing = get_object_or_404(Listing, pk=pk)
    if not _can_edit(request.user, listing):
        from django.http import Http404

        raise Http404()

    photo_error = None
    saved = False
    if request.method == "POST":
        form = ListingForm(request.POST, instance=listing, require_category=False)
        remove_ids = request.POST.getlist("remove_photos")
        new_files = request.FILES.getlist("photos")

        remaining = listing.photos.exclude(pk__in=remove_ids).count()
        total_after = remaining + len(new_files)
        if total_after < settings.LISTING_MIN_PHOTOS:
            photo_error = "Добавьте хотя бы 1 Фото"
        elif total_after > settings.LISTING_MAX_PHOTOS:
            photo_error = "Можно добавить не более 15 фото."
        else:
            for f in new_files:
                if f.size < settings.PHOTO_MIN_SIZE:
                    photo_error = "Размер фото должен быть не менее 30 Кбайт."
                    break
                if f.size > settings.PHOTO_MAX_SIZE:
                    photo_error = "Размер фото должен быть не более 3 Мб."
                    break

        if form.is_valid() and photo_error is None:
            form.save()
            if remove_ids:
                listing.photos.filter(pk__in=remove_ids).delete()
            start = listing.photos.count()
            for i, f in enumerate(new_files):
                ListingPhoto.objects.create(
                    listing=listing, image=f, position=start + i
                )
            saved = True
            form = ListingForm(instance=listing, require_category=False)
    else:
        form = ListingForm(instance=listing, require_category=False)

    return render(
        request,
        "listings/edit.html",
        {
            "form": form,
            "listing": listing,
            "photos": listing.photos.all(),
            "photo_error": photo_error,
            "saved": saved,
        },
    )


@login_required
@require_POST
def listing_delete(request, pk):
    listing = get_object_or_404(Listing, pk=pk)
    if not _can_edit(request.user, listing):
        from django.http import Http404

        raise Http404()
    listing.status = Listing.Status.DELETED
    listing.deleted_at = timezone.now()
    listing.save(update_fields=["status", "deleted_at"])
    return redirect("accounts:my_account")


# --- Избранное / жалобы -----------------------------------------------------


@login_required
@require_POST
def toggle_favorite(request, pk):
    listing = get_object_or_404(Listing, pk=pk)
    fav = Favorite.objects.filter(user=request.user, listing=listing).first()
    if fav:
        fav.delete()
        added = False
        message = f"Объявление ({listing.title}) убрано из избранного."
    else:
        Favorite.objects.create(user=request.user, listing=listing)
        added = True
        message = f"Объявление ({listing.title}) добавлено в Избранное."

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"added": added, "message": message})
    return redirect(listing.get_absolute_url())


@login_required
@require_POST
def complaint_create(request, pk):
    listing = get_object_or_404(Listing, pk=pk)
    text = (request.POST.get("text") or "").strip()
    if not text:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"ok": False, "message": "Введите текст"}, status=400)
        return redirect(listing.get_absolute_url())

    Complaint.objects.create(listing=listing, reporter=request.user, text=text)
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"ok": True, "message": "Жалоба отправлена."})
    return redirect(listing.get_absolute_url())
