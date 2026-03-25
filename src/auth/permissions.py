"""Role-based access control."""

from enum import Enum
from functools import wraps

from flask import g, jsonify


class Role(str, Enum):
    USER = "user"
    SUPPORT = "support"
    ADMIN = "admin"

    @classmethod
    def hierarchy(cls) -> dict:
        return {cls.USER: 0, cls.SUPPORT: 1, cls.ADMIN: 2}

    def level(self) -> int:
        return self.hierarchy()[self]


def require_role(minimum_role: Role):
    """Decorator that checks the authenticated user meets the minimum role level."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            user_role = Role(g.current_user_role)
            if user_role.level() < minimum_role.level():
                return jsonify({"error": "Insufficient permissions"}), 403
            return f(*args, **kwargs)
        return decorated
    return decorator
