from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import user_passes_test
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.models import SiteSettings
from listings.models import Category, Complaint, Listing

from .forms import CategoryForm, RulesForm

User = get_user_model()

USERS_PER_PAGE = 200
ADS_PER_PAGE = 200
COMPLAINTS_PER_PAGE = 200


def staff_required(view):
    return user_passes_test(
        lambda u: u.is_authenticated and u.is_staff,
        login_url="accounts:login",
    )(view)


def _paginate(request, qs, per_page):
    return Paginator(qs, per_page).get_page(request.GET.get("page"))


@staff_required
def index(request):
    counts = {
        "users": User.objects.count(),
        "published": Listing.objects.filter(
            status=Listing.Status.PUBLISHED
        ).count(),
        "queue": Listing.objects.filter(status=Listing.Status.QUEUE).count(),
        "deleted": Listing.objects.filter(status=Listing.Status.DELETED).count(),
        "complaints": Complaint.objects.count(),
        "categories": Category.objects.count(),
    }
    return render(request, "panel/index.html", {"counts": counts, "active": "index"})


@staff_required
def users(request):
    qs = User.objects.all().order_by("date_joined")
    page = _paginate(request, qs, USERS_PER_PAGE)
    return render(request, "panel/users.html", {"page_obj": page, "active": "users"})


def _ads_page(request, status):
    qs = (
        Listing.objects.filter(status=status)
        .select_related("author", "category")
        .prefetch_related("photos")
        .order_by("-created_at")
    )
    return _paginate(request, qs, ADS_PER_PAGE)


@staff_required
def ads_all(request):
    page = _ads_page(request, Listing.Status.PUBLISHED)
    return render(
        request,
        "panel/ads.html",
        {"page_obj": page, "section": "all", "title": "Все объявления", "active": "all"},
    )


@staff_required
def ads_queue(request):
    page = _ads_page(request, Listing.Status.QUEUE)
    return render(
        request,
        "panel/ads.html",
        {"page_obj": page, "section": "queue", "title": "В очереди", "active": "queue"},
    )


@staff_required
def ads_deleted(request):
    page = _ads_page(request, Listing.Status.DELETED)
    return render(
        request,
        "panel/ads.html",
        {"page_obj": page, "section": "deleted", "title": "Удалённые", "active": "deleted"},
    )


@staff_required
@require_POST
def listing_approve(request, pk):
    listing = get_object_or_404(Listing, pk=pk)
    listing.status = Listing.Status.PUBLISHED
    if listing.published_at is None:
        listing.published_at = timezone.now()
    listing.save(update_fields=["status", "published_at"])
    return redirect(request.POST.get("next") or "panel:ads_queue")


@staff_required
@require_POST
def listing_reject(request, pk):
    listing = get_object_or_404(Listing, pk=pk)
    listing.status = Listing.Status.DELETED
    listing.deleted_at = timezone.now()
    listing.save(update_fields=["status", "deleted_at"])
    return redirect(request.POST.get("next") or "panel:ads_queue")


@staff_required
def complaints(request):
    qs = (
        Complaint.objects.select_related("listing", "reporter")
        .prefetch_related("listing__photos")
        .order_by("-created_at")
    )
    page = _paginate(request, qs, COMPLAINTS_PER_PAGE)
    return render(request, "panel/complaints.html", {"page_obj": page, "active": "complaints"})


@staff_required
def categories(request):
    if request.method == "POST":
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("panel:categories")
    else:
        form = CategoryForm()
    return render(
        request,
        "panel/categories.html",
        {"form": form, "categories": Category.objects.all(), "active": "categories"},
    )


@staff_required
def category_edit(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == "POST":
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            return redirect("panel:categories")
    else:
        form = CategoryForm(instance=category)
    return render(
        request,
        "panel/category_edit.html",
        {"form": form, "category": category, "active": "categories"},
    )


@staff_required
def rules_edit(request):
    obj = SiteSettings.get()
    saved = False
    if request.method == "POST":
        form = RulesForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            saved = True
    else:
        form = RulesForm(instance=obj)
    return render(
        request, "panel/rules_edit.html", {"form": form, "saved": saved, "active": "rules"}
    )
