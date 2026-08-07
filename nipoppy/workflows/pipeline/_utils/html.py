"""Utilities for processing HTML strings."""

from html.parser import HTMLParser
from typing import Iterable, Optional

COMMON_HTML_TAGS = {
    "html",
    "head",
    "body",
    "title",
    "div",
    "span",
    "p",
    "br",
    "hr",
    "b",
    "i",
    "u",
    "strong",
    "em",
    "a",
    "img",
    "ul",
    "ol",
    "li",
    "table",
    "tr",
    "td",
    "th",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "form",
    "input",
    "button",
    "label",
    "section",
    "article",
    "header",
    "footer",
}


class SelectiveHTMLStripper(HTMLParser):
    """HTML parser that strips specified tags and keeps others."""

    def __init__(self, tags=None):
        """Initialize the HTML parser with specified tags to strip."""
        super().__init__()
        self.strip_tags = set(tags or COMMON_HTML_TAGS)
        self.fed = []

    def handle_starttag(self, tag, attrs):
        """Handle start tag."""
        if tag not in self.strip_tags:
            # no change (i.e. preserve case)
            self.fed.append(self.get_starttag_text())

    def handle_endtag(self, tag):
        """Handle end tag."""
        if tag not in self.strip_tags:
            self.fed.append(f"</{tag}>")

    def handle_startendtag(self, tag, attrs):
        """Handle self-closing tag."""
        if tag not in self.strip_tags:
            # no change (i.e. preserve case)
            self.fed.append(self.get_starttag_text())

    def handle_data(self, d):
        """Handle data."""
        self.fed.append(d)

    def get_data(self):
        """Get the processed data as a single string."""
        return "".join(self.fed)


def strip_html_tags(html: str, tags: Optional[Iterable] = None):
    """Strip specified HTML tags from a string."""
    s = SelectiveHTMLStripper(tags=tags)
    s.feed(html)
    return s.get_data()
