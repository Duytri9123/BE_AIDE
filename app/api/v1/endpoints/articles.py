from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.article import Article
from app.services.article_content import normalize_article_html

router = APIRouter()


class ArticleCard(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    slug: str
    title: str
    summary: str | None
    cover_image_url: str | None
    category: str | None
    source_url: str | None


class ArticleDetail(ArticleCard):
    content_html: str
    meta_description: str | None


@router.get("", response_model=dict)
async def list_articles(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: str | None = None,
    q: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    filters = [Article.published.is_(True)]
    if category:
        filters.append(Article.category == category)
    if q:
        filters.append(Article.title.ilike(f"%{q}%"))
    count = await db.scalar(select(func.count()).select_from(Article).where(*filters))
    result = await db.execute(
        select(Article).where(*filters).order_by(Article.created_at.desc(), Article.id.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )
    return {"items": [ArticleCard.model_validate(row) for row in result.scalars()],
            "total": count or 0, "page": page, "page_size": page_size}


@router.get("/{slug}", response_model=ArticleDetail)
async def get_article(slug: str, db: AsyncSession = Depends(get_db)):
    article = await db.scalar(select(Article).where(Article.slug == slug, Article.published.is_(True)))
    if article is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài viết")
    result = ArticleDetail.model_validate(article)
    result.content_html = normalize_article_html(result.content_html)
    return result
