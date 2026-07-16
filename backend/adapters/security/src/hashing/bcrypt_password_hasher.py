import base64
import hashlib

import bcrypt


class BcryptPasswordHasher:
    """bcrypt implementation of the `PasswordHasher` port.

    Lives in an adapter rather than the domain because `bcrypt` is a third-party
    dependency and the domain has none. The `SystemClock` precedent (implemented
    inline in the usecase) does not apply -- that one is stdlib-only.

    Input is SHA-256 pre-hashed and base64-encoded before bcrypt, the same
    construction as passlib's `bcrypt_sha256`. This is not decoration:

    - bcrypt silently truncates at 72 bytes, but `Password` allows 128 code
      points, which scenario 2.4d pins as up to 252 UTF-8 bytes and requires to
      be accepted with a 201. Truncating would make two different long passwords
      interchangeable at login; rejecting would 500 a request the spec says is
      valid. Pre-hashing makes every input exactly 44 bytes, so neither happens.
    - base64 is what keeps a NUL byte out of the digest: bcrypt treats NUL as a
      terminator, so a raw digest containing one would silently shorten the
      effective password.
    """

    _ROUNDS = 12

    def hash(self, plain_password: str) -> str:
        return bcrypt.hashpw(self._prepare(plain_password), bcrypt.gensalt(rounds=self._ROUNDS)).decode("utf-8")

    def verify(self, plain_password: str, hashed_password: str) -> bool:
        return bcrypt.checkpw(self._prepare(plain_password), hashed_password.encode("utf-8"))

    def _prepare(self, plain_password: str) -> bytes:
        digest = hashlib.sha256(plain_password.encode("utf-8")).digest()
        return base64.b64encode(digest)
