class FakePasswordHasher:
    """In-memory `PasswordHasher` double.

    Real bcrypt costs ~100ms per call by design, which would dominate the whole
    usecase suite. The transform is deliberately visible and reversible so tests
    can assert *which* value was hashed -- `BcryptPasswordHasher`'s own tests
    cover the real algorithm.
    """

    PREFIX = "hashed::"

    def __init__(self) -> None:
        self.hashed_values: list[str] = []
        # Scenario 5.4: spy so a test can prove the lockout gate short-circuits
        # BEFORE password verification -- a locked account must never reach verify().
        self.verify_call_count = 0

    def hash(self, plain_password: str) -> str:
        self.hashed_values.append(plain_password)
        return f"{self.PREFIX}{plain_password}"

    def verify(self, plain_password: str, hashed_password: str) -> bool:
        self.verify_call_count += 1
        return hashed_password == f"{self.PREFIX}{plain_password}"
