from sqladmin import ModelView
from app.models.article import Article
from markupsafe import Markup
import bleach


def render_article_html(model, _attribute):
    return Markup(bleach.clean(
        model.content_html or "",
        tags={"p", "br", "h2", "h3", "h4", "ul", "ol", "li", "strong", "b", "em", "i", "blockquote", "table", "thead", "tbody", "tr", "th", "td", "a", "img", "figure", "figcaption", "span", "div"},
        attributes={"a": ["href", "title", "rel"], "img": ["src", "alt", "title", "width", "height"], "td": ["colspan", "rowspan"], "th": ["colspan", "rowspan"]},
        protocols={"http", "https"}, strip=True,
    ))


class ArticleAdmin(ModelView, model=Article):
    name = "Bài viết"
    name_plural = "Quản lý bài viết"
    icon = "fa-solid fa-newspaper"
    category = "Nội dung website"
    column_list = [Article.id, Article.title, Article.slug, Article.category, Article.published, Article.updated_at]
    column_searchable_list = [Article.title, Article.slug, Article.category]
    column_sortable_list = [Article.id, Article.title, Article.updated_at]
    column_default_sort = [(Article.updated_at, True)]
    column_details_list = [Article.title, Article.category, Article.published, Article.summary,
                           Article.content_html, Article.cover_image_url, Article.slug,
                           Article.meta_description, Article.source_url, Article.created_at, Article.updated_at]
    column_formatters_detail = {Article.content_html: render_article_html}
    form_columns = [Article.title, Article.slug, Article.summary, Article.content_html,
                    Article.cover_image_url, Article.category, Article.meta_description,
                    Article.source_url, Article.published]
    form_widget_args = {"summary": {"rows": 5}, "content_html": {"rows": 25},
                        "meta_description": {"rows": 3}}
    column_labels = {
        Article.title: "Tiêu đề", Article.slug: "Đường dẫn (slug)",
        Article.summary: "Tóm tắt", Article.content_html: "Nội dung HTML",
        Article.cover_image_url: "Ảnh đại diện (URL)", Article.category: "Danh mục",
        Article.meta_description: "Mô tả SEO", Article.source_url: "Nguồn bài viết",
        Article.published: "Xuất bản", Article.updated_at: "Cập nhật lúc",
    }
    can_create = True
    can_edit = True
    can_delete = True
    can_export = True
    page_size = 30
