from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class RegisterRequestDto:
    email: str
    password: str
    confirm_password: str
    extra_fields: dict = field(default_factory=dict)

    def to_json(self) -> dict:
        body = asdict(self)
        body.pop("extra_fields")
        body.update(self.extra_fields)
        return body
