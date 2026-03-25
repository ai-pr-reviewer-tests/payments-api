"""Currency utilities."""

CURRENCY_CONFIG = {
    "usd": {"symbol": "$", "decimal_places": 2, "name": "US Dollar"},
    "eur": {"symbol": "\u20ac", "decimal_places": 2, "name": "Euro"},
    "gbp": {"symbol": "\u00a3", "decimal_places": 2, "name": "British Pound"},
    "cad": {"symbol": "C$", "decimal_places": 2, "name": "Canadian Dollar"},
    "aud": {"symbol": "A$", "decimal_places": 2, "name": "Australian Dollar"},
    "jpy": {"symbol": "\u00a5", "decimal_places": 0, "name": "Japanese Yen"},
}


def format_amount(amount_cents: int, currency: str) -> str:
    """Format an amount in cents to a human-readable string."""
    config = CURRENCY_CONFIG.get(currency)
    if config is None:
        return f"{amount_cents} {currency}"
    
    if config["decimal_places"] == 0:
        return f"{config['symbol']}{amount_cents}"
    
    amount = amount_cents / (10 ** config["decimal_places"])
    return f"{config['symbol']}{amount:.{config['decimal_places']}f}"


def cents_to_decimal(amount_cents: int, currency: str) -> float:
    """Convert cents to decimal amount."""
    config = CURRENCY_CONFIG.get(currency, {"decimal_places": 2})
    return amount_cents / (10 ** config["decimal_places"])


def decimal_to_cents(amount: float, currency: str) -> int:
    """Convert decimal amount to cents."""
    config = CURRENCY_CONFIG.get(currency, {"decimal_places": 2})
    return int(round(amount * (10 ** config["decimal_places"])))


def is_supported_currency(currency: str) -> bool:
    """Check if a currency code is supported."""
    return currency in CURRENCY_CONFIG
