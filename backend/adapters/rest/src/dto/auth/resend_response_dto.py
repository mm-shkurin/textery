from pydantic import BaseModel

from auth.verification_code import VerificationCode


class ResendResponseDto(BaseModel):
    verification_code: str
    code_expires_at: str

    @classmethod
    def from_domain(cls, code: VerificationCode) -> "ResendResponseDto":
        return cls(
            verification_code=code.code,
            code_expires_at=code.expires_at.isoformat(),
        )
