"""Reading a child pytest run's report as structured values rather than as text.

Kept apart from the gate that runs the child so the gate's assertions read as
claims rather than as string surgery. Everything here exists to make the
assertions *whole-value*: a substring search over a pytest report is a trap --
`"1 passed" in output` also matches `11 passed`, and a sentence looked for
anywhere in the output may be sitting in the warnings summary of a run that
otherwise reported a pass.
"""

import re
import subprocess

# Banner lines pytest draws around every report section, e.g.
# `======== FAILURES ========` and the closing `======== 1 failed in 4s ========`.
_BANNER = re.compile(r"^=+ (?P<name>.+?) =+$")
# The per-test sub-banner pytest draws inside FAILURES, e.g. `____ test_probe ____`.
# Underscored rather than `=`, so `_BANNER` leaves these inside the section body.
_FAILING_TEST = re.compile(r"^_+ (?P<name>\S+?) _+$")
_COUNT = re.compile(r"^(?P<count>\d+) (?P<outcome>[a-z]+)$")
_ELAPSED = re.compile(r" in \d[\d.]*s.*$")

# The section pytest writes only for tests that actually failed. Named because
# both this module and the join test address it, and a bare literal in two files
# is a rename waiting to leave one of them silently reading "".
FAILURES_SECTION = "FAILURES"


class ChildPytestReport:
    """One finished child run, addressable by header line, section and tally."""

    def __init__(self, completed: "subprocess.CompletedProcess[str]") -> None:
        self._completed = completed

    @property
    def exit_code(self) -> int:
        return self._completed.returncode

    @property
    def output(self) -> str:
        return self._completed.stdout + self._completed.stderr

    @property
    def tail(self) -> str:
        return self.output[-2000:]

    def header_values(self, keys: tuple[str, ...]) -> dict[str, str]:
        """What each named `key: ...` session-header line says, as one mapping.

        Returned whole so the caller pins every header line in a single equality.
        Asserted one key at a time, the first mismatch raises and the second line
        is never looked at -- a child that found neither the right rootdir nor the
        right configfile would report only the first as wrong.

        The `key: ` shape is spelled here and nowhere else, so a caller's
        expectation is the bare value and cannot drift from what this matches on.
        """
        return {key: self._header_value(key) for key in keys}

    def _header_value(self, key: str) -> str:
        """The text after `key: `, or a description of the absence.

        Described rather than raised, so the caller's assertion reports both what
        it wanted and what it got in one message.
        """
        prefix = f"{key}: "
        return next(
            (
                line.rstrip()[len(prefix) :]
                for line in self.output.splitlines()
                if line.startswith(prefix)
            ),
            f"<no '{key}:' line in the child's header>",
        )

    def section(self, name: str) -> str:
        """The body between a named banner and the next one, or "" if absent."""
        lines = self.output.splitlines()
        banners = self._banners()
        # Each banner's body ends where the next one starts, and the last one's at
        # the end of the report -- so the ends are the starts shifted by one.
        ends = [number for number, _ in banners[1:]] + [len(lines)]
        return next(
            (
                "\n".join(lines[number + 1 : end])
                for (number, banner), end in zip(banners, ends, strict=True)
                if banner == name
            ),
            "",
        )

    def failing_test_names(self) -> set[str]:
        """Which tests the FAILURES section is actually about, as a set to compare whole.

        The alternative -- `name in section` for the test that should have failed
        and `other not in section` for the one that should not -- is vacuous on the
        negative half: `section()` returns "" when there is no FAILURES banner at
        all, so "the clean test is not named" passes on a child that failed nothing
        and on a child that never ran. A set equality carries both halves and
        cannot be satisfied by an empty section.
        """
        return {
            match.group("name")
            for line in self.section(FAILURES_SECTION).splitlines()
            if (match := _FAILING_TEST.match(line.rstrip()))
        }

    def failure_text_contains(self, text: str) -> bool:
        """Whether the FAILURES section carries `text`, scoped rather than global.

        The caller must not reach for `section(...)` and search the result itself:
        every other reading of the child's output is parsed in here, and the whole
        reason this is scoped to FAILURES is that the sentence the gate looks for
        also appears in the warnings summary of a run where the gate is inert.
        """
        return text in self.section(FAILURES_SECTION)

    def summary_counts(self) -> dict[str, int]:
        """The final banner's tally, parsed whole: `1 failed in 4.37s` -> `{failed: 1}`.

        The whole dict is the value to compare against, so a second failure, a
        skip, or a stray warning cannot hide behind a match on one of the terms.
        """
        banners = self._banners()
        if not banners:
            return {}
        return {
            match.group("outcome"): int(match.group("count"))
            for part in _ELAPSED.sub("", banners[-1][1]).split(", ")
            if (match := _COUNT.match(part.strip()))
        }

    def _banners(self) -> list[tuple[int, str]]:
        return [
            (number, match.group("name").strip())
            for number, line in enumerate(self.output.splitlines())
            if (match := _BANNER.match(line.rstrip()))
        ]
