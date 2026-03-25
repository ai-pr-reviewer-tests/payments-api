"""Request validation helpers."""

from marshmallow import Schema, fields, validate, ValidationError


class LoginSchema(Schema):
    email = fields.Email(required=True)
    password = fields.Str(required=True, validate=validate.Length(min=1))


class ChargeSchema(Schema):
    amount_cents = fields.Int(required=True, validate=validate.Range(min=1))
    currency = fields.Str(required=True, validate=validate.OneOf(["usd", "eur", "gbp"]))
    source_token = fields.Str(required=True, validate=validate.Length(min=1))
    description = fields.Str(load_default="")


class RefundSchema(Schema):
    amount_cents = fields.Int(validate=validate.Range(min=1), load_default=None)


def validate_request_data(schema_cls, data: dict) -> dict:
    """Validate request data against a marshmallow schema.

    Args:
        schema_cls: The marshmallow Schema class to validate against.
        data: The raw request data dictionary.

    Returns:
        The validated and deserialized data.

    Raises:
        ValidationError: If validation fails.
    """
    schema = schema_cls()
    return schema.load(data)
