"""Reading a child pytest run's report as structured values rather than as text.

Kept apart from the gate that runs the child so the gate's assertions read as
claims rather than as string surgery. Everything here exists to make the
assertions *whole-value*: a substring search over a pytest report is a trap --
`"1 passed" in output` also matches `11 passed`, and a sentence looked for
anywhere in the output may be sitting in the warnings summary of a run that
otherwise reported a pass.
"""

import subprocess
from functools import cached_property

from statements.child_report_banners import (
    FAILURES_SECTION,
    Banner,
    banners_in,
    counts_in,
    failing_test_names_in,
)

__all__ = ["FAILURES_SECTION", "ChildPytestReport"]


class ChildPytestReport:
    """One finished child run, addressable by header line, section and tally."""

    def __init__(self, completed: "subprocess.CompletedProcess[str]") -> None:
        self._completed = completed

    @property
    def exit_code(self) -> int:
        return self._completed.returncode

    @cached_property
    def output(self) -> str:
        """The two streams, joined so neither can eat the other's lines.

        `"\\n".join` rather than `+`: every reading below is positional over this
        text -- the tally is the last banner, a section is the span between two --
        so a stdout without a trailing newline merged its final tally banner into
        stderr's first line, and the tally then read `{}` while the gate blamed
        pytest for it.
        """
        return "\n".join((self._completed.stdout, self._completed.stderr))

    @cached_property
    def _stdout_line_count(self) -> int:
        """How many of the joined lines came from stdout, so a banner can be attributed.

        The join appends stderr *after* stdout, and a banner is recognised by line shape
        alone, with no idea which stream a line came from -- so a child whose
        stderr carries a `=+ ... =+` line of its own has that line read as pytest's
        closing tally. Counting the first stream's lines is what makes the streams
        distinguishable again without dropping either from the report.

        Under-counts by design when stdout ends in a newline: `splitlines()` drops
        the trailing empty field, and the separator then contributes a blank line
        that this count attributes to stderr. A blank line is not a banner, so the
        boundary line's side never changes an answer -- and erring toward stderr can
        only ever make the tally stricter, never let a stderr banner through.
        """
        return len(self._completed.stdout.splitlines())

    @cached_property
    def _lines(self) -> list[str]:
        """The joined report, split once.

        Every reading below is positional over these lines -- a header prefix, a
        banner index, the span between two banners -- and a finished child's output
        cannot change, so the split is done once rather than per question asked.
        """
        return self.output.splitlines()

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
                for line in self._lines
                if line.startswith(prefix)
            ),
            f"<no '{key}:' line in the child's header>",
        )

    def section(self, name: str) -> str:
        """The body between a named banner and the next one, or "" if absent."""
        banners = self._banners
        return next(
            (
                "\n".join(self._lines[banner.line_number + 1 : end])
                for banner, end in zip(banners, self._body_ends(banners), strict=True)
                if banner.name == name
            ),
            "",
        )

    def _body_ends(self, banners: list[Banner]) -> list[int]:
        """Where each banner's body stops.

        A body ends where the next banner starts, and the last one's at the end of
        the report -- so the ends are the starts shifted by one.
        """
        return [banner.line_number for banner in banners[1:]] + [len(self._lines)]

    def failing_test_names(self) -> set[str]:
        """Which tests the FAILURES section is actually about, as a set to compare whole.

        The alternative -- `name in section` for the test that should have failed
        and `other not in section` for the one that should not -- is vacuous on the
        negative half: `section()` returns "" when there is no FAILURES banner at
        all, so "the clean test is not named" passes on a child that failed nothing
        and on a child that never ran. A set equality carries both halves and
        cannot be satisfied by an empty section.
        """
        return failing_test_names_in(self.section(FAILURES_SECTION))

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

        Read off the *stdout* banners rather than off `self._banners[-1]`. pytest
        writes its report to stdout; anything on stderr is the child's own noise --
        a wrapper script echoing a summary, a nested pytest, a plugin drawing its
        own separator -- and joined after stdout it would otherwise be the last
        banner in the report and be reported as pytest's closing tally, a count no
        pytest ever wrote. `section()` deliberately still spans the banners of both
        streams: a section is bounded by whatever line comes next, and discarding
        stderr to make the tally right would move where stdout's sections end.
        """
        banners = self._stdout_banners
        if not banners:
            return {}
        return counts_in(banners[-1].name)

    @cached_property
    def _stdout_banners(self) -> list[Banner]:
        """The banners pytest itself drew, as opposed to the ones stderr contributed."""
        return [
            banner for banner in self._banners if banner.line_number < self._stdout_line_count
        ]

    @cached_property
    def _banners(self) -> list[Banner]:
        """Every banner line in the report, found once.

        Cached for the same reason `_lines` is: a finished child's output cannot
        change, and this is asked twice per section read -- `failing_test_names`
        and `failure_text_contains` each go through `section`. Since the markup
        strip landed, each of those asks re-ran a regex substitution over every
        line of the report to rediscover banners already found.
        """
        return banners_in(self._lines)
