from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class VerifyRequestDto:
    email: str
    code: str

    def to_json(self) -> dict:
        return asdict(self)
