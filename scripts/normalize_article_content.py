"""Normalize existing article HTML in the configured database. Idempotent."""
import asyncio
import sys
from pathlib import Path

from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.db.session import AsyncSessionLocal  # noqa: E402
from app.models.article import Article  # noqa: E402
from app.services.article_content import normalize_article_html  # noqa: E402


async def main():
    changed = 0
    async with AsyncSessionLocal() as db:
        articles = (await db.execute(select(Article))).scalars().all()
        for article in articles:
            clean = normalize_article_html(article.content_html)
            if clean != article.content_html:
                article.content_html = clean
                changed += 1
        await db.commit()
    print(f"Normalized {changed} of {len(articles)} articles")


if __name__ == "__main__":
    asyncio.run(main())
