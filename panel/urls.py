from django.urls import path

from . import views

app_name = "panel"

urlpatterns = [
    path("", views.index, name="index"),
    path("users/", views.users, name="users"),
    path("ads/", views.ads_all, name="ads_all"),
    path("ads/queue/", views.ads_queue, name="ads_queue"),
    path("ads/deleted/", views.ads_deleted, name="ads_deleted"),
    path("ads/<int:pk>/approve/", views.listing_approve, name="listing_approve"),
    path("ads/<int:pk>/reject/", views.listing_reject, name="listing_reject"),
    path("complaints/", views.complaints, name="complaints"),
    path("categories/", views.categories, name="categories"),
    path("categories/<int:pk>/edit/", views.category_edit, name="category_edit"),
    path("rules/", views.rules_edit, name="rules_edit"),
]
