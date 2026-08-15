from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class PageSettings:
    """Page geometry for a whole document, exactly as stored.

    Frozen over the nine read-side keys `documents_get.yaml` declares. There is
    deliberately no factory that fills in a default preset: the story exists to
    keep "never configured" distinguishable from "configured to today's preset",
    and a `PageSettings.default()` sitting here would be reached for on the read
    path within a release. Absence is carried as `None` from column to wire.

    `from_stored` -- the resolver that reads a missing key as its default and
    preserves an undefined one -- belongs to scenarios 2.3/2.4 and is not written
    yet. Until then the column only ever holds SQL NULL or a server-written object.
    """

    page_size: str
    orientation: str
    margins_mm: Mapping[str, float]
    font_size_pt: float
    line_height: float
    header_text: str | None
    footer_text: str | None
    show_page_numbers: bool
    skip_number_on_first_page: bool
