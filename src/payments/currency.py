"""Automatic currency conversion for international payments."""

import logging
from decimal import Decimal, ROUND_HALF_UP

from src.db.connection import get_db_connection

logger = logging.getLogger(__name__)

SUPPORTED_CURRENCIES = ("usd", "eur", "gbp", "cad", "aud", "jpy", "chf", "sek", "nok", "dkk")
BASE_CURRENCY = "usd"
DECIMAL_PLACES = {"jpy": 0}
DEFAULT_DECIMAL_PLACES = 2


def _load_exchange_rates() -> dict[str, Decimal]:
    """Load current exchange rates from the database.

    Returns a dict mapping currency pair keys (e.g. 'usd_eur') to their
    exchange rate as a Decimal.
    """
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT from_currency, to_currency, rate FROM exchange_rates WHERE active = true"
        )
        rows = cur.fetchall()

    rates = {}
    for row in rows:
        key = f"{row['from_currency']}_{row['to_currency']}"
        rates[key] = Decimal(str(row["rate"]))

    logger.info("Loaded %d exchange rates from database", len(rates))
    return rates


_rates = _load_exchange_rates()


def get_exchange_rate(from_currency: str, to_currency: str) -> Decimal:
    """Get the exchange rate between two currencies.

    Args:
        from_currency: Source currency code (e.g. 'usd').
        to_currency: Target currency code (e.g. 'eur').

    Returns:
        Exchange rate as a Decimal.

    Raises:
        ValueError: If the currency pair is not supported.
    """
    from_currency = from_currency.lower()
    to_currency = to_currency.lower()

    if from_currency == to_currency:
        return Decimal("1")

    if from_currency not in SUPPORTED_CURRENCIES:
        raise ValueError(f"Unsupported source currency: {from_currency}")
    if to_currency not in SUPPORTED_CURRENCIES:
        raise ValueError(f"Unsupported target currency: {to_currency}")

    direct_key = f"{from_currency}_{to_currency}"
    if direct_key in _rates:
        return _rates[direct_key]

    inverse_key = f"{to_currency}_{from_currency}"
    if inverse_key in _rates:
        return Decimal("1") / _rates[inverse_key]

    if from_currency != BASE_CURRENCY and to_currency != BASE_CURRENCY:
        from_base = _get_rate_to_base(from_currency)
        to_base = _get_rate_to_base(to_currency)
        if from_base and to_base:
            return (Decimal("1") / from_base) * to_base

    raise ValueError(
        f"No exchange rate available for {from_currency} -> {to_currency}"
    )


def _get_rate_to_base(currency: str) -> Decimal | None:
    """Get the rate from BASE_CURRENCY to the given currency."""
    key = f"{BASE_CURRENCY}_{currency}"
    if key in _rates:
        return _rates[key]

    inverse_key = f"{currency}_{BASE_CURRENCY}"
    if inverse_key in _rates:
        return Decimal("1") / _rates[inverse_key]

    return None


def convert_amount(amount_cents: int, from_currency: str,
                   to_currency: str) -> dict:
    """Convert a payment amount from one currency to another.

    Args:
        amount_cents: Amount in the smallest unit of the source currency.
        from_currency: Source currency code.
        to_currency: Target currency code.

    Returns:
        dict with original amount, converted amount, rate, and metadata.

    Raises:
        ValueError: If the conversion is not possible.
    """
    from_currency = from_currency.lower()
    to_currency = to_currency.lower()

    if amount_cents < 0:
        raise ValueError("Amount must be non-negative")

    if from_currency == to_currency:
        return {
            "original_amount_cents": amount_cents,
            "converted_amount_cents": amount_cents,
            "from_currency": from_currency,
            "to_currency": to_currency,
            "exchange_rate": "1",
            "conversion_applied": False,
        }

    rate = get_exchange_rate(from_currency, to_currency)

    from_decimals = DECIMAL_PLACES.get(from_currency, DEFAULT_DECIMAL_PLACES)
    to_decimals = DECIMAL_PLACES.get(to_currency, DEFAULT_DECIMAL_PLACES)

    if from_decimals == 0:
        source_amount = Decimal(amount_cents)
    else:
        source_amount = Decimal(amount_cents) / Decimal(10 ** from_decimals)

    converted = source_amount * rate

    if to_decimals == 0:
        converted_cents = int(converted.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    else:
        factor = Decimal(10 ** to_decimals)
        converted_cents = int(
            (converted * factor).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        )

    return {
        "original_amount_cents": amount_cents,
        "converted_amount_cents": converted_cents,
        "from_currency": from_currency,
        "to_currency": to_currency,
        "exchange_rate": str(rate),
        "conversion_applied": True,
    }


def process_international_payment(user_id: int, amount_cents: int,
                                  source_currency: str, target_currency: str,
                                  source_token: str,
                                  description: str = "") -> dict:
    """Process a payment with automatic currency conversion.

    Converts the amount to the target currency and processes the charge,
    recording both the original and converted amounts.

    Args:
        user_id: ID of the paying user.
        amount_cents: Amount in the source currency's smallest unit.
        source_currency: Currency of the amount provided.
        target_currency: Currency to charge in.
        source_token: Payment source token.
        description: Optional payment description.

    Returns:
        dict with payment details including conversion metadata.
    """
    from src.payments.processor import process_charge
    from src.db.queries import update_payment_status

    conversion = convert_amount(amount_cents, source_currency, target_currency)

    result = process_charge(
        user_id=user_id,
        amount_cents=conversion["converted_amount_cents"],
        currency=target_currency,
        source_token=source_token,
        description=description,
    )

    if conversion["conversion_applied"]:
        _store_conversion_metadata(
            payment_id=result["payment_id"],
            original_amount_cents=amount_cents,
            original_currency=source_currency,
            converted_amount_cents=conversion["converted_amount_cents"],
            target_currency=target_currency,
            exchange_rate=conversion["exchange_rate"],
        )

    return {
        **result,
        "conversion": conversion,
    }


def _store_conversion_metadata(payment_id: int, original_amount_cents: int,
                               original_currency: str,
                               converted_amount_cents: int,
                               target_currency: str,
                               exchange_rate: str) -> None:
    """Store currency conversion metadata for a payment."""
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO payment_conversions
               (payment_id, original_amount_cents, original_currency,
                converted_amount_cents, target_currency, exchange_rate,
                created_at)
               VALUES (%s, %s, %s, %s, %s, %s, NOW())""",
            (payment_id, original_amount_cents, original_currency,
             converted_amount_cents, target_currency, exchange_rate),
        )
    logger.info(
        "Conversion metadata stored for payment %d: %d %s -> %d %s (rate: %s)",
        payment_id, original_amount_cents, original_currency,
        converted_amount_cents, target_currency, exchange_rate,
    )


def get_conversion_metadata(payment_id: int) -> dict | None:
    """Retrieve currency conversion metadata for a payment."""
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute(
            """SELECT payment_id, original_amount_cents, original_currency,
                      converted_amount_cents, target_currency, exchange_rate,
                      created_at
               FROM payment_conversions WHERE payment_id = %s""",
            (payment_id,),
        )
        return cur.fetchone()
