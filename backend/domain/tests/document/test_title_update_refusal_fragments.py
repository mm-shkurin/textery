"""Scenario 3.2 -- the NEGATIVE CONTROL over the refusal guard's own fragments.

`test_title_update_refusal_safety.py` asserts that no forbidden fragment appears
in the two fields the rest handler echoes verbatim. That claim is only worth
anything if each fragment is DISCRIMINATING -- if it would be absent from safe
text and present only in a leak. A fragment that occurs in ordinary safe prose
makes the guard fire on everything, which reads as six confident Security-5.1
failures against a message nobody touched.

That is not a hypothetical. Rename `TitleUpdate` -> `Title` and the two derived
fragments become `Title` and `TITLE`, both of which occur in the shipped message
("A title cannot be set and cleared at the same time.") AND in the shipped code
(`INVALID_TITLE_INTENT`). Every arm goes red at once, the accusation points at
production text that is perfectly safe, and the cheapest unblock under that
pressure is to delete the only prose arm the guard has -- trading a real guard
away to silence a defect in the list.

So this file states the precondition as a claim of its own, with its own
diagnosis, and `assert_carries_no_internal_shape` checks the same precondition
inline so that the leak arms report the fragment-list defect rather than the leak.
The two are not redundant: this file names the failure ONCE and unambiguously,
while the inline check is what stops the other file's failure text from lying.

The baselines are FROZEN test-local copies rather than the live production
constants, and `refusal_guard/fragments.py` states why at length: a live baseline
would invert the diagnosis exactly when a real leak lands.
"""

import pytest

from refusal_guard.fragments import (
    FORBIDDEN_FRAGMENTS,
    KNOWN_SAFE_SURFACES,
    assert_fragment_discriminates,
)


class TestTheForbiddenFragmentsDiscriminate:
    """Each fragment, against each known-safe surface -- the guard's own tripwire."""

    @pytest.mark.parametrize(("surface", "baseline"), KNOWN_SAFE_SURFACES)
    @pytest.mark.parametrize("forbidden", FORBIDDEN_FRAGMENTS)
    def test_should_not_match_text_that_is_known_to_be_safe(self, forbidden, surface, baseline):
        """A fragment in the baseline is a defect in the LIST, never in the text.

        Both surfaces are covered because the same list guards both, and the two
        are degenerate under different edits: `(` and `=` can never appear in an
        identifier, so only the message baseline exercises them meaningfully,
        while `TITLE_UPDATE` is the fragment that exists for the code surface and
        the code baseline is the only place a careless suffix would collide.
        """
        assert_fragment_discriminates(surface, baseline, forbidden)
