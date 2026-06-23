from django.shortcuts import render

from listings.models import Category, Listing

from .models import SiteSettings


def home(request):
    """Главная страница: категории слева, случайные публикации справа."""
    categories = (
        Category.objects.all()
        .prefetch_related("listings")
        .order_by("position", "name")
    )
    random_listings = (
        Listing.objects.filter(status=Listing.Status.PUBLISHED)
        .select_related("category")
        .prefetch_related("photos")
        .order_by("?")[:12]
    )
    return render(
        request,
        "core/home.html",
        {"categories": categories, "listings": random_listings},
    )


def rules(request):
    settings_obj = SiteSettings.get()
    return render(request, "core/rules.html", {"settings": settings_obj})


def contacts(request):
    settings_obj = SiteSettings.get()
    return render(request, "core/contacts.html", {"settings": settings_obj})
