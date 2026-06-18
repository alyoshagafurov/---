"""Сквозной смоук-тест основных сценариев (запуск: python smoke_test.py)."""
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

# Для теста используем in-memory backend, чтобы проверять mail.outbox.
from django.conf import settings as dj_settings
dj_settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

from io import BytesIO
from django.test import Client
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core import mail
from PIL import Image
from accounts.models import User
from listings.models import Listing, Category, Favorite, Complaint
from messaging.models import Conversation, Message

results = []
def ok(name, cond):
    results.append((name, bool(cond)))
    print(("✓" if cond else "✗"), name)

def make_photo(size_kb=60):
    img = Image.new("RGB", (700, 700), "#1763cf")
    buf = BytesIO(); img.save(buf, format="JPEG", quality=95)
    data = buf.getvalue()
    # дотягиваем до нужного размера
    if len(data) < size_kb * 1024:
        data = data + b"\x00" * (size_kb * 1024 - len(data))
    return SimpleUploadedFile("p.jpg", data, content_type="image/jpeg")

# Чистим тестового пользователя от прошлых прогонов
User.objects.filter(email="tester@example.com").delete()
User.objects.filter(email="moved@example.com").delete()

c = Client()

# 1. Регистрация с неверными данными -> ошибки
r = c.post("/accounts/register/", {"display_name": "плохое имя!", "email": "рус@mail.ru",
            "password1": "123", "password2": "456"})
ok("Регистрация: невалидные данные не проходят", "Регистрация" in r.content.decode() and not User.objects.filter(email="рус@mail.ru").exists())

# 2. Корректная регистрация
mail.outbox = []
r = c.post("/accounts/register/", {"display_name": "Tester1", "email": "tester@example.com",
            "password1": "secret12", "password2": "secret12", "terms": "on"})
u = User.objects.filter(email="tester@example.com").first()
ok("Регистрация проходит", u is not None)
ok("Письмо о регистрации отправлено", any("зарегистрирован" in m.subject for m in mail.outbox))
ok("После регистрации редирект в аккаунт", r.status_code == 302 and "/accounts/me" in r.url)

# 3. Дубль почты
r = c2 = Client().post("/accounts/register/", {"display_name": "Dup", "email": "tester@example.com",
            "password1": "secret12", "password2": "secret12", "terms": "on"})
ok("Дубликат почты отклонён", "уже Зарегистрирована" in r.content.decode())

# 4. Добавление публикации (модерация -> очередь)
cat = Category.objects.first()
r = c.post("/listings/add/", {"category": cat.id, "title": "Тестовая публикация",
            "description": "Описание теста", "terms": "on", "photos": [make_photo(), make_photo()]})
listing = Listing.objects.filter(title="Тестовая публикация").first()
ok("Публикация создана", listing is not None)
ok("Публикация в очереди", listing and listing.status == Listing.Status.QUEUE)
ok("Фото сохранены (2 шт.)", listing and listing.photos.count() == 2)
ok("Показано сообщение о модерации", "после проверки Администрацией" in r.content.decode())

# 5. Публикация без фото -> ошибка
r = c.post("/listings/add/", {"category": cat.id, "title": "Без фото",
            "description": "x", "terms": "on"})
ok("Без фото — ошибка", "хотя бы 1 Фото" in r.content.decode())

# 6. Модерация: админ публикует
admin = Client(); admin.force_login(User.objects.get(email="admin@example.com"))
r = admin.post(f"/panel/ads/{listing.id}/approve/")
listing.refresh_from_db()
ok("Админ публикует объявление", listing.status == Listing.Status.PUBLISHED)

# 7. Избранное (AJAX)
other_listing = Listing.objects.filter(status=Listing.Status.PUBLISHED).exclude(author=u).first()
r = c.post(f"/listings/{other_listing.id}/favorite/", HTTP_X_REQUESTED_WITH="XMLHttpRequest")
ok("Добавлено в избранное", Favorite.objects.filter(user=u, listing=other_listing).exists())
ok("JSON ответ избранного", "добавлено" in r.json().get("message", ""))
r = c.post(f"/listings/{other_listing.id}/favorite/", HTTP_X_REQUESTED_WITH="XMLHttpRequest")
ok("Убрано из избранного", not Favorite.objects.filter(user=u, listing=other_listing).exists())

# 8. Жалоба
r = c.post(f"/listings/{other_listing.id}/complaint/", {"text": "Не соответствует категории"},
           HTTP_X_REQUESTED_WITH="XMLHttpRequest")
ok("Жалоба создана", Complaint.objects.filter(listing=other_listing, reporter=u).exists())
r = c.post(f"/listings/{other_listing.id}/complaint/", {"text": ""},
           HTTP_X_REQUESTED_WITH="XMLHttpRequest")
ok("Пустая жалоба отклонена", r.status_code == 400)

# 9. Сообщения
other_user = other_listing.author
r = c.get(f"/messages/with/{other_user.id}/")
conv = Conversation.get_or_create_between(u, other_user)
r = c.post(f"/messages/{conv.id}/", {"text": "Здравствуйте!"})
ok("Сообщение отправлено", Message.objects.filter(conversation=conv, sender=u).exists())

# 10. Настройки: смена имени
r = c.post("/accounts/settings/name/", {"display_name": "Tester2"})
u.refresh_from_db()
ok("Имя изменено", u.display_name == "Tester2")

# 11. Настройки: смена почты (+письмо)
mail.outbox = []
r = c.post("/accounts/settings/email/", {"new_email": "moved@example.com",
            "current_password": "secret12", "confirm_password": "secret12"})
u.refresh_from_db()
ok("Почта изменена", u.email == "moved@example.com")
ok("Письмо о смене почты", any("Почта изменена" == m.subject for m in mail.outbox))

# 12. Настройки: смена пароля (+письмо)
mail.outbox = []
r = c.post("/accounts/settings/password/", {"current_password": "secret12",
            "password1": "newpass1", "password2": "newpass1"})
u.refresh_from_db()
ok("Пароль изменён", u.check_password("newpass1"))
ok("Письмо о смене пароля", any("Пароль изменен" == m.subject for m in mail.outbox))

# 13. Восстановление пароля
mail.outbox = []
r = Client().post("/accounts/forgot-password/", {"email": "moved@example.com"})
ok("Письмо восстановления отправлено", any("Изменение пароля" == m.subject for m in mail.outbox))
ok("Показано подтверждение отправки", "было отправлено Письмо" in r.content.decode())

# 14. Удаление публикации -> в удалённые
r = c.post(f"/listings/{listing.id}/delete/")
listing.refresh_from_db()
ok("Публикация удалена (статус deleted)", listing.status == Listing.Status.DELETED)

# 15. Панель: доступ только для staff
ok("Гость не входит в панель", Client().get("/panel/").status_code == 302)
ok("Обычный пользователь не входит в панель", c.get("/panel/").status_code == 302)
ok("Админ входит в панель", admin.get("/panel/").status_code == 200)

print("\n=== ИТОГ ===")
passed = sum(1 for _, v in results if v)
print(f"{passed}/{len(results)} проверок пройдено")
fails = [n for n, v in results if not v]
if fails:
    print("ПРОВАЛЫ:")
    for n in fails:
        print("  -", n)
