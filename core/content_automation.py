"""Deterministic content classification and location distribution helpers.

The rules work without an AI provider, so admin saves remain reliable even if
TokenMix is unavailable. TokenMix can still enrich the generated content later.
"""

from __future__ import annotations

import hashlib
import re

from django.db.models import Count
from django.utils.text import slugify


BLOG_TAXONOMY = (
    ("النخيل والأشجار", "palms-trees", ("نخيل", "نخلة", "أشجار", "شجرة", "تشجير", "زراعة")),
    ("تصميم الحدائق", "garden-design", ("تصميم", "حديقة", "حدائق", "جلسات", "ممرات")),
    ("الري والصيانة", "irrigation-maintenance", ("ري", "صيانة", "تسميد", "تقليم", "مكافحة")),
    ("اللاندسكيب", "landscape", ("لاندسكيب", "هاردسكيب", "ثيل", "عشب", "مسطحات")),
    ("المظلات والشبوك", "shades-fencing", ("مظلات", "مظلة", "شبوك", "سياج", "برجولات")),
    ("دليل وتكاليف", "guides-costs", ("تكلفة", "سعر", "أسعار", "دليل", "اختيار", "أفضل")),
)

SERVICE_TAXONOMY = (
    ("تصميم وتنفيذ الحدائق", "garden-design-build", ("تصميم", "حدائق", "حديقة", "جلسات", "ممرات")),
    ("النخيل والتشجير", "palms-planting", ("نخيل", "أشجار", "تشجير", "زراعة", "توريد")),
    ("الري والصيانة", "irrigation-care", ("ري", "صيانة", "تقليم", "تسميد", "مكافحة")),
    ("اللاندسكيب الصلب", "hardscape", ("لاندسكيب", "هاردسكيب", "بلاط", "حجر", "أرضيات")),
    ("المظلات والشبوك", "shades-fencing", ("مظلات", "مظلة", "شبوك", "سياج", "برجولات")),
)

STOP_WORDS = {
    "في", "من", "إلى", "على", "عن", "مع", "هذا", "هذه", "ذلك", "التي", "الذي", "خدمة",
    "خدمات", "شركة", "تنفيذ", "أفضل", "داخل", "جميع", "السعودية", "المملكة", "مشروع",
}


def normalized_text(*values: str) -> str:
    return " ".join(str(value or "") for value in values).lower()


def stable_unicode_slug(value: str, prefix: str = "item") -> str:
    clean = slugify(value or "", allow_unicode=True)
    if clean:
        return clean[:130]
    digest = hashlib.sha1((value or prefix).encode("utf-8")).hexdigest()[:12]
    return f"{prefix}-{digest}"


def infer_taxonomy(text: str, taxonomy, default_name: str, default_slug: str):
    normalized = normalized_text(text)
    best = None
    best_score = 0
    for name, slug, keywords in taxonomy:
        score = sum(normalized.count(keyword.lower()) for keyword in keywords)
        if score > best_score:
            best = (name, slug)
            best_score = score
    return best or (default_name, default_slug)


def choose_city(related_name: str):
    from .models import City

    count_name = "_content_count"
    return (
        City.objects.filter(is_active=True, is_system=True)
        .annotate(**{count_name: Count(related_name)})
        .order_by(count_name, "name")
        .first()
    )


def choose_district(city, related_name: str):
    if not city:
        return None
    count_name = "_content_count"
    return (
        city.districts.filter(is_active=True)
        .annotate(**{count_name: Count(related_name)})
        .order_by(count_name, "sort_order", "name")
        .first()
    )


def _candidate_tag_names(*values: str, city=None, district=None, limit: int = 8):
    raw_text = normalized_text(*values)
    names = []

    for _, _, keywords in BLOG_TAXONOMY + SERVICE_TAXONOMY:
        for keyword in keywords:
            if keyword in raw_text and keyword not in names:
                names.append(keyword)

    for token in re.findall(r"[\u0600-\u06FF]{3,}", raw_text):
        token = token.strip("،.؛:()[]{}")
        if token and token not in STOP_WORDS and token not in names:
            names.append(token)
        if len(names) >= limit:
            break

    if city and city.name not in names:
        names.append(city.name)
    if district and district.name not in names:
        names.append(district.name)
    return names[:limit]


def classify_blog_post(post):
    from .models import BlogCategory, BlogTag

    if post.auto_classify and not post.category_id:
        name, slug = infer_taxonomy(
            normalized_text(post.title, post.excerpt, post.content, post.meta_keywords),
            BLOG_TAXONOMY,
            "نصائح اللاندسكيب",
            "landscape-tips",
        )
        post.category, _ = BlogCategory.objects.get_or_create(
            slug=slug,
            defaults={
                "name": name,
                "description": f"مقالات وأدلة عملية حول {name}.",
                "meta_title": f"{name} | مقالات وأدلة",
                "meta_description": f"مقالات عملية ونصائح متخصصة عن {name} في السعودية.",
            },
        )

    if post.auto_distribute and not post.city_id:
        post.city = choose_city("blog_posts")
    if post.city_id and not post.district_id:
        post.district = choose_district(post.city, "blog_posts")


def apply_blog_tags(post):
    from .models import BlogTag

    if not post.auto_classify or post.tags.exists():
        return
    tags = []
    for name in _candidate_tag_names(
        post.title,
        post.excerpt,
        post.content,
        post.meta_keywords,
        city=post.city,
        district=post.district,
    ):
        tag, _ = BlogTag.objects.get_or_create(
            slug=stable_unicode_slug(name, "tag"),
            defaults={
                "name": name,
                "meta_title": f"{name} | مقالات متخصصة",
                "meta_description": f"مقالات وخدمات مرتبطة بموضوع {name}.",
            },
        )
        tags.append(tag)
    if tags:
        post.tags.add(*tags)


def classify_service(service):
    from .models import ServiceCategory

    if service.auto_classify and not service.category_id:
        name, slug = infer_taxonomy(
            normalized_text(service.title, service.short_title, service.description, service.meta_keywords),
            SERVICE_TAXONOMY,
            "خدمات اللاندسكيب",
            "landscape-services",
        )
        service.category, _ = ServiceCategory.objects.get_or_create(
            slug=slug,
            defaults={
                "name": name,
                "description": f"خدمات متخصصة ضمن {name}.",
                "meta_title": f"{name} | خدماتنا",
                "meta_description": f"استعرض خدمات {name} المتاحة في المدن والأحياء التي نخدمها.",
            },
        )

    if service.auto_distribute and not service.primary_city_id:
        service.primary_city = choose_city("primary_services")
    if service.primary_city_id and not service.primary_district_id:
        service.primary_district = choose_district(service.primary_city, "primary_services")


def apply_service_tags(service):
    from .models import ServiceTag

    if not service.auto_classify or service.tags.exists():
        return
    tags = []
    for name in _candidate_tag_names(
        service.title,
        service.short_title,
        service.description,
        service.meta_keywords,
        city=service.primary_city,
        district=service.primary_district,
    ):
        tag, _ = ServiceTag.objects.get_or_create(
            slug=stable_unicode_slug(name, "service-tag"),
            defaults={
                "name": name,
                "meta_title": f"{name} | خدمات",
                "meta_description": f"خدمات مرتبطة بموضوع {name}.",
            },
        )
        tags.append(tag)
    if tags:
        service.tags.add(*tags)


def classify_project(project):
    if project.city_id and not project.district_id:
        project.district = choose_district(project.city, "projects")
