def get_client_ip(request):
    """IP-адрес клиента с учётом обратного прокси."""
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def mask_email(email):
    """Скрывает середину локальной части почты: Anna***penko@gmail.com."""
    if not email or "@" not in email:
        return email
    local, domain = email.split("@", 1)
    if len(local) <= 4:
        masked = local[:1] + "***"
    else:
        masked = local[:4] + "***" + local[-4:]
    return f"{masked}@{domain}"
