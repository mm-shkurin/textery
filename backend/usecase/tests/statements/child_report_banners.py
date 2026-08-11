"""The banner grammar of a pytest report: what a separator line is, and what it says.

Split out of `child_pytest_report.py` when that file passed the 200-line limit
adding the stream attribution the tally now needs. The division is this package's
usual one -- `forgotten_await_probes.py` carries probe sources, `arming_probe.py`
carries vectors -- so `ChildPytestReport` reads as *one finished child run,
addressed by header, section and tally*, and this file holds the line-shapes those
questions are answered with.

Nothing here knows about streams, caching, or a `CompletedProcess`. It is given
lines and gives back structure.
"""

import re
from typing import NamedTuple

# Banner lines pytest draws around every report section, e.g.
# `======== FAILURES ========` and the closing `======== 1 failed in 4s ========`.
_BANNER = re.compile(r"^=+ (?P<name>.+?) =+$")
# The per-test sub-banner pytest draws inside FAILURES, e.g. `____ test_probe ____`.
# Underscored rather than `=`, so `_BANNER` leaves these inside the section body.
_FAILING_TEST = re.compile(r"^_+ (?P<name>\S+?) _+$")
_COUNT = re.compile(r"^(?P<count>\d+) (?P<outcome>[a-z]+)$")
# The SGR escapes pytest's `write_sep` wraps a whole separator line in once markup
# is on -- which it is in a non-tty whenever `PY_COLORS=1` or `FORCE_COLOR` is set.
# Stripped before `_BANNER` is tried, because that pattern is anchored: a coloured
# report would otherwise answer no banners at all, and tally as the empty dict a
# report that drew no banner honestly answers.
_MARKUP = re.compile(r"\x1b\[[0-9;]*m")
_ELAPSED = re.compile(r" in \d[\d.]*s.*$")

# The section pytest writes only for tests that actually failed. Named because
# this module, the report reader and the join test all address it, and a bare
# literal in three files is a rename waiting to leave one of them silently
# reading "".
FAILURES_SECTION = "FAILURES"


class Banner(NamedTuple):
    """One `==== name ====` line: where it sits in the report, and what it announces.

    Named rather than left an anonymous pair because the position is read in three
    places and the tally reads the name off the last one -- `banners[-1][1]` does
    not say which half of the pair the tally is parsed from.
    """

    line_number: int
    name: str


def banners_in(lines: list[str]) -> list[Banner]:
    """Every banner line among `lines`, with the line number it was found at."""
    return [
        Banner(number, match.group("name").strip())
        for number, line in enumerate(lines)
        if (match := _BANNER.match(_MARKUP.sub("", line).rstrip()))
    ]


def counts_in(banner_name: str) -> dict[str, int]:
    """A tally banner's name parsed whole: `1 failed in 4.37s` -> `{'failed': 1}`."""
    return {
        match.group("outcome"): int(match.group("count"))
        for part in _ELAPSED.sub("", banner_name).split(", ")
        if (match := _COUNT.match(part.strip()))
    }


def failing_test_names_in(section_body: str) -> set[str]:
    """The `_____ test_x _____` sub-banners a FAILURES body carries, as names."""
    return {
        match.group("name")
        for line in section_body.splitlines()
        if (match := _FAILING_TEST.match(line.rstrip()))
    }
