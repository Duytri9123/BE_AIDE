"""Clean and simplify article HTML before storing or rendering it."""
from urllib.parse import urlparse

import bleach
from bs4 import BeautifulSoup, NavigableString


ALLOWED_TAGS = {"p", "br", "h2", "h3", "h4", "ul", "ol", "li", "strong", "b", "em", "i", "blockquote", "table", "thead", "tbody", "tr", "th", "td", "a", "img", "figure", "figcaption", "span", "div"}
ALLOWED_ATTRS = {
    "a": ["href", "title"],
    "img": ["src", "alt", "title", "width", "height"],
    "td": ["colspan", "rowspan"],
    "th": ["colspan", "rowspan"],
}


def normalize_article_html(value: str | None) -> str:
    if not value:
        return ""
    clean = bleach.clean(
        value, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS,
        protocols={"http", "https"}, strip=True,
    )
    soup = BeautifulSoup(clean, "html.parser")
    while wrappers := soup.find_all(["span", "div"]):
        for tag in wrappers:
            if tag.parent is not None:
                tag.unwrap()
    for tag in list(soup.find_all(["b", "i"])):
        tag.name = {"b": "strong", "i": "em"}[tag.name]
    for heading in soup.find_all(["h2", "h3", "h4"]):
        for child in list(heading.find_all(["strong", "em"])):
            child.unwrap()
    for img in list(soup.find_all("img")):
        if urlparse(img.get("src", "")).scheme not in {"http", "https"}:
            img.decompose()
    for a in soup.find_all("a"):
        if urlparse(a.get("href", "")).scheme not in {"http", "https"}:
            a.unwrap()
        else:
            a["rel"] = "noopener noreferrer"
    for tag in list(soup.find_all(["p", "li", "h2", "h3", "h4"])):
        if not tag.get_text(strip=True) and not tag.find("img"):
            tag.decompose()
    return "\n".join(str(node).strip() for node in soup.contents if not isinstance(node, NavigableString) or node.strip()).strip()
