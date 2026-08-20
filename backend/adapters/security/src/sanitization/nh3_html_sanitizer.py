import nh3

# Matches what the editor can produce. Tiptap emits <strong>/<em>; the story's own
# fixtures pin <b>/<i>. Both are kept -- an allowlist narrower than the editor
# deletes users' formatting on save, silently.
#
# The block half (blockquote/pre/code/hr/s) was added when story 5 migrated the
# editor to the StarterKit BLOCK schema: the toolbar grew Цитата, Блок кода,
# горизонтальная линейка and зачёркивание, and this list did not. A tag the
# editor can produce but the sanitizer strips is not a hardened boundary, it is
# silent data loss discovered on reload -- the user formats, saves, comes back,
# and the quote is a bare paragraph. The same tags are what a markdown-to-HTML
# conversion emits (see MarkdownHtmlConverter), so the conversion path depends on
# this list too.
_ALLOWED_TAGS = {
    "h1",
    "h2",
    "h3",
    "p",
    "ul",
    "ol",
    "li",
    "strong",
    "em",
    "b",
    "i",
    "u",
    "s",
    "a",
    "br",
    "blockquote",
    "pre",
    "code",
    "hr",
    # The table half, added with the editor's «вставить таблицу» control. Every
    # tag Tiptap's Table extension can emit is listed: a table whose <tbody> is
    # stripped is not a degraded table, it is a pile of unwrapped cell text, and
    # the loss is only discovered on reload.
    "table",
    "thead",
    "tbody",
    "tfoot",
    "tr",
    "th",
    "td",
    # `img` is deliberately NOT here, and its absence is a decision rather than
    # an oversight. Both export renderers refuse outbound fetches on purpose
    # (see WeasyPrintPdfRenderer._blocked_url_fetcher -- the document HTML is
    # user-controlled, so resolving a src is an SSRF vector). An allowed <img>
    # would therefore render in the editor and vanish from every PDF and DOCX
    # the user downloads, which is a worse answer than not offering it: the loss
    # is invisible until the file is opened somewhere else.
}

# `style` on the block nodes carries text alignment, which TextAlign renders as
# `style="text-align: …"` on the heading/paragraph it applies to. Without it the
# centre-align button was another silent-loss control. nh3 has no CSS property
# filter, so the value is constrained before it ever reaches here -- see
# _strip_unsafe_styles below.
_ALLOWED_ATTRIBUTES = {
    "a": {"href", "title"},
    # Merged cells, and nothing else. `colwidth` -- which Tiptap writes when a
    # column is resized -- is deliberately absent: it is a comma-separated pixel
    # list this filter would have to parse to trust, and losing a column width is
    # a cosmetic regression where losing a merge would corrupt the table's shape.
    "th": {"colspan", "rowspan"},
    "td": {"colspan", "rowspan"},
    "p": {"style"},
    "h1": {"style"},
    "h2": {"style"},
    "h3": {"style"},
}

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

# The ONLY declaration a stored style attribute may carry. nh3 filters tags,
# attributes and URL schemes, but it does not parse CSS -- so allowing `style`
# through unexamined would hand an attacker the whole property space: a
# `position: fixed` overlay covering the page (clickjacking), `url(...)` fetching
# a tracker on open, or a legacy `expression()`. The editor produces exactly one
# style declaration, so the filter below is an allowlist of one property with an
# allowlist of four values rather than an attempt to sanitize CSS in general.
_ALIGN_PROPERTY = "text-align"
_ALLOWED_ALIGNMENTS = {"left", "right", "center", "justify"}
_STYLE_ATTRIBUTE = "style"


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
