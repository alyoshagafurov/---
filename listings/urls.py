from django.urls import path

from . import views

app_name = "listings"

urlpatterns = [
    path("add/", views.listing_create, name="create"),
    path("category/<slug:slug>/", views.category_detail, name="category"),
    path("<int:pk>/", views.listing_detail, name="detail"),
    path("<int:pk>/edit/", views.listing_edit, name="edit"),
    path("<int:pk>/delete/", views.listing_delete, name="delete"),
    path("<int:pk>/favorite/", views.toggle_favorite, name="toggle_favorite"),
    path("<int:pk>/complaint/", views.complaint_create, name="complaint"),
]
