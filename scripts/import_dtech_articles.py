"""Import DTECH news sitemap into the article CMS. Safe to run repeatedly.

Run after `alembic upgrade head`: python scripts/import_dtech_articles.py
Pass --refresh to replace previously imported content with the current source.
"""
import argparse
import asyncio
import re
import sys
from pathlib import Path
from urllib.parse import urljoin, urlparse
from xml.etree import ElementTree

import httpx
from bs4 import BeautifulSoup
from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.db.session import AsyncSessionLocal  # noqa: E402
from app.models.article import Article  # noqa: E402
from app.services.article_content import normalize_article_html  # noqa: E402

SITEMAP = "https://dtech.vn/sitemap/sitemap_news.xml"
ALLOWED_TAGS = {"p", "br", "h2", "h3", "h4", "ul", "ol", "li", "strong", "b", "em", "i", "blockquote", "table", "thead", "tbody", "tr", "th", "td", "a", "img", "figure", "figcaption", "span", "div"}
ALLOWED_ATTRS = {"a": {"href", "title"}, "img": {"src", "alt", "title", "width", "height"}, "td": {"colspan", "rowspan"}, "th": {"colspan", "rowspan"}}


def parse_article(url: str, html: str) -> dict | None:
    soup = BeautifulSoup(html, "html.parser")
    heading = soup.select_one("h1")
    content = soup.select_one("div.title1 + div.content") or soup.select_one("div.content")
    if not heading:
        return None
    title = heading.get_text(" ", strip=True)
    if not title:
        return None
    if content and content.get_text(" ", strip=True).startswith("Các bài viết khác"):
        content = None
    if content is None:
        content = BeautifulSoup("<div></div>", "html.parser").div
    for marker in content.find_all(string=lambda s: s and s.strip() == "Các bài viết khác"):
        parent = marker.find_parent("div")
        if parent and parent is not content:
            parent.decompose()
    for tag in content.find_all(["script", "style", "iframe", "form", "button", "noscript"]):
        tag.decompose()
    for tag in content.find_all(True):
        if tag.name not in ALLOWED_TAGS:
            tag.unwrap()
            continue
        attrs = ALLOWED_ATTRS.get(tag.name, set())
        for attr in list(tag.attrs):
            if attr not in attrs:
                del tag[attr]
        for attr in ("href", "src"):
            if tag.has_attr(attr):
                value = urljoin(url, tag[attr])
                if urlparse(value).scheme not in ("http", "https"):
                    del tag[attr]
                else:
                    tag[attr] = value
        if tag.name == "a" and tag.get("href", "").startswith("http"):
            tag["rel"] = "noopener noreferrer"
    description = soup.select_one('meta[name="description"]')
    summary = description.get("content", "").strip() if description else ""
    if not summary:
        summary = content.get_text(" ", strip=True)[:350]
    cover = content.find("img")
    slug = Path(urlparse(url).path).stem
    slug = re.sub(r"[^a-z0-9-]", "-", slug.lower()).strip("-")[:255]
    if not slug:
        return None
    kind = re.search(r"-([a-z]+)-\d+$", slug)
    category = {"gp": "Giải pháp", "cn": "Công nghệ", "bg": "Báo giá", "gt": "Giới thiệu", "kn": "Kinh nghiệm", "careers": "Tuyển dụng"}.get(kind.group(1) if kind else "", "Bài viết")
    return {"slug": slug, "title": title[:500], "summary": summary,
            "content_html": normalize_article_html(content.decode_contents()), "cover_image_url": cover.get("src") if cover else None,
            "category": category, "meta_description": summary[:500],
            "source_url": url, "published": True}


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true", help="Update existing imported articles")
    args = parser.parse_args()
    async with httpx.AsyncClient(timeout=30, follow_redirects=True, headers={"User-Agent": "AIDE-article-import/1.0"}) as client:
        response = await client.get(SITEMAP)
        response.raise_for_status()
        root = ElementTree.fromstring(response.text)
        urls = [node.text for node in root.findall(".//{*}url/{*}loc") if node.text]
        urls = list(dict.fromkeys(url for url in urls if urlparse(url).netloc == "dtech.vn" and url.endswith(".html")))
        semaphore = asyncio.Semaphore(5)

        async def fetch(url):
            async with semaphore:
                try:
                    res = await client.get(url)
                    res.raise_for_status()
                    return url, parse_article(url, res.text), None
                except Exception as exc:
                    return url, None, str(exc)

        results = await asyncio.gather(*(fetch(url) for url in urls))
    created = updated = skipped = 0
    async with AsyncSessionLocal() as db:
        for url, values, error in results:
            if error or not values:
                skipped += 1
                print(f"SKIP {url}: {error or 'no article content'}")
                continue
            existing = await db.scalar(select(Article).where(Article.source_url == url))
            if existing is None:
                existing = await db.scalar(select(Article).where(Article.slug == values["slug"]))
            if existing:
                if args.refresh:
                    for key, value in values.items():
                        setattr(existing, key, value)
                    updated += 1
                else:
                    skipped += 1
            else:
                db.add(Article(**values))
                created += 1
        await db.commit()
    print(f"Imported: {created} new, {updated} updated, {skipped} skipped from {len(urls)} URLs")


if __name__ == "__main__":
    asyncio.run(main())
