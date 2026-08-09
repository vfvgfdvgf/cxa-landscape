"""Safe HTML and JSON helpers used by public templates and AI content."""

import json

import nh3
from django.utils.safestring import mark_safe

ALLOWED_TAGS = {
    "a", "abbr", "b", "blockquote", "br", "code", "div", "em", "figcaption",
    "figure", "h2", "h3", "h4", "hr", "i", "img", "li", "ol", "p", "pre",
    "span", "strong", "table", "tbody", "td", "th", "thead", "tr", "u", "ul",
}
ALLOWED_ATTRIBUTES = {
    "a": {"href", "title", "target"},
    "img": {"src", "alt", "title", "width", "height", "loading", "decoding"},
    "div": {"class"},
    "span": {"class"},
    "table": {"class"},
    "th": {"scope", "colspan", "rowspan"},
    "td": {"colspan", "rowspan"},
}


def sanitize_html(value: str) -> str:
    """Sanitize rich text with an allowlist instead of regex replacements."""
    if not value:
        return ""
    return nh3.clean(
        str(value),
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        url_schemes={"http", "https", "mailto", "tel"},
        link_rel="noopener noreferrer",
        strip_comments=True,
    )


def safe_html(value: str):
    return mark_safe(sanitize_html(value))


def safe_json_dumps(value) -> str:
    """Serialize JSON safely for embedding inside an application/ld+json script."""
    payload = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return (
        payload.replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )
