import tomllib
from pathlib import Path

import nh3

# The allow-lists are data, in sanitization_policy.toml beside this file: they
# change whenever the editor grows a control, and each such change used to be a
# Python edit. Loaded once at import -- the file ships with the adapter and the
# process reads it before it serves anything.
_POLICY_FILE = Path(__file__).with_name("sanitization_policy.toml")

with _POLICY_FILE.open("rb") as _handle:
    _POLICY = tomllib.load(_handle)


def _named_set(key: str) -> set[str]:
    return set(_POLICY[key])


def _per_tag_sets(key: str) -> dict[str, set[str]]:
    return {tag: set(names) for tag, names in _POLICY[key].items()}


_ALLOWED_TAGS = _named_set("tags")
_ALLOWED_ATTRIBUTES = _per_tag_sets("attributes")
_ALLOWED_URL_SCHEMES = _named_set("url_schemes")
_STRIP_WITH_CONTENTS = _named_set("strip_with_contents")
_STYLE_ATTRIBUTE = _POLICY["style"]["attribute"]
_ALIGN_PROPERTY = _POLICY["style"]["property"]
_ALLOWED_ALIGNMENTS = set(_POLICY["style"]["values"])


class Nh3HtmlSanitizer:
    """HtmlSanitizer port implementation, backed by nh3 (Rust `ammonia`).

    nh3 rather than bleach: bleach has been archived and unmaintained since Jan
    2023 and its own README points to nh3. This is the single control between a
    PUT body and stored XSS -- an unmaintained library there is indefensible when
    its authors say to move. It is also an HTML5 tree parser, so it cannot be
    defeated by the malformed-markup tricks that beat regex filters, and it is
    allowlist-based, which the story requires ("never a denylist").

    Lives in the security adapter, next to hashing and tokens: XSS defense is the
    same kind of thing, and a separate adapter module would cost a sys.path entry
    and a test tree for one class.
    """

    def sanitize(self, content: str) -> str:
        return nh3.clean(
            content,
            tags=_ALLOWED_TAGS,
            attributes=_ALLOWED_ATTRIBUTES,
            url_schemes=_ALLOWED_URL_SCHEMES,
            clean_content_tags=_STRIP_WITH_CONTENTS,
            attribute_filter=_keep_only_alignment,
            # Forced server-side rather than trusted from the client: without it a
            # saved link to an attacker's page can reach back through window.opener.
            link_rel="noopener noreferrer",
        )


def _keep_only_alignment(tag: str, attribute: str, value: str) -> str | None:
    """Drop every style declaration that is not a plain text alignment.

    Returning `None` removes the attribute. Only `style` is inspected: every other
    attribute has already passed the tag/attribute allowlist above, and `href` is
    additionally scheme-checked by nh3 itself.

    Whole-value match, not a substring search: `text-align: center; position:
    fixed` must be REJECTED, not partially honoured, so anything carrying more
    than the one declaration is dropped entirely rather than salvaged. A rejected
    alignment costs the user a centred paragraph; a salvaged one could cost them
    an invisible overlay over the page.
    """
    if attribute != _STYLE_ATTRIBUTE:
        return value
    property_name, separator, alignment = value.partition(":")
    if not separator or property_name.strip().lower() != _ALIGN_PROPERTY:
        return None
    if alignment.strip().rstrip(";").strip().lower() not in _ALLOWED_ALIGNMENTS:
        return None
    return value
