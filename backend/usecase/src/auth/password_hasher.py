from typing import Protocol


class PasswordHasher(Protocol):
    """Port for one-way password hashing.

    Deliberately has no null-object fallback: `RegisterUser` takes it as a
    required constructor argument. A default that quietly returned the plaintext
    would persist real credentials in the clear and no test would notice -- the
    same shape of bug as the null repository that silently discarded accounts
    (see scenario 1.5's review findings).
    """

    def hash(self, plain_password: str) -> str:
        """Return a one-way hash of `plain_password`.

        The caller passes the NFC-normalized value (`Password.value`), never the
        raw request string, so the same password typed in decomposed and
        precomposed form hashes identically.
        """
        ...

    def verify(self, plain_password: str, hashed_password: str) -> bool:
        """Return True when `plain_password` matches `hashed_password`."""
        ...
