from dataclasses import dataclass
from typing import ClassVar

from clients.application.dto.auth.register_request_dto import RegisterRequestDto


@dataclass(frozen=True)
class RegisterScope:
    email: str
    password: str
    confirm_password: str

    DEFAULTS: ClassVar[dict] = {
        "email": "user@example.com",
        "password": "Str0ng!Pass",
        "confirm_password": "Str0ng!Pass",
    }

    @classmethod
    def builder(cls, **overrides) -> "RegisterScope":
        return cls(**{**cls.DEFAULTS, **overrides})

    def to_request_dto(self) -> RegisterRequestDto:
        return RegisterRequestDto(
            email=self.email,
            password=self.password,
            confirm_password=self.confirm_password,
        )
