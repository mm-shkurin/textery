from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class LoginRequestDto:
    email: str
    password: str

    def to_json(self) -> dict:
        return asdict(self)
