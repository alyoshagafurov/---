from django.shortcuts import render

from listings.models import Category, Listing

from .models import SiteSettings


def home(request):
    """Главная страница: категории с публикациями."""
    categories = (
        Category.objects.all()
        .prefetch_related("listings")
        .order_by("position", "name")
    )
    latest = (
        Listing.objects.filter(status=Listing.Status.PUBLISHED)
        .select_related("category")
        .prefetch_related("photos")[:10]
    )
    return render(
        request,
        "core/home.html",
        {"categories": categories, "latest": latest},
    )


def rules(request):
    settings_obj = SiteSettings.get()
    return render(request, "core/rules.html", {"settings": settings_obj})


def contacts(request):
    settings_obj = SiteSettings.get()
    return render(request, "core/contacts.html", {"settings": settings_obj})
