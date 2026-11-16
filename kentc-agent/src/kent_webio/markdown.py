"""Render chat Markdown with an allowlist of elements and link targets."""

from urllib.parse import urlsplit

from bs4 import BeautifulSoup, NavigableString
from markdown import Markdown

ELEMENTS = {
    "a", "blockquote", "br", "code", "em", "h1", "h2", "h3", "h4", "h5", "h6", "hr", "li", "ol", "p", "pre",
    "strong", "table", "tbody", "td", "th", "thead", "tr", "ul",
}


def web_url(value: str) -> bool:
    if not value.lower().startswith(("https://", "http://")) or any(ord(char) < 33 for char in value):
        return False
    try:
        return bool(urlsplit(value).hostname)
    except ValueError:
        return False


def render_markdown(text: str) -> str:
    parser = Markdown(extensions=["fenced_code", "sane_lists", "tables", "nl2br"])
    parser.preprocessors.deregister("html_block")
    parser.inlinePatterns.deregister("html")
    try:
        markup = parser.convert(text)
    except RecursionError:
        return ""
    content = BeautifulSoup(markup, "html.parser")
    for tag in content.find_all(True):
        if tag.name == "img":
            tag.replace_with(NavigableString(tag.get("alt", "")))
        elif tag.name not in ELEMENTS:
            if tag.name is not None:
                tag.decompose()
        elif tag.name == "a":
            href = tag.get("href", "")
            if web_url(href):
                tag.attrs = {"href": href, "target": "_blank", "rel": "noopener noreferrer"}
            else:
                tag.unwrap()
        elif tag.name == "ol" and (start := tag.get("start", "")).isdigit() and start.isascii():
            tag.attrs = {"start": start}
        else:
            tag.attrs = {}
    return content.decode_contents()
