"""The one off-preset PageSettings both layers assert against.

Lives under `domain/tests` rather than `usecase/tests` because the domain test
needs it and the domain module may not import from usecase -- not even in tests.
The two `statements` directories carry no `__init__.py` and merge into one
implicit namespace package (see `backend/pyproject.toml`), so `usecase/tests`
reaches this the legal way round: usecase depends on domain.

There was a byte-identical second copy of this literal in the domain test file.
Two copies of an EXPECTED value is the dangerous kind of duplication: both round-
trip assertions compare a stored object against their own copy, so editing one
copy alone does not fail anything -- it just quietly stops the two layers from
agreeing on what "configured" means.
"""

from document.page_settings import PageSettings


def configured_page_settings() -> PageSettings:
    """Deliberately nothing like a plausible default preset.

    A4/portrait would be indistinguishable from a default someone materialized on
    the way through, so every value here is off-preset: if a round-trip assertion
    ever passes against constructed defaults, these values are what break it.
    """
    return PageSettings(
        page_size="A5",
        orientation="landscape",
        margins_mm={"top": 15.0, "right": 10.0, "bottom": 15.0, "left": 25.0},
        font_size_pt=12.5,
        line_height=1.15,
        header_text="Кафедра прикладной математики",
        footer_text=None,
        show_page_numbers=True,
        skip_number_on_first_page=False,
    )
