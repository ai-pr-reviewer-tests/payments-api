"""Input sanitization utilities."""
import re
import html


def sanitize_string(value: str, max_length: int = 255) -> str:
    """Sanitize a string input."""
    value = value.strip()
    value = html.escape(value)
    return value[:max_length]


def sanitize_email(email: str) -> str:
    """Sanitize and validate an email address."""
    email = email.strip().lower()
    if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
        raise ValueError(f"Invalid email address: {email}")
    return email


def is_safe_identifier(value: str) -> bool:
    """Check if a value is safe to use as an identifier."""
    return bool(re.match(r"^[a-zA-Z0-9_-]+$", value))
