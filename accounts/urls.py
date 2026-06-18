from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("register/", views.register, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("forgot-password/", views.password_reset_request, name="password_reset"),
    path(
        "reset/<uidb64>/<token>/",
        views.password_reset_confirm,
        name="password_reset_confirm",
    ),
    # Профиль
    path("me/", views.my_account, name="my_account"),
    path("user/<int:pk>/", views.user_profile, name="user_profile"),
    # Настройки
    path("settings/", views.settings_index, name="settings"),
    path("settings/avatar/", views.settings_avatar, name="settings_avatar"),
    path("settings/name/", views.settings_name, name="settings_name"),
    path("settings/password/", views.settings_password, name="settings_password"),
    path("settings/email/", views.settings_email, name="settings_email"),
    # Избранное
    path("favorites/", views.favorites, name="favorites"),
]
