from pydantic import BaseModel


class LoginRequestDto(BaseModel):
    # No Field constraints, matching RegisterRequestDto/VerifyRequestDto: shape and
    # policy live in the domain and surface as a 400/401 {error_code, message},
    # never Pydantic's 422 envelope.
    email: str
    password: str
