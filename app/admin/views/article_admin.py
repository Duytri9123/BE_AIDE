from sqladmin import ModelView
from app.models.article import Article
from markupsafe import Markup
from app.services.article_content import normalize_article_html


def render_article_html(model, _attribute):
    return Markup(normalize_article_html(model.content_html))


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

    async def on_model_change(self, data, model, is_created, request):
        if "content_html" in data:
            data["content_html"] = normalize_article_html(data["content_html"])
