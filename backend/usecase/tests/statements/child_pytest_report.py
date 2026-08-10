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

    @staticmethod
    def expected_header_line(key: str, value: object) -> str:
        """What a session header line looks like, so only this class knows.

        The caller compares whole lines; without this it would have to spell the
        `key: value` shape itself and drift from what `header_line` matches on.
        """
        return f"{key}: {value}"

    def header_line(self, key: str) -> str:
        """The whole `key: ...` line from the session header, for equality.

        Returns a description of the absence rather than raising, so the caller's
        assertion reports both what it wanted and what it got in one message.
        """
        prefix = f"{key}:"
        return next(
            (line.rstrip() for line in self.output.splitlines() if line.startswith(prefix)),
            f"<no '{prefix}' line in the child's header>",
        )

    def section(self, name: str) -> str:
        """The body between a named banner and the next one, or "" if absent."""
        lines = self.output.splitlines()
        banners = self._banners()
        for index, (number, banner) in enumerate(banners):
            if banner != name:
                continue
            end = banners[index + 1][0] if index + 1 < len(banners) else len(lines)
            return "\n".join(lines[number + 1 : end])
        return ""

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
            for line in self.section("FAILURES").splitlines()
            if (match := _FAILING_TEST.match(line.rstrip()))
        }

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
