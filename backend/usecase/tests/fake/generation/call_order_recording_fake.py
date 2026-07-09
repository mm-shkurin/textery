class CallOrderRecordingFake:
    """Shared base for generation Fakes that must prove call ordering.

    Both FakeGenerationStorage and FakeGenerationQueue record every call into
    a single shared list so a Statements assertion can verify not just that
    each collaborator was called, but the exact order across collaborators.
    """

    def __init__(self, call_order: list) -> None:
        self._call_order = call_order

    def _record(self, tag: str, value: object) -> None:
        self._call_order.append((tag, value))
