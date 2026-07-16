from hashing.bcrypt_password_hasher import BcryptPasswordHasher

_PASSWORD = "Passw0rd1!"
# 128 code points / 252 UTF-8 bytes -- the exact upper bound scenario 2.4d pins as
# valid. bcrypt truncates at 72 bytes, so this is the case that proves the SHA-256
# pre-hash is doing its job rather than the hasher silently truncating.
_MAX_LENGTH_PASSWORD = "Пароль1!" + "я" * 120


class TestBcryptPasswordHasher:
    def test_hash_is_not_the_plaintext(self):
        hasher = BcryptPasswordHasher()

        hashed = hasher.hash(_PASSWORD)

        assert hashed != _PASSWORD
        assert _PASSWORD not in hashed

    def test_hash_is_a_bcrypt_hash(self):
        hasher = BcryptPasswordHasher()

        hashed = hasher.hash(_PASSWORD)

        assert hashed.startswith("$2b$"), f"expected a bcrypt hash, got {hashed!r}"

    def test_verify_accepts_the_correct_password(self):
        hasher = BcryptPasswordHasher()

        assert hasher.verify(_PASSWORD, hasher.hash(_PASSWORD)) is True

    def test_verify_rejects_a_wrong_password(self):
        hasher = BcryptPasswordHasher()

        assert hasher.verify("Wr0ngPass!", hasher.hash(_PASSWORD)) is False

    def test_same_password_hashes_differently_each_time(self):
        hasher = BcryptPasswordHasher()

        assert hasher.hash(_PASSWORD) != hasher.hash(_PASSWORD), "salt is not being applied"

    def test_max_length_password_round_trips_without_truncation(self):
        hasher = BcryptPasswordHasher()

        assert hasher.verify(_MAX_LENGTH_PASSWORD, hasher.hash(_MAX_LENGTH_PASSWORD)) is True

    def test_two_long_passwords_differing_past_byte_72_are_not_interchangeable(self):
        # Without the SHA-256 pre-hash both inputs truncate to the same 72 bytes
        # and bcrypt would accept either for the other -- a real login hole.
        hasher = BcryptPasswordHasher()
        shared_prefix = "A1!" + "b" * 100

        hashed = hasher.hash(shared_prefix + "one")

        assert hasher.verify(shared_prefix + "two", hashed) is False
