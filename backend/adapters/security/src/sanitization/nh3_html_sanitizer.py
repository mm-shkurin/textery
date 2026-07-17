import nh3

# Matches what the editor can produce. Tiptap emits <strong>/<em>; the story's own
# fixtures pin <b>/<i>. Both are kept -- an allowlist narrower than the editor
# deletes users' formatting on save, silently.
_ALLOWED_TAGS = {"h1", "h2", "h3", "p", "ul", "ol", "li", "strong", "em", "b", "i", "u", "a", "br"}

_ALLOWED_ATTRIBUTES = {"a": {"href", "title"}}

# Deliberately the same set the client's Link extension permits (see
# 05-manual-mode/decisions/link-url-input-decision.md, which records Tiptap's
# allowlist). A server list narrower than the client's is a data-loss bug that
# only shows up on reload: the user creates a link, sees it render, saves, comes
# back, and it is gone. `javascript:` is in neither list.
_ALLOWED_URL_SCHEMES = {
    "http",
    "https",
    "mailto",
    "tel",
    "ftp",
    "ftps",
    "callto",
    "sms",
    "cid",
    "xmpp",
}

# Removed WITH their contents, not just unwrapped. Dropping only the tag would
# leave `alert(1)` sitting in the document as text -- technically "stripped",
# still the payload.
_STRIP_WITH_CONTENTS = {"script", "style"}


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
            # Forced server-side rather than trusted from the client: without it a
            # saved link to an attacker's page can reach back through window.opener.
            link_rel="noopener noreferrer",
        )
