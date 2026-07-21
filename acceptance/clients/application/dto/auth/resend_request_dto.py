from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ResendRequestDto:
    email: str

    def to_json(self) -> dict:
        return asdict(self)
