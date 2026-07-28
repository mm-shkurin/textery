"""Shared arrange-phase assertions.

An arrange step that silently half-failed produces a confusing failure in the *act*
assertion instead of at the point of breakage. Every export scenario therefore pins
its setup calls to 200 — six hand-rolled copies of the same message before this
module existed. Holding the wording once here keeps setup failures instantly
recognisable as setup ("setup: ...") rather than as the behaviour under test.

Scenario-specific setup pins (a version the CAS must have reached, an id the response
must carry) stay with their scenario — only the universal "this arrange call
succeeded" half lives here.

Nothing here touches auth, document setup, or any scenario constant, so it is a plain
module of functions rather than a mixin.
"""


def assert_setup_ok(response, described_as: str) -> None:
    """Pin an arrange-phase HTTP call to 200. `described_as` completes the sentence
    "setup: expected {described_as} to succeed with 200"."""
    assert response.status_code == 200, (
        f"setup: expected {described_as} to succeed with 200, got "
        f"status_code={response.status_code}, body={response.body}"
    )
