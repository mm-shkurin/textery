from statements.verify_account_atomic_transition_statements import (
    VerifyAccountAtomicTransitionStatements,
)


class TestVerifyAccountAtomicTransition:
    """Scenario 3.6: verify wires the atomic single-row transitions.

    Given a pending account with an active, unexpired verification code
    When the client submits the correct code
    Then _apply_verification persists the transition via the atomic
         transition_to_verified / transition_to_consumed port methods
         (not the lock-free verify()+save() / consume()+save() pair)
    """

    async def test_should_drive_atomic_transitions_on_happy_path(
        self,
        verify_account_atomic_transition_statements: VerifyAccountAtomicTransitionStatements,
    ):
        statements = verify_account_atomic_transition_statements
        await statements.given_pending_account_with_verification_code()
        await statements.verify_with_the_issued_code()
        statements.assert_verify_drove_the_atomic_transitions()
