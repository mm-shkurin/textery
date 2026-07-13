from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class RegisterRequestScope:
    email: str
    password: str
    confirm_password: str

    DEFAULTS: ClassVar[dict] = {
        "email": "user@example.ru",
        "password": "Str0ng!Pass",
        "confirm_password": "Str0ng!Pass",
    }

    @classmethod
    def builder(cls, **overrides) -> "RegisterRequestScope":
        return cls(**{**cls.DEFAULTS, **overrides})
