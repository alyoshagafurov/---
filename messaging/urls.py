from django.urls import path

from . import views

app_name = "messaging"

urlpatterns = [
    path("", views.inbox, name="inbox"),
    path("contact-admin/", views.contact_admin, name="contact_admin"),
    path("with/<int:user_id>/", views.start_with, name="start_with"),
    path("<int:pk>/", views.conversation, name="conversation"),
]
