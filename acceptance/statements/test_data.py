from uuid import uuid4


class TestData:
    @staticmethod
    def unique_idempotency_key() -> str:
        return f"acceptance-test-{uuid4()}"
