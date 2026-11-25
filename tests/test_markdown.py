import re

import pytest

from core.markdown import render_markdown


def test_basic_markdown() -> None:
    html = render_markdown("**bold** and *it* and `code`\n\n- a\n- b")

    assert "<strong>bold</strong>" in html
    assert "<em>it</em>" in html
    assert "<code>code</code>" in html
    assert "<li>a</li>" in html


def test_albanian_characters_survive() -> None:
    assert "Çfarë është ëndrra?" in render_markdown("Çfarë është ëndrra?")


@pytest.mark.parametrize(
    "source",
    [
        "<script>alert(1)</script>",
        "<img src=x onerror=alert(1)>",
        '<a href="#" onclick="alert(1)">x</a>',
        "<iframe src='https://evil.example'></iframe>",
        "<style>body{display:none}</style>",
    ],
)
def test_raw_html_is_escaped_not_rendered(source: str) -> None:
    html = render_markdown(source)

    # No real tag other than the paragraph wrapper, and no attribute at all.
    assert re.findall(r"<(/?)(\w+)", html) in ([("", "p"), ("/", "p")], [])
    assert not re.search(r"<\w+[^>]*\son\w+=", html)
    assert "&lt;" in html  # shown as text instead


@pytest.mark.parametrize(
    "source",
    [
        "[click](javascript:alert(1))",
        "[click](JaVaScRiPt:alert(1))",
        "[click](data:text/html;base64,PHNjcmlwdD4=)",
        "[click](vbscript:msgbox)",
    ],
)
def test_dangerous_link_schemes_are_removed(source: str) -> None:
    html = render_markdown(source).lower()

    assert "javascript:" not in html
    assert "data:" not in html
    assert "vbscript:" not in html


def test_links_get_nofollow_and_noopener() -> None:
    html = render_markdown("[CampusQ](https://example.com)")

    assert 'href="https://example.com"' in html
    assert "nofollow" in html
    assert "noopener" in html


def test_markdown_images_are_not_rendered() -> None:
    html = render_markdown("![pixel](https://tracker.example/p.gif)")

    assert "<img" not in html
    assert "tracker.example" not in html or "<img" not in html


def test_fenced_code_is_kept_and_escaped() -> None:
    html = render_markdown("```\n<b>not bold</b>\n```")

    assert "<pre>" in html
    assert "&lt;b&gt;" in html
    assert "<b>" not in html


def test_headings_are_limited() -> None:
    html = render_markdown("# Huge\n\n### Ok")

    assert "<h1>" not in html  # stripped so posts can't impersonate page titles
    assert "<h3>Ok</h3>" in html


def test_blockquotes_and_comparisons_work() -> None:
    html = render_markdown("> cituar\n\nnëse a < b dhe c > d")

    assert "<blockquote>" in html
    assert "a &lt; b" in html
    assert "c &gt; d" in html
