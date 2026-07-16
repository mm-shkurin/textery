from pydantic import BaseModel


class VerifyRequestDto(BaseModel):
    email: str
    # No Field(pattern=...) on `code`, deliberately: the 6-digit rule lives in the
    # domain's VerificationCodeValue and surfaces as a 400 {error_code, message},
    # mirroring RegisterRequestDto, which carries no constraints either and lets
    # the Email/Password value objects reject a bad request. A Pydantic pattern
    # here answers 422 with Pydantic's own envelope -- a second error taxonomy on
    # the same auth surface, and one auth_verify.yaml does not document.
    # See decisions/verify-code-shape-validation-decision.md.
    code: str
