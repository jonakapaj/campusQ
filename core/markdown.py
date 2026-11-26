"""Markdown -> safe HTML for user content.

Raw HTML in the source is escaped, and the rendered output is sanitized with nh3
against a small allowlist, so <script>, event handlers and javascript: links can
never reach the page. Images are not allowed in Markdown: they would let anyone
embed tracking pixels; pictures are uploaded instead.
"""

import markdown
import nh3
from markdown.extensions import Extension

ALLOWED_TAGS = {
    "p", "br", "strong", "em", "del", "code", "pre", "blockquote", "ul", "ol", "li",
    "a", "h3", "h4", "hr", "span", "div", "table", "thead", "tbody", "tr", "th", "td",
}  # fmt: skip
ALLOWED_ATTRIBUTES = {
    "a": {"href", "title"},
    # Pygments' code highlighting (added in Milestone 4) uses CSS classes only.
    "span": {"class"},
    "div": {"class"},
    "code": {"class"},
    "pre": {"class"},
}
URL_SCHEMES = {"http", "https", "mailto"}


class _NoRawHtml(Extension):
    """Treat raw HTML in the source as plain text (escaped), not as markup."""

    def extendMarkdown(self, md: markdown.Markdown) -> None:  # noqa: N802 (markdown API)
        md.preprocessors.deregister("html_block")
        md.inlinePatterns.deregister("html")


def render_markdown(text: str) -> str:
    html = markdown.markdown(
        text,
        extensions=["fenced_code", "sane_lists", "tables", _NoRawHtml()],
        output_format="html",
    )
    return nh3.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        url_schemes=URL_SCHEMES,
        link_rel="nofollow noopener noreferrer ugc",
    )
