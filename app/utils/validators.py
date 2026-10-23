import re

MAX_ATTACHMENTS = 10


def validate_password_strength(value: str) -> str:
    if len(value) < 8:
        raise ValueError("Password must be at least 8 characters long")
    if len(value) > 64:
        raise ValueError("Password must be at most 64 characters long")
    if not re.search(r"[A-Za-z]", value) or not re.search(r"\d", value):
        raise ValueError("Password must contain at least one letter and one digit")
    return value


def validate_attachment_urls(urls: list[str]) -> list[str]:
    if len(urls) > MAX_ATTACHMENTS:
        raise ValueError(f"At most {MAX_ATTACHMENTS} attachment URLs are allowed")
    cleaned = []
    for url in urls:
        url = url.strip()
        if not re.match(r"^https?://[^\s]+$", url) or len(url) > 500:
            raise ValueError(f"Invalid attachment URL: {url[:60]}")
        cleaned.append(url)
    return cleaned
