from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class RegisterRequestDto:
    email: str
    password: str
    confirm_password: str

    def to_json(self) -> dict:
        return asdict(self)
