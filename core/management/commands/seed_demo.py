"""Заполняет базу демо-данными: админ, пользователи, категории, публикации.

Запуск:  python manage.py seed_demo
"""

from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils import timezone
from PIL import Image, ImageDraw, ImageFont

from core.models import SiteSettings
from listings.models import Category, Listing, ListingPhoto

User = get_user_model()

CATEGORIES = ["Электроника", "Одежда", "Дом и сад", "Хобби", "Книги", "Разное"]

DEMO_LISTINGS = [
    ("Электроника", "Наушники беспроводные", "Удобные наушники, отличный звук."),
    ("Электроника", "Зарядное устройство", "Быстрая зарядка, новый адаптер."),
    ("Одежда", "Куртка демисезонная", "Тёплая куртка, размер M, как новая."),
    ("Одежда", "Кроссовки", "Лёгкие кроссовки для бега, размер 42."),
    ("Дом и сад", "Набор кастрюль", "Качественный набор посуды из 3 предметов."),
    ("Хобби", "Шахматы деревянные", "Классический набор шахмат ручной работы."),
    ("Книги", "Сборник рассказов", "Интересная книга в хорошем состоянии."),
    ("Разное", "Рюкзак городской", "Вместительный рюкзак с отделом для ноутбука."),
]


FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/Library/Fonts/Arial.ttf",
]


def _load_font(size):
    for path in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _lighten(hex_color, amount):
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
    r = int(r + (255 - r) * amount)
    g = int(g + (255 - g) * amount)
    b = int(b + (255 - b) * amount)
    return (r, g, b)


def _wrap(text, font, draw, max_width):
    words = text.split()
    lines, line = [], ""
    for w in words:
        test = (line + " " + w).strip()
        if draw.textlength(test, font=font) <= max_width:
            line = test
        else:
            if line:
                lines.append(line)
            line = w
    if line:
        lines.append(line)
    return lines


def make_image(text, color):
    """Аккуратная картинка-заглушка: диагональный градиент + крупный заголовок."""
    size = 700
    top = _lighten(color, 0.22)
    bottom = color.lstrip("#")
    bottom = tuple(int(bottom[i : i + 2], 16) for i in (0, 2, 4))
    img = Image.new("RGB", (size, size))
    draw = ImageDraw.Draw(img)
    for y in range(size):
        t = y / size
        row = (
            int(top[0] * (1 - t) + bottom[0] * t),
            int(top[1] * (1 - t) + bottom[1] * t),
            int(top[2] * (1 - t) + bottom[2] * t),
        )
        draw.line([(0, y), (size, y)], fill=row)
    font = _load_font(58)
    lines = _wrap(text, font, draw, size - 100)
    line_h = (font.getbbox("Ay")[3] - font.getbbox("Ay")[1]) + 16
    total_h = line_h * len(lines)
    y = (size - total_h) / 2
    for ln in lines:
        w = draw.textlength(ln, font=font)
        draw.text(((size - w) / 2, y), ln, fill="white", font=font)
        y += line_h
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=88)
    return ContentFile(buf.getvalue(), name="demo.jpg")


class Command(BaseCommand):
    help = "Создаёт демонстрационные данные"

    def handle(self, *args, **options):
        SiteSettings.get()

        admin, created = User.objects.get_or_create(
            email="admin@example.com",
            defaults={"display_name": "Admin", "is_staff": True, "is_superuser": True},
        )
        if created:
            admin.set_password("admin12345")
            admin.save()
            self.stdout.write("Создан админ: admin@example.com / admin12345")

        users = []
        for i in range(1, 4):
            u, c = User.objects.get_or_create(
                email=f"user{i}@example.com",
                defaults={"display_name": f"User{i}"},
            )
            if c:
                u.set_password("user12345")
                u.last_seen = timezone.now()
                u.registration_ip = f"192.168.0.{i}"
                u.last_login_ip = f"192.168.0.{i}"
                u.save()
            users.append(u)

        cats = {}
        for i, name in enumerate(CATEGORIES):
            cat, _ = Category.objects.get_or_create(name=name, defaults={"position": i})
            cats[name] = cat

        colors = ["#1763cf", "#1f9d55", "#d64545", "#9a6a00", "#6b21a8", "#0e7490"]
        for idx, (cat_name, title, desc) in enumerate(DEMO_LISTINGS):
            author = users[idx % len(users)]
            if Listing.objects.filter(title=title, author=author).exists():
                continue
            listing = Listing.objects.create(
                author=author,
                category=cats[cat_name],
                title=title,
                description=desc,
                status=Listing.Status.PUBLISHED,
                published_at=timezone.now(),
            )
            for n in range(2):
                ListingPhoto.objects.create(
                    listing=listing,
                    image=make_image(title, colors[idx % len(colors)]),
                    position=n,
                )

        # Одна публикация в очереди (для проверки модерации).
        if not Listing.objects.filter(status=Listing.Status.QUEUE).exists():
            listing = Listing.objects.create(
                author=users[0],
                category=cats["Разное"],
                title="Настольная лампа",
                description="Публикация ожидает проверки администрацией.",
                status=Listing.Status.QUEUE,
            )
            ListingPhoto.objects.create(
                listing=listing, image=make_image("Лампа", "#0e7490"), position=0
            )

        self.stdout.write(self.style.SUCCESS("Демо-данные готовы."))
