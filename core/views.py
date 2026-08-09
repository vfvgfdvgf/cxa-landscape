from pathlib import Path
import hashlib
from urllib.parse import urlencode, urljoin
from datetime import timezone as datetime_timezone

from django.conf import settings
from django.db import models
from django.core.cache import cache
from django.core.paginator import Paginator
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.templatetags.static import static
from django.urls import reverse
from django.db.utils import OperationalError, ProgrammingError
from django.utils.encoding import iri_to_uri
from django.utils import timezone
from django.utils.html import strip_tags
from django.views.decorators.cache import cache_control
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_GET, require_POST
from xml.sax.saxutils import escape

from .data import (
    BLOG_POSTS,
    CITIES,
    PHONE_NUMBER,
    SERVICE_SLUGS,
    SITE_NAME,
    TESTIMONIALS,
    build_quote_message,
    get_city,
    get_post,
    get_service,
)
from .context_processors import build_theme_css
from .forms import BlogCommentForm
from .html_utils import safe_json_dumps
from .image_utils import is_responsive_variant_name
from .project_media import CATEGORY_IMAGES, HERO_DESKTOP, HERO_MOBILE, IMAGE_GROUPS, IMAGE_METADATA, PROJECT_MEDIA
from .request_utils import rate_limit, request_fingerprint, safe_page_url, valid_phone
from .models import ConversionEvent, Lead, LibraryImage, PageMedia, SiteSettings
from .models import BlogCategory, BlogComment, BlogPost, BlogTag, City as CityModel, District, CityServicePage, Page, Project, Service as ServiceModel, Testimonial
from .text_utils import fix_arabic_text, fix_payload_text


UI_TEXT = {
    "ar": {
        "home": "الرئيسية",
        "about": "من نحن",
        "services": "الخدمات",
        "projects": "المشاريع",
        "cities": "المدن",
        "blog": "المدونة",
        "contact": "اتصل بنا",
        "quote": "اطلب عرض سعر",
        "call_now": "اتصل الآن",
        "whatsapp": "واتساب",
        "hero_badge": "نخيل ولاندسكيب ضمن مدن التغطية المنشورة",
    },
}

STATIC_IMAGE_FILES = tuple(item["filename"] for item in PROJECT_MEDIA)

SERVICE_CATEGORY_MAP = {
    "shades": "shades",
    "fencing": "fencing",
    "palm-trees": "palm",
    "traditional": "traditional",
}

def detect_language(request):
    return "ar"


def safe_static(path):
    try:
        return iri_to_uri(static(path))
    except Exception:
        return iri_to_uri(f"/static/{str(path).lstrip('/')}")


def build_seo(
    title,
    description,
    request,
    image="",
    keywords="",
    robots="index, follow, max-image-preview:large",
    page_type="WebPage",
    published_at=None,
    modified_at=None,
    canonical_query_keys=(),
):
    site_base = getattr(settings, "SITE_URL", "").rstrip("/") or request.build_absolute_uri("/").rstrip("/")
    canonical = f"{site_base}{request.path}"
    canonical_query = {
        key: request.GET.get(key)
        for key in canonical_query_keys
        if request.GET.get(key) not in (None, "", "1")
    }
    if canonical_query:
        canonical = f"{canonical}?{urlencode(canonical_query)}"
    absolute_image = urljoin(f"{site_base}/", image.lstrip("/")) if image else ""
    schemas = [
        {
            "@context": "https://schema.org",
            "@type": page_type,
            "@id": f"{canonical}#webpage",
            "name": title,
            "headline": title,
            "description": description,
            "url": canonical,
            "inLanguage": "ar-SA",
            **({"image": absolute_image} if absolute_image else {}),
        }
    ]
    if request.path != "/":
        schemas.append(
            {
                "@context": "https://schema.org",
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "الرئيسية", "item": f"{site_base}/"},
                    {"@type": "ListItem", "position": 2, "name": title.split("|")[0].strip(), "item": canonical},
                ],
            }
        )
    if page_type in {"Article", "BlogPosting"}:
        article = schemas[0]
        article["@type"] = "BlogPosting"
        article["mainEntityOfPage"] = {"@type": "WebPage", "@id": canonical}
        article["author"] = {"@type": "Organization", "name": SITE_NAME, "url": f"{site_base}/"}
        article["publisher"] = {"@type": "Organization", "name": SITE_NAME, "url": f"{site_base}/"}
        if published_at:
            article["datePublished"] = published_at.isoformat()
        if modified_at:
            article["dateModified"] = modified_at.isoformat()
    return {
        "title": title,
        "description": description,
        "canonical": canonical,
        "image": absolute_image,
        "keywords": keywords,
        "robots": robots,
        "og_type": "article" if page_type in {"Article", "BlogPosting"} else "website",
        "schema_json": safe_json_dumps(schemas),
    }


def add_pagination_seo(seo, request, page_obj):
    if not page_obj or page_obj.paginator.num_pages <= 1:
        return seo
    site_base = getattr(settings, "SITE_URL", "").rstrip("/") or request.build_absolute_uri("/").rstrip("/")
    base_url = f"{site_base}{request.path}"
    if page_obj.has_previous():
        previous_page = page_obj.previous_page_number()
        seo["prev_url"] = base_url if previous_page == 1 else f"{base_url}?{urlencode({'page': previous_page})}"
    if page_obj.has_next():
        seo["next_url"] = f"{base_url}?{urlencode({'page': page_obj.next_page_number()})}"
    return seo


def get_service_highlights(settings_obj):
    if settings_obj and settings_obj.service_highlights_list:
        return [fix_arabic_text(item) for item in settings_obj.service_highlights_list]
    return ["لاندسكيب", "تصميم حدائق", "أشجار ونخيل", "شبوك", "مظلات"]


def highlights_phrase(settings_obj, limit=4):
    return "، ".join(get_service_highlights(settings_obj)[:limit])


def build_base_context(request):
    language = detect_language(request)
    settings_obj = None
    try:
        settings_obj = SiteSettings.load()
    except (OperationalError, ProgrammingError):
        settings_obj = None

    location_options = get_location_options()
    return fix_payload_text({
        "lang_code": language,
        "is_rtl": True,
        "ui": UI_TEXT[language],
        "services_map": SERVICE_SLUGS,
        "cities_data": CITIES,
        "settings_obj": settings_obj,
        "theme_css_vars": build_theme_css(settings_obj=settings_obj),
        "location_options": location_options,
        "location_options_json": safe_json_dumps(location_options),
    })


def render_clean(request, template_name, context, **kwargs):
    return render(request, template_name, fix_payload_text(context), **kwargs)



def get_library_images(start=0, count=None):
    files = STATIC_IMAGE_FILES[start:] if count is None else STATIC_IMAGE_FILES[start : start + count]
    return [
        build_library_image(
            filename,
            title=f"صورة مشروع {index + 1}",
            alt=f"صورة مشروع {index + 1}",
        )
        for index, filename in enumerate(files, start=start)
    ]



def with_fallback_media(items, fallback_items):
    return items or fallback_items


def serialize_library_item(item):
    if isinstance(item, dict):
        return {
            "filename": item.get("source_name", ""),
            "image_url": item.get("image_url", ""),
            "title": fix_arabic_text(item.get("title", "")),
            "display_alt": fix_arabic_text(item.get("display_alt") or item.get("alt_text", "") or item.get("title", "")),
            "category": item.get("category", "general"),
        }
    return {
        "filename": item.source_name,
        "image_url": item.image_url,
        "title": fix_arabic_text(item.title),
        "display_alt": fix_arabic_text(item.display_alt),
        "category": item.category,
    }


def default_usage_group_for(filename):
    for usage_group, filenames in IMAGE_GROUPS.items():
        if filename in filenames:
            return usage_group
    return "home_gallery"


def default_category_for(filename):
    metadata = IMAGE_METADATA.get(filename, {})
    return metadata.get("category", "general")


def default_title_for(filename):
    return "صورة من مشاريع اللاندسكيب"


def default_alt_for(filename):
    return "صورة تنسيق حدائق ولاندسكيب"


def get_library_records():
    cached_records = cache.get("library:records")
    if cached_records is not None:
        return cached_records

    try:
        records = []
        for item in (
            LibraryImage.objects.filter(is_active=True)
            .defer("image_data")
            .only(
                "id", "source_name", "title", "alt_text", "category", "usage_group",
                "image", "image_stored", "image_filename", "external_url", "sort_order",
            )
        ):
            records.append(
                {
                    "id": item.pk,
                    "source_name": item.source_name,
                    "title": item.title,
                    "alt_text": item.alt_text,
                    "display_alt": item.display_alt,
                    "category": item.category,
                    "usage_group": item.usage_group,
                    "sort_order": item.sort_order,
                    "image_url": item.image_url,
                }
            )
        cache.set("library:records", records, 300)
        return records
    except (OperationalError, ProgrammingError):
        return []


def build_library_image(filename, title="", alt=""):
    records = get_library_records()
    matched = next((item for item in records if item.get("source_name") == filename), None)
    if matched:
        return serialize_library_item(matched)
    return {
        "filename": filename,
        "image_url": safe_static(filename),
        "title": fix_arabic_text(title or "صورة من مشاريع اللاندسكيب"),
        "display_alt": fix_arabic_text(alt or title or "صورة تنسيق حدائق ولاندسكيب"),
        "category": default_category_for(filename),
    }


def get_page_image_block(page_slug):
    records = [
        serialize_library_item(item)
        for item in get_library_records()
        if item.get("usage_group") == page_slug and item.get("source_name") in STATIC_IMAGE_FILES
    ]
    if records:
        return records
    filenames = IMAGE_GROUPS.get(page_slug)
    if filenames:
        return [build_library_image(filename) for filename in filenames]
    return get_library_images(0, 4)


def get_images_by_category(category, limit=4):
    records = [
        serialize_library_item(item)
        for item in get_library_records()
        if item.get("category") == category and item.get("source_name") in STATIC_IMAGE_FILES
    ]
    if records:
        return records[:limit]
    matches = CATEGORY_IMAGES.get(category) or CATEGORY_IMAGES["general"]
    return [build_library_image(filename) for filename in matches[:limit]]


def resolve_service_category(service_slug, service_name="", category_name=""):
    text = " ".join([service_slug or "", service_name or "", category_name or ""]).lower()
    if any(term in text for term in ("شبك", "سياج", "تسوير", "بواب", "fence", "mesh")):
        return "fencing"
    if any(term in text for term in ("مظلة", "برجول", "جلسات", "pergola", "shade")):
        return "shades"
    if any(term in text for term in ("ري", "صيانة", "تقليم", "تسميد", "تربة", "آفات", "تصريف", "irrigation", "maintenance")):
        return "traditional"
    return SERVICE_CATEGORY_MAP.get(service_slug, "palm")


def assign_service_fallback_images(services):
    output = []
    used_images = set()
    global_candidates = [build_library_image(item["filename"]) for item in PROJECT_MEDIA]
    for index, service in enumerate(services):
        updated = dict(service)
        service_category = resolve_service_category(
            updated.get("slug", ""),
            updated.get("name", ""),
            updated.get("category", ""),
        )
        category_candidates = get_images_by_category(service_category, 100)
        candidates = category_candidates + global_candidates
        current_image = updated.get("image") or ""
        if current_image and current_image not in used_images:
            selected = current_image
        else:
            selected = ""
            if candidates:
                start = index % len(candidates)
                ordered = candidates[start:] + candidates[:start]
                for item in ordered:
                    candidate = item.get("image_url", "")
                    if candidate and candidate not in used_images:
                        selected = candidate
                        break
                if not selected:
                    selected = candidates[index % len(candidates)].get("image_url", "")
        updated["image"] = selected
        if selected:
            used_images.add(selected)
        output.append(updated)
    return output


def assign_project_fallback_images(projects):
    fallback_images = get_page_image_block("portfolio")
    output = []
    for index, project in enumerate(projects):
        updated = dict(project)
        if not updated.get("image_url") and index < len(fallback_images):
            updated["image_url"] = fallback_images[index]["image_url"]
        output.append(updated)
    return output


def service_cards():
    try:
        services = list(ServiceModel.objects.filter(is_visible=True).select_related("category", "primary_city", "primary_district").prefetch_related("cities", "tags"))
        if services:
            return assign_service_fallback_images([
                {
                    "slug": service.slug,
                    "name": fix_arabic_text(service.title),
                    "short_name": fix_arabic_text(service.short_title or service.title),
                    "description": fix_arabic_text(service.description),
                    "benefits": [fix_arabic_text(item) for item in service.benefits_list],
                    "image": service.resolved_image,
                    "category": fix_arabic_text(service.category.name) if service.category else "",
                    "tags": [fix_arabic_text(tag.name) for tag in service.tags.all()[:5]],
                    "primary_city": fix_arabic_text(service.primary_city.name) if service.primary_city else "",
                    "primary_district": fix_arabic_text(service.primary_district.name) if service.primary_district else "",
                }
                for service in services
            ])
    except (OperationalError, ProgrammingError):
        pass
    return assign_service_fallback_images([{"slug": slug, **service} for slug, service in SERVICE_SLUGS.items()])


def get_page_media(page, section=None):
    try:
        queryset = PageMedia.objects.filter(page=page, is_active=True)
        if section:
            queryset = queryset.filter(section=section)
        return list(queryset)
    except (OperationalError, ProgrammingError):
        return []


def get_managed_page(page_slug=None, template_key=None):
    try:
        queryset = Page.objects.filter(is_visible=True)
        if page_slug:
            return queryset.filter(models.Q(custom_url=page_slug) | models.Q(slug=page_slug)).first()
        if template_key:
            return queryset.filter(template_key=template_key).first()
    except Exception:
        return None
    return None


def get_cities_data():
    try:
        cities = list(
            CityModel.objects.filter(is_active=True, is_system=True)
            .annotate(active_district_count=models.Count("districts", filter=models.Q(districts__is_active=True)))
            .order_by("name")
        )
        if cities:
            return [
                {
                    "slug": city.slug,
                    "name": fix_arabic_text(city.name),
                    "region": fix_arabic_text(city.region),
                    "description": fix_arabic_text(city.short_description or city.content),
                    "content": fix_arabic_text(city.content),
                    "hero_title": fix_arabic_text(city.hero_title),
                    "district_count": city.active_district_count,
                }
                for city in cities
            ]
    except (OperationalError, ProgrammingError):
        pass
    return CITIES


def get_projects_data():
    try:
        projects = list(Project.objects.filter(is_visible=True).select_related("city", "district"))
        if projects:
            return assign_project_fallback_images([
                {
                    "title": fix_arabic_text(project.title),
                    "category": fix_arabic_text(project.get_category_display()),
                    "image_url": project.image_url,
                    "description": fix_arabic_text(project.description),
                    "city": fix_arabic_text(project.city.name) if project.city else "",
                    "district": fix_arabic_text(project.district.name) if project.district else "",
                }
                for project in projects
            ])
    except (OperationalError, ProgrammingError):
        pass
    return [
        {
            "title": item["title"],
            "category": item["category"],
            "image_url": safe_static(item["filename"]),
            "description": item["description"],
            "city": "",
            "district": "",
        }
        for item in PROJECT_MEDIA
    ]


def get_testimonials_data():
    try:
        items = list(Testimonial.objects.filter(is_visible=True))
        if items:
            return [
                {
                    "name": fix_arabic_text(f"{item.name} - {item.city_name}".strip(" -")),
                    "quote": fix_arabic_text(item.review),
                    "rating": item.rating,
                }
                for item in items
            ]
    except (OperationalError, ProgrammingError):
        pass
    return TESTIMONIALS


def get_posts_data():
    try:
        posts = list(
            BlogPost.objects.filter(status="published")
            .filter(models.Q(publish_at__lte=timezone.now()) | models.Q(publish_at__isnull=True))
            .select_related("category")
            .prefetch_related("tags")
        )
        if posts:
            return posts
    except (OperationalError, ProgrammingError):
        pass
    return [
        {
            **post,
            "image_url": safe_static(PROJECT_MEDIA[index % len(PROJECT_MEDIA)]["filename"]),
        }
        for index, post in enumerate(BLOG_POSTS)
    ]


def get_blog_sidebar_data():
    cache_key = "blog-sidebar-data"
    cached = cache.get(cache_key)
    if cached:
        return cached

    try:
        categories = list(BlogCategory.objects.all())
        tags = list(BlogTag.objects.all()[:20])
        popular_posts = list(BlogPost.objects.filter(status="published").filter(models.Q(publish_at__lte=timezone.now()) | models.Q(publish_at__isnull=True)).order_by("-view_count", "-publish_at")[:5])
    except (OperationalError, ProgrammingError):
        categories, tags, popular_posts = [], [], []

    payload = {"categories": categories, "tags": tags, "popular_posts": popular_posts}
    cache.set(cache_key, payload, 300)
    return payload


def get_location_options():
    cache_key = "site:location_options"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    try:
        cities = CityModel.objects.filter(is_active=True, is_system=True).prefetch_related(
            models.Prefetch("districts", queryset=District.objects.filter(is_active=True).order_by("sort_order", "name"))
        ).order_by("name")
        options = [
            {
                "id": city.pk,
                "slug": city.slug,
                "name": fix_arabic_text(city.name),
                "districts": [
                    {"id": district.pk, "name": fix_arabic_text(district.name)}
                    for district in city.districts.all()
                ],
            }
            for city in cities
        ]
    except (OperationalError, ProgrammingError):
        options = [{"id": None, "slug": city["slug"], "name": city["name"], "districts": []} for city in CITIES]
    cache.set(cache_key, options, 600)
    return options


@require_GET
def location_options_json(request):
    return JsonResponse(get_location_options(), safe=False)


def home(request):
    context = build_base_context(request)
    settings_obj = context.get("settings_obj")
    site_name = fix_arabic_text(settings_obj.site_name) if settings_obj else SITE_NAME
    highlights_text = highlights_phrase(settings_obj)
    managed_page = get_managed_page(template_key="home")
    services = service_cards()
    cities = get_cities_data()
    projects = get_projects_data()
    latest_posts = get_posts_data()[:6]
    context.update(
        {
            "seo": build_seo(
                f"{site_name} | {(settings_obj.homepage_meta_title if settings_obj else 'لاندسكيب وتنسيق حدائق في السعودية')}",
                settings_obj.homepage_meta_description if settings_obj else f"نخيل نجد لخدمات {highlights_text} ضمن المدن والأحياء المنشورة في الموقع.",
                request,
                image=settings_obj.default_og_image_resolved if settings_obj else "",
                keywords=settings_obj.seo_default_keywords if settings_obj else "",
            ),
            "hero_title": fix_arabic_text(managed_page.hero_title) if managed_page and managed_page.hero_title else "توريد وزراعة النخيل وتنفيذ الحدائق والري والشبوك",
            "hero_text": fix_arabic_text(managed_page.intro_text) if managed_page and managed_page.intro_text else "نورّد ونزرع النخيل العربي والواشنطني والملوكي، وننفذ اللاندسكيب وشبكات الري والشبوك مع تغطية المدن والأحياء.",
            "hero_background": settings_obj.homepage_hero_background_resolved if settings_obj else "",
            "services": services,
            "portfolio_items": projects,
            "testimonials": get_testimonials_data(),
            "featured_cities": cities[:12],
            "hero_media": get_page_image_block("home_hero"),
            "hero_desktop": build_library_image(HERO_DESKTOP, title="توريد وزراعة النخيل", alt="مشروع نخيل نجد"),
            "hero_mobile": build_library_image(HERO_MOBILE, title="توريد وزراعة النخيل", alt="مشروع نخيل نجد"),
            "home_gallery": with_fallback_media(get_page_media("home", "gallery"), get_page_image_block("home_gallery")),
            "home_banners": get_page_image_block("home_banners"),
            "latest_posts": latest_posts,
            "stats": [
                {"value": str(len(cities)), "label": "مدينة ثابتة بالتغطية"},
                {"value": str(sum(item.get("district_count", 0) for item in cities)), "label": "حيًا ضمن صفحات التغطية"},
                {"value": str(len(services)), "label": "خدمة منظمة قابلة للاختيار"},
            ],
        }
    )
    return render_clean(request, "pages/home.html", context)


def managed_page(request, page_slug):
    page = get_managed_page(page_slug=page_slug)
    if not page:
        raise Http404("Page not found")
    context = build_base_context(request)
    context.update(
        {
            "seo": build_seo(
                page.meta_title or f"{page.title} | {context.get('settings_obj').site_name if context.get('settings_obj') else SITE_NAME}",
                page.meta_description or page.intro_text,
                request,
            ),
            "page_obj": page,
            "page_images": with_fallback_media(
                get_page_media(page.template_key if page.template_key != "custom" else "home"),
                get_page_image_block(page.template_key if page.template_key != "custom" else "about"),
            ),
        }
    )
    return render_clean(request, "pages/managed_page.html", context)


def about(request):
    context = build_base_context(request)
    context["seo"] = build_seo(
        f"من نحن | {context.get('settings_obj').site_name if context.get('settings_obj') else SITE_NAME}",
        "تعرف على خبرة شركتنا السعودية في تصميم الحدائق وتنفيذ اللاندسكيب وزراعة الأشجار والنخيل.",
        request,
    )
    context["page_images"] = with_fallback_media(get_page_media("about"), get_page_image_block("about"))
    return render_clean(request, "pages/about.html", context)


def services(request):
    context = build_base_context(request)
    context.update(
        {
            "seo": build_seo(
                f"خدماتنا | {context.get('settings_obj').site_name if context.get('settings_obj') else SITE_NAME}",
                "استعرض خدمات تصميم الحدائق وتنفيذ اللاندسكيب وزراعة الأشجار والنخيل وأنظمة الري في السعودية.",
                request,
            ),
            "services": service_cards(),
            "page_images": with_fallback_media(get_page_media("services"), get_page_image_block("services")),
        }
    )
    return render_clean(request, "pages/services.html", context)


def service_detail(request, service_slug):
    context = build_base_context(request)
    settings_obj = context.get("settings_obj")
    service_obj = None
    try:
        service_obj = ServiceModel.objects.filter(slug=service_slug, is_visible=True).first()
    except (OperationalError, ProgrammingError):
        service_obj = None

    if service_obj:
        service = {
            "slug": service_obj.slug,
            "name": fix_arabic_text(service_obj.title),
            "short_name": fix_arabic_text(service_obj.short_title or service_obj.title),
            "keyword": fix_arabic_text(service_obj.short_title or service_obj.title),
            "description": fix_arabic_text(service_obj.description),
            "benefits": [fix_arabic_text(item) for item in service_obj.benefits_list],
            "image": service_obj.resolved_image,
            "meta_title": fix_arabic_text(service_obj.meta_title),
            "meta_description": fix_arabic_text(service_obj.meta_description),
            "meta_keywords": fix_arabic_text(service_obj.meta_keywords),
            "category": fix_arabic_text(service_obj.category.name) if service_obj.category else "",
            "tags": [fix_arabic_text(tag.name) for tag in service_obj.tags.all()[:8]],
            "primary_city": fix_arabic_text(service_obj.primary_city.name) if service_obj.primary_city else "",
            "primary_district": fix_arabic_text(service_obj.primary_district.name) if service_obj.primary_district else "",
        }
        updated_at = service_obj.updated_at
    else:
        raw_service = SERVICE_SLUGS.get(service_slug)
        if not raw_service:
            raise Http404("Service not found")
        service = {
            "slug": service_slug,
            "name": fix_arabic_text(raw_service["name"]),
            "short_name": fix_arabic_text(raw_service.get("short_name", raw_service["name"])),
            "keyword": fix_arabic_text(raw_service.get("keyword", raw_service["name"])),
            "description": fix_arabic_text(raw_service.get("description", "")),
            "benefits": [fix_arabic_text(item) for item in raw_service.get("benefits", [])],
            "image": "",
            "meta_title": "",
            "meta_description": "",
            "meta_keywords": "",
        }
        updated_at = timezone.now()

    cities_data = get_cities_data()
    city_links = []
    for city in cities_data:
        try:
            url = reverse("city_service_detail", kwargs={"city_slug": city["slug"], "service_slug": service["slug"]})
        except Exception:
            url = reverse("city_detail", kwargs={"city_slug": city["slug"]})
        city_links.append({"name": city["name"], "url": url})

    service_text = f"{service['name']} في السعودية"
    context.update(
        {
            "seo": build_seo(
                service["meta_title"] or f"{service_text} | تفاصيل التوريد والتنفيذ",
                service["meta_description"]
                or f"خدمة {service_text} ضمن مدن التغطية المنشورة، مع تحديد نطاق التوريد والتنفيذ والري والصيانة حسب الموقع.",
                request,
                image=service.get("image", ""),
                keywords=service["meta_keywords"]
                or f"{service['name']}, توريد نخيل, تكريب نخيل, تشذيب نخيل, لاندسكيب, تنسيق حدائق, شبوك, مظلات",
            ),
            "service": service,
            "cities": city_links,
            "page_images": with_fallback_media(get_page_media("services"), get_images_by_category(resolve_service_category(service["slug"]), 6)),
            "updated_at": updated_at,
        }
    )
    return render_clean(request, "pages/service_detail.html", context)


def portfolio(request):
    context = build_base_context(request)
    page_obj = Paginator(get_projects_data(), 12).get_page(request.GET.get("page"))
    seo = build_seo(
        f"المشاريع والأعمال | {context.get('settings_obj').site_name if context.get('settings_obj') else SITE_NAME}",
        "معرض أعمال لمشاريع النخيل والشبوك واللاندسكيب المرتبطة بمدن التغطية وأحيائها.",
        request,
        canonical_query_keys=("page",),
    )
    add_pagination_seo(seo, request, page_obj)
    context.update(
        {
            "seo": seo,
            "portfolio_items": list(page_obj.object_list),
            "page_obj": page_obj,
            "page_images": with_fallback_media(get_page_media("portfolio"), get_page_image_block("portfolio")),
        }
    )
    return render_clean(request, "pages/portfolio.html", context)


def cities(request):
    context = build_base_context(request)
    city_data = get_cities_data()
    context["seo"] = build_seo(
        f"المدن التي نخدمها | {context.get('settings_obj').site_name if context.get('settings_obj') else SITE_NAME}",
        "صفحات محلية لمدن التغطية المنشورة وأحيائها، تشمل الخدمات والمقالات والمشاريع المرتبطة بكل موقع.",
        request,
    )
    context["page_images"] = with_fallback_media(get_page_media("cities"), get_page_image_block("cities"))
    context["cities_data"] = city_data
    return render_clean(request, "pages/cities.html", context)


def _published_blog_queryset():
    return (
        BlogPost.objects.filter(status="published")
        .filter(models.Q(publish_at__lte=timezone.now()) | models.Q(publish_at__isnull=True))
        .select_related("category")
        .prefetch_related("tags")
        .order_by("-is_featured", "-publish_at", "-created_at")
    )


def _paginate_blog_queryset(request, queryset):
    return Paginator(queryset, 12).get_page(request.GET.get("page"))


def blog_index(request):
    context = build_base_context(request)
    settings_obj = context.get("settings_obj")
    query = request.GET.get("q", "").strip()[:120]
    category_filter = request.GET.get("category", "").strip()[:140]
    page_obj = None

    try:
        queryset = _published_blog_queryset()
        if query:
            queryset = queryset.filter(
                models.Q(title__icontains=query)
                | models.Q(excerpt__icontains=query)
                | models.Q(content__icontains=query)
            )
        if category_filter:
            queryset = queryset.filter(category__slug=category_filter)
        page_obj = _paginate_blog_queryset(request, queryset)
        posts = list(page_obj.object_list)
    except (OperationalError, ProgrammingError):
        posts = get_posts_data()
        if query:
            posts = [post for post in posts if query.lower() in (post.get("title", "") if isinstance(post, dict) else post.title).lower()]

    seo = build_seo(
        f"مدونة الأعمال والخدمات | {context.get('settings_obj').site_name if context.get('settings_obj') else SITE_NAME}",
        "مقالات عربية عملية عن تصميم الحدائق وتكلفة اللاندسكيب وأنواع الأشجار والنخيل وأنظمة الري في السعودية.",
        request,
        robots="noindex, follow" if (query or category_filter) else "index, follow, max-image-preview:large",
        canonical_query_keys=() if (query or category_filter) else ("page",),
    )
    if not query and not category_filter:
        seo = add_pagination_seo(seo, request, page_obj)
    featured_posts = [post for post in posts if getattr(post, "is_featured", False)][:3] if not query and not category_filter and (not page_obj or page_obj.number == 1) else []
    sidebar = get_blog_sidebar_data()
    context.update(
        {
            "seo": seo,
            "posts": posts,
            "page_obj": page_obj,
            "featured_posts": featured_posts,
            "search_query": query,
            "active_category": category_filter,
            "categories": sidebar["categories"],
            "tags_cloud": sidebar["tags"],
            "popular_posts": sidebar["popular_posts"],
            "blog_hero_background": settings_obj.blog_hero_background_resolved if settings_obj else "",
            "page_images": with_fallback_media(get_page_media("blog"), get_page_image_block("blog")),
        }
    )
    return render_clean(request, "blog/index.html", context)


def blog_category(request, category_slug):
    category = BlogCategory.objects.filter(slug=category_slug).first()
    if not category:
        raise Http404("Category not found")
    page_obj = _paginate_blog_queryset(request, _published_blog_queryset().filter(category=category))
    context = build_base_context(request)
    settings_obj = context.get("settings_obj")
    sidebar = get_blog_sidebar_data()
    seo = build_seo(
        category.meta_title or f"مقالات {category.name} | {context.get('settings_obj').site_name if context.get('settings_obj') else SITE_NAME}",
        category.meta_description or category.description,
        request,
        canonical_query_keys=("page",),
    )
    context.update(
        {
            "seo": add_pagination_seo(seo, request, page_obj),
            "posts": list(page_obj.object_list),
            "page_obj": page_obj,
            "featured_posts": [],
            "search_query": "",
            "active_category": category.slug,
            "current_taxonomy_title": f"تصنيف: {category.name}",
            "categories": sidebar["categories"],
            "tags_cloud": sidebar["tags"],
            "popular_posts": sidebar["popular_posts"],
            "blog_hero_background": settings_obj.blog_hero_background_resolved if settings_obj else "",
            "page_images": with_fallback_media(get_page_media("blog"), get_page_image_block("blog")),
        }
    )
    return render_clean(request, "blog/index.html", context)


def blog_tag(request, tag_slug):
    tag = BlogTag.objects.filter(slug=tag_slug).first()
    if not tag:
        raise Http404("Tag not found")
    page_obj = _paginate_blog_queryset(request, _published_blog_queryset().filter(tags=tag).distinct())
    context = build_base_context(request)
    settings_obj = context.get("settings_obj")
    sidebar = get_blog_sidebar_data()
    seo = build_seo(
        tag.meta_title or f"وسم: {tag.name} | {context.get('settings_obj').site_name if context.get('settings_obj') else SITE_NAME}",
        tag.meta_description or f"مقالات مرتبطة بوسم {tag.name}",
        request,
        canonical_query_keys=("page",),
    )
    context.update(
        {
            "seo": add_pagination_seo(seo, request, page_obj),
            "posts": list(page_obj.object_list),
            "page_obj": page_obj,
            "featured_posts": [],
            "search_query": "",
            "active_category": "",
            "current_taxonomy_title": f"وسم: {tag.name}",
            "categories": sidebar["categories"],
            "tags_cloud": sidebar["tags"],
            "popular_posts": sidebar["popular_posts"],
            "blog_hero_background": settings_obj.blog_hero_background_resolved if settings_obj else "",
            "page_images": with_fallback_media(get_page_media("blog"), get_page_image_block("blog")),
        }
    )
    return render_clean(request, "blog/index.html", context)

def blog_detail(request, post_slug):
    try:
        post = (
            BlogPost.objects.filter(status="published", slug=post_slug)
            .filter(models.Q(publish_at__lte=timezone.now()) | models.Q(publish_at__isnull=True))
            .select_related("category", "city", "district")
            .prefetch_related("tags", "comments")
            .first()
        )
    except (OperationalError, ProgrammingError):
        post = None
    if not post:
        post = get_post(post_slug)
    if not post:
        raise Http404("Post not found")

    approved_comments = []
    related_posts = []
    comment_form = BlogCommentForm()

    if hasattr(post, "pk"):
        view_key = f"blog-view:{post.pk}:{request_fingerprint(request, 'blog-view')}"
        if cache.add(view_key, 1, timeout=1800):
            BlogPost.objects.filter(pk=post.pk).update(view_count=models.F("view_count") + 1)
        if request.method == "POST":
            comment_form = BlogCommentForm(request.POST)
            if comment_form.is_valid():
                comment = comment_form.save(commit=False)
                comment.post = post
                comment.save()
                comment_form = BlogCommentForm()
        approved_comments = list(post.comments.filter(is_approved=True, is_spam=False))
        related_posts = list(
            BlogPost.objects.filter(status="published")
            .exclude(pk=post.pk)
            .filter(
                models.Q(category=post.category) | models.Q(tags__in=post.tags.all())
            )
            .filter(models.Q(publish_at__lte=timezone.now()) | models.Q(publish_at__isnull=True))
            .distinct()
            .select_related("category")[:4]
        )

    # Prepare SEO image and keywords for the article (prefer featured image)
    seo_image = ""
    if hasattr(post, "featured_image") and getattr(post, "featured_image"):
        try:
            seo_image = post.featured_image.url
        except Exception:
            seo_image = getattr(post, "featured_image_url", "") or getattr(post, "image_url", "")
    else:
        seo_image = getattr(post, "featured_image_url", "") or getattr(post, "image_url", "")
    seo_keywords = getattr(post, "meta_keywords", "") or ""

    context = build_base_context(request)
    context.update(
        {
            "seo": build_seo(
                f"{post.title if hasattr(post, 'title') else post['title']} | {context.get('settings_obj').site_name if context.get('settings_obj') else SITE_NAME}",
                post.meta_description if hasattr(post, "meta_description") else post["meta_description"],
                request,
                image=seo_image,
                keywords=seo_keywords,
                page_type="BlogPosting",
                published_at=getattr(post, "publish_at", None) or getattr(post, "created_at", None),
                modified_at=getattr(post, "updated_at", None),
            ),
            "post": post,
            "article_intro": post.excerpt if hasattr(post, "excerpt") else post["intro"],
            "article_sections": getattr(post, "sections", None),
            "comment_form": comment_form,
            "approved_comments": approved_comments,
            "related_posts": related_posts,
            "share_url": request.build_absolute_uri(request.path),
            "page_images": with_fallback_media(get_page_media("blog_post"), get_page_image_block("blog_post")),
        }
    )
    return render_clean(request, "blog/detail.html", context)


@require_POST
@csrf_protect
@rate_limit("blog-read", limit=20, window=300)
def blog_track_read(request, post_slug):
    try:
        seconds = int(request.POST.get("seconds", "0"))
    except (TypeError, ValueError):
        seconds = 0
    seconds = min(max(seconds, 0), 900)
    dedupe_key = f"blog-read:{post_slug}:{request_fingerprint(request, 'blog-read-once')}"
    if seconds >= 4 and cache.add(dedupe_key, 1, timeout=6 * 3600):
        BlogPost.objects.filter(slug=post_slug, status="published").update(
            total_read_seconds=models.F("total_read_seconds") + seconds
        )
    return JsonResponse({"ok": True})


@require_POST
@csrf_protect
@rate_limit("lead", limit=5, window=600)
def capture_lead(request):
    if request.POST.get("website"):
        return JsonResponse({"ok": True})

    name = (request.POST.get("name") or "زائر الموقع").strip()[:120]
    phone = (request.POST.get("phone") or request.POST.get("mobile") or "").strip()[:20]
    city = (request.POST.get("city") or "").strip()[:120]
    district = (request.POST.get("district") or "").strip()[:140]
    service = (request.POST.get("service") or "").strip()[:160]
    details = (request.POST.get("details") or request.POST.get("message") or "").strip()[:3000]
    page_url = safe_page_url(
        request.POST.get("page_url") or request.META.get("HTTP_REFERER"),
        allowed_hosts=[request.get_host().split(":", 1)[0], getattr(settings, "SITE_DOMAIN", "")],
    )

    if phone and not valid_phone(phone):
        return JsonResponse({"ok": False, "error": "invalid_phone"}, status=400)
    if not phone:
        phone = "تواصل عبر واتساب"

    message_parts = []
    if service:
        message_parts.append(f"الخدمة: {service}")
    if district:
        message_parts.append(f"الحي: {district}")
    if details:
        message_parts.append(f"التفاصيل: {details}")
    if page_url:
        message_parts.append(f"صفحة الطلب: {page_url}")
    message = "\n".join(message_parts) or "طلب سريع من الموقع"

    try:
        lead = Lead.objects.create(
            name=name,
            phone=phone,
            city_name=city,
            district_name=district,
            message=message,
            source="website",
            page_url=page_url,
            utm_source=(request.POST.get("utm_source") or "").strip()[:120],
            utm_medium=(request.POST.get("utm_medium") or "").strip()[:120],
            utm_campaign=(request.POST.get("utm_campaign") or "").strip()[:160],
        )
        return JsonResponse({"ok": True, "lead_id": lead.pk})
    except (OperationalError, ProgrammingError):
        return JsonResponse({"ok": False, "error": "database_unavailable"}, status=503)


@require_POST
@csrf_protect
@rate_limit("conversion", limit=30, window=300)
def track_conversion(request):
    event_type = (request.POST.get("event_type") or "").strip()
    allowed = {choice[0] for choice in ConversionEvent.EVENT_CHOICES}
    if event_type not in allowed:
        return JsonResponse({"ok": False, "error": "invalid_event"}, status=400)

    page_url = safe_page_url(
        request.POST.get("page_url") or request.META.get("HTTP_REFERER"),
        allowed_hosts=[request.get_host().split(":", 1)[0], getattr(settings, "SITE_DOMAIN", "")],
    )
    try:
        event = ConversionEvent.objects.create(
            event_type=event_type,
            label=(request.POST.get("label") or "").strip()[:160],
            page_url=page_url,
            metadata={
                "city": (request.POST.get("city") or "")[:120],
                "district": (request.POST.get("district") or "")[:140],
                "service": (request.POST.get("service") or "")[:160],
                "utm_source": (request.POST.get("utm_source") or "")[:120],
                "utm_medium": (request.POST.get("utm_medium") or "")[:120],
                "utm_campaign": (request.POST.get("utm_campaign") or "")[:160],
            },
        )
        return JsonResponse({"ok": True, "event_id": event.pk})
    except (OperationalError, ProgrammingError):
        return JsonResponse({"ok": False, "error": "database_unavailable"}, status=503)


@cache_control(public=True, max_age=31536000, immutable=True)
def library_image_from_database(request, pk, filename):
    item = get_object_or_404(
        LibraryImage.objects.only("image_data", "image_content_type", "image_filename", "is_active"),
        pk=pk,
        is_active=True,
    )
    if not item.image_data:
        raise Http404

    content = bytes(item.image_data)
    etag = hashlib.sha256(content).hexdigest()
    if request.headers.get("If-None-Match", "").strip('"') == etag:
        return HttpResponse(status=304)
    response = HttpResponse(content, content_type=item.image_content_type or "image/jpeg")
    response["ETag"] = f'"{etag}"'
    response["Content-Disposition"] = f'inline; filename="{item.image_filename or filename}"'
    return response


def contact(request):
    context = build_base_context(request)
    settings_obj = context.get("settings_obj")
    context.update(
        {
            "seo": build_seo(
                f"اتصل بنا | {settings_obj.site_name if settings_obj else SITE_NAME}",
                settings_obj.seo_default_description if settings_obj and settings_obj.seo_default_description else f"تواصل معنا الآن لطلب عرض سعر سريع لخدمات {highlights_phrase(settings_obj)} في السعودية.",
                request,
                image=settings_obj.default_og_image_resolved if settings_obj else "",
                keywords=settings_obj.seo_default_keywords if settings_obj else "",
            ),
            "phone": context.get("contact_phone") or PHONE_NUMBER,
            "page_images": with_fallback_media(get_page_media("contact"), get_page_image_block("contact")),
        }
    )
    return render_clean(request, "pages/contact.html", context)


LEGAL_PAGES = {
    "privacy": {
        "title": "سياسة الخصوصية",
        "description": "توضح هذه السياسة البيانات التي يجمعها الموقع عند إرسال طلب عرض سعر وكيف نستخدمها ونحميها.",
        "sections": [
            ("البيانات التي نجمعها", "قد نجمع الاسم ورقم الجوال والمدينة ونوع الخدمة والتفاصيل التي يرسلها الزائر طوعًا عبر نماذج الموقع."),
            ("سبب استخدام البيانات", "نستخدم البيانات للرد على الطلب، إعداد عرض سعر، تحسين الخدمة، وقياس أداء قنوات التواصل داخل الموقع."),
            ("الحفظ والحماية", "نحتفظ بالبيانات للمدة اللازمة لخدمة الطلب والمتابعة التجارية، ونطبق إجراءات تقنية وتنظيمية للحد من الوصول غير المصرح به."),
            ("مشاركة البيانات", "لا نبيع بيانات العملاء. قد نعالج البيانات عبر مزودي الاستضافة والتخزين والخدمات التقنية اللازمة لتشغيل الموقع."),
            ("حقوقك", "تقدر تطلب تصحيح بياناتك أو حذفها بالتواصل معنا عبر بيانات الاتصال الظاهرة في الموقع، مع مراعاة المتطلبات النظامية."),
            ("التحديثات", "قد نحدث هذه السياسة عند تطوير الموقع أو تغير آلية معالجة البيانات، ويظهر النص المحدث في هذه الصفحة."),
        ],
    },
    "terms": {
        "title": "الشروط والأحكام",
        "description": "شروط استخدام الموقع وطلب عروض الأسعار لخدمات اللاندسكيب والنخيل والصيانة.",
        "sections": [
            ("طبيعة المعلومات", "المحتوى والأسعار التقديرية والحاسبات في الموقع معلومات أولية، ولا تعتبر عرضًا ملزمًا قبل المعاينة واعتماد عرض السعر النهائي."),
            ("طلبات الخدمة", "إرسال الطلب لا ينشئ عقدًا تلقائيًا. يبدأ الالتزام بعد الاتفاق الواضح على نطاق العمل والسعر والمدة وطريقة الدفع."),
            ("الصور والمقاسات", "دقة التقدير تعتمد على صحة البيانات والصور والمقاسات التي يقدمها العميل، وقد تتغير التكلفة بعد المعاينة الميدانية."),
            ("الملكية الفكرية", "تصميم الموقع والنصوص والصور المملوكة للشركة محمية، ولا يجوز إعادة استخدامها تجاريًا بدون إذن."),
            ("الاستخدام المقبول", "يمنع إساءة استخدام النماذج أو إرسال بيانات مضللة أو محاولة تعطيل الموقع أو الوصول غير المصرح به."),
            ("التواصل", "لأي استفسار عن الشروط تواصل معنا عبر الهاتف أو واتساب أو البريد الظاهر في صفحة الاتصال."),
        ],
    },
}


def _legal_page(request, key):
    page = LEGAL_PAGES[key]
    context = build_base_context(request)
    context.update({
        "legal_page": page,
        "seo": build_seo(
            f"{page['title']} | {context.get('settings_obj').site_name if context.get('settings_obj') else SITE_NAME}",
            page["description"],
            request,
        ),
    })
    return render_clean(request, "pages/legal.html", context)


def privacy(request):
    return _legal_page(request, "privacy")


def terms(request):
    return _legal_page(request, "terms")


CALCULATOR_PAGES = {
    "landscape": {
        "title": "حاسبة تكلفة اللاندسكيب",
        "service": "لاندسكيب وتنسيق حدائق",
        "description": "تقدير تكلفة تصميم وتنفيذ اللاندسكيب للفلل والاستراحات والمشاريع.",
        "unit": "متر مربع",
        "min_rate": 180,
        "max_rate": 360,
        "tips": ["يشمل التقدير الزراعة والتوزيع العام.", "تزيد التكلفة مع الجلسات والممرات والإضاءة.", "المعاينة تحدد احتياج التربة والري."],
        "keywords": "حاسبة تكلفة لاندسكيب, تكلفة تنسيق حدائق, سعر اللاندسكيب",
    },
    "palm-supply": {
        "title": "حاسبة تكلفة توريد النخيل",
        "service": "توريد نخيل",
        "description": "تقدير تكلفة توريد النخيل حسب العدد والمقاس والنوع.",
        "unit": "نخلة",
        "min_rate": 450,
        "max_rate": 1800,
        "tips": ["السعر يتغير حسب نوع النخيل والمقاس.", "النقل والزراعة قد تحسب منفصلة.", "نخيل المداخل يحتاج اختيار مقاس متناسق."],
        "keywords": "حاسبة تكلفة توريد نخيل, سعر نخيل الرياض, تكلفة نخيل واشنطني",
    },
    "palm-pruning": {
        "title": "حاسبة تكلفة تكريب وتشذيب النخيل",
        "service": "تكريب أو تشذيب نخيل",
        "description": "تقدير تكلفة تنظيف وتكريب وتشذيب النخيل حسب العدد والارتفاع.",
        "unit": "نخلة",
        "min_rate": 45,
        "max_rate": 180,
        "tips": ["الارتفاع وكثافة السعف تؤثر على السعر.", "تنظيف المخلفات قد يضاف للتكلفة.", "التكريب الدوري يحسن الشكل ويقلل المخاطر."],
        "keywords": "حاسبة تكلفة تكريب نخيل, سعر تشذيب نخيل, تكلفة تنظيف نخيل",
    },
    "washingtonia-palm": {
        "title": "حاسبة تكلفة نخيل واشنطني",
        "service": "نخيل واشنطني",
        "description": "تقدير تكلفة توريد وزراعة نخيل واشنطني للمداخل والطرق.",
        "unit": "نخلة",
        "min_rate": 600,
        "max_rate": 2200,
        "tips": ["المقاس هو العامل الأكبر في السعر.", "يفضل للمداخل والطرق والمساحات المفتوحة.", "يحتاج ري منتظم بعد الزراعة."],
        "keywords": "حاسبة تكلفة نخيل واشنطني, سعر نخيل واشنطني, توريد نخيل واشنطنيا",
    },
    "royal-palm": {
        "title": "حاسبة تكلفة نخيل ملوكي",
        "service": "نخيل ملوكي",
        "description": "تقدير تكلفة توريد وزراعة النخيل الملوكي للواجهات الفاخرة.",
        "unit": "نخلة",
        "min_rate": 900,
        "max_rate": 3200,
        "tips": ["يناسب الفلل والواجهات الرسمية.", "يحتاج توزيع متناسق ومسافات واضحة.", "اختيار المقاس يغير التكلفة بشكل كبير."],
        "keywords": "حاسبة تكلفة نخيل ملوكي, سعر نخيل ملوكي, توريد نخيل ملوكي",
    },
    "natural-grass": {
        "title": "حاسبة تكلفة الثيل الطبيعي",
        "service": "ثيل طبيعي",
        "description": "تقدير تكلفة توريد وزراعة الثيل الطبيعي مع التسوية والري.",
        "unit": "متر مربع",
        "min_rate": 35,
        "max_rate": 95,
        "tips": ["جودة التربة والتسوية تؤثر على النتيجة.", "الثيل الطبيعي يحتاج ري وقص وصيانة.", "المساحات الكبيرة تخفض متوسط التكلفة."],
        "keywords": "حاسبة تكلفة ثيل طبيعي, سعر الثيل الطبيعي, زراعة ثيل طبيعي",
    },
    "artificial-grass": {
        "title": "حاسبة تكلفة العشب الصناعي",
        "service": "عشب صناعي",
        "description": "تقدير تكلفة تركيب العشب الصناعي للحدائق والجلسات والأسطح.",
        "unit": "متر مربع",
        "min_rate": 45,
        "max_rate": 140,
        "tips": ["السعر يتغير حسب سماكة وجودة العشب.", "تجهيز الأرضية مهم لطول عمر التركيب.", "مناسب لتقليل الصيانة واستهلاك الماء."],
        "keywords": "حاسبة تكلفة عشب صناعي, سعر العشب الصناعي, تركيب عشب صناعي",
    },
    "irrigation": {
        "title": "حاسبة تكلفة شبكات الري",
        "service": "شبكات ري",
        "description": "تقدير تكلفة شبكة الري للحدائق والنخيل والثيل.",
        "unit": "متر مربع",
        "min_rate": 25,
        "max_rate": 85,
        "tips": ["نوع الري يختلف بين التنقيط والرش.", "التحكم الآلي يزيد التكلفة ويحسن التشغيل.", "توزيع المناطق يقلل هدر الماء."],
        "keywords": "حاسبة تكلفة شبكات ري, سعر شبكة ري, ري بالتنقيط للنخيل",
    },
    "tree-supply": {
        "title": "حاسبة تكلفة توريد الأشجار",
        "service": "توريد أشجار",
        "description": "تقدير تكلفة توريد وزراعة أشجار ظل وزينة ومثمرة.",
        "unit": "شجرة",
        "min_rate": 120,
        "max_rate": 850,
        "tips": ["نوع الشجرة وحجمها يغيران السعر.", "أشجار الظل الكبيرة تحتاج نقل وزراعة بعناية.", "اختيار أشجار مناسبة للمناخ يقلل الصيانة."],
        "keywords": "حاسبة تكلفة توريد أشجار, سعر أشجار ظل, تكلفة زراعة أشجار",
    },
    "soil-preparation": {
        "title": "حاسبة تكلفة تجهيز التربة",
        "service": "تجهيز تربة زراعية",
        "description": "تقدير تكلفة تحسين وتجهيز التربة قبل الزراعة واللاندسكيب.",
        "unit": "متر مربع",
        "min_rate": 18,
        "max_rate": 60,
        "tips": ["قد تشمل إزالة تربة قديمة أو إضافة تربة محسنة.", "التسميد والخلطات ترفع الجودة والتكلفة.", "تجهيز التربة يحسن نجاح الزراعة."],
        "keywords": "حاسبة تكلفة تجهيز تربة, سعر تربة زراعية, تحسين تربة حدائق",
    },
    "fencing": {
        "title": "حاسبة تكلفة الشبوك",
        "service": "شبوك وسياجات",
        "description": "تقدير تكلفة تركيب الشبوك والسياجات للمزارع والاستراحات.",
        "unit": "متر طولي",
        "min_rate": 55,
        "max_rate": 180,
        "tips": ["الارتفاع ونوع الشبك يغيران السعر.", "الأعمدة والبوابات تحسب ضمن التفاصيل.", "الشبوك مناسبة للحماية والخصوصية."],
        "keywords": "حاسبة تكلفة شبوك, سعر تركيب شبوك, شبوك مزارع",
    },
    "shades": {
        "title": "حاسبة تكلفة المظلات",
        "service": "مظلات خارجية",
        "description": "تقدير تكلفة مظلات السيارات والجلسات والمداخل.",
        "unit": "متر مربع",
        "min_rate": 130,
        "max_rate": 380,
        "tips": ["نوع القماش أو المعدن يؤثر على السعر.", "المساحة والارتفاع وطريقة التثبيت مهمة.", "المظلات تكمل اللاندسكيب وتزيد الاستخدام."],
        "keywords": "حاسبة تكلفة مظلات, سعر مظلات سيارات, تركيب مظلات خارجية",
    },
}


def cost_calculator(request):
    context = build_base_context(request)
    calculators = [
        {"slug": slug, **calculator}
        for slug, calculator in CALCULATOR_PAGES.items()
    ]
    context.update(
        {
            "seo": build_seo(
                "حاسبة تكلفة اللاندسكيب والنخيل والثيل | تقدير سريع",
                "احسب تكلفة تقريبية لخدمات اللاندسكيب، توريد وزراعة النخيل، الثيل الطبيعي والعشب الصناعي وشبكات الري قبل طلب عرض السعر.",
                request,
                keywords="حاسبة تكلفة لاندسكيب, تكلفة توريد نخيل, تكلفة الثيل, تكلفة تنسيق حدائق",
            ),
            "calculators": calculators,
            "calculator": CALCULATOR_PAGES["landscape"],
            "calculator_slug": "landscape",
            "page_images": with_fallback_media(get_page_media("services"), get_page_image_block("services")),
        }
    )
    return render_clean(request, "pages/cost_calculator.html", context)


def cost_calculator_detail(request, calculator_slug):
    calculator = CALCULATOR_PAGES.get(calculator_slug)
    if not calculator:
        raise Http404("Calculator not found")
    context = build_base_context(request)
    context.update(
        {
            "seo": build_seo(
                f"{calculator['title']} | تقدير تكلفة سريع",
                calculator["description"],
                request,
                keywords=calculator["keywords"],
            ),
            "calculators": [{"slug": slug, **item} for slug, item in CALCULATOR_PAGES.items()],
            "calculator": calculator,
            "calculator_slug": calculator_slug,
            "page_images": with_fallback_media(get_page_media("services"), get_page_image_block("services")),
        }
    )
    return render_clean(request, "pages/cost_calculator.html", context)


COMPARISON_PAGES = {
    "washingtonia-vs-royal-palm": {
        "title": "نخيل واشنطني أم نخيل ملوكي؟",
        "description": "مقارنة عملية بين نخيل واشنطني والنخيل الملوكي من حيث الشكل والاستخدام والصيانة والأنسب للفلل والمداخل.",
        "left": "نخيل واشنطني",
        "right": "نخيل ملوكي",
        "left_points": ["مناسب للطرق والمداخل الواسعة", "يعطي ارتفاعًا واضحًا وسريع الحضور", "اختيار عملي للمشاريع الخارجية"],
        "right_points": ["مظهر فاخر ومنظم", "مناسب للفلل والواجهات الراقية", "يفضل عند التركيز على الهوية البصرية"],
        "recommendation": "إذا كان الهدف تغطية مداخل وطرق ومساحات كبيرة فالنخيل الواشنطني خيار عملي، أما إذا كان الهدف واجهة فاخرة ومظهر رسمي فالنخيل الملوكي غالبًا أفضل.",
        "keywords": "نخيل واشنطني, نخيل ملوكي, الفرق بين نخيل واشنطني وملوكي",
    },
    "natural-vs-artificial-grass": {
        "title": "ثيل طبيعي أم عشب صناعي؟",
        "description": "مقارنة بين الثيل الطبيعي والعشب الصناعي للحدائق والاستراحات من حيث الشكل والصيانة والري والتكلفة.",
        "left": "ثيل طبيعي",
        "right": "عشب صناعي",
        "left_points": ["مظهر طبيعي وملمس حي", "يحتاج ري وقص وصيانة", "مناسب لمن يريد حديقة خضراء حقيقية"],
        "right_points": ["صيانة أقل واستهلاك ماء شبه معدوم", "مناسب للممرات والجلسات والأسطح", "يحافظ على الشكل في الاستخدام اليومي"],
        "recommendation": "الثيل الطبيعي أفضل لعشاق المساحات الحية مع صيانة منتظمة، والعشب الصناعي أفضل إذا كانت الأولوية قلة الصيانة وتوفير الماء.",
        "keywords": "ثيل طبيعي, عشب صناعي, الفرق بين الثيل الطبيعي والصناعي",
    },
}


def comparison_detail(request, comparison_slug):
    comparison = COMPARISON_PAGES.get(comparison_slug)
    if not comparison:
        raise Http404("Comparison not found")
    context = build_base_context(request)
    context.update(
        {
            "seo": build_seo(
                f"{comparison['title']} | مقارنة لاختيار الأنسب",
                comparison["description"],
                request,
                keywords=comparison["keywords"],
            ),
            "comparison": comparison,
            "page_images": with_fallback_media(get_page_media("services"), get_page_image_block("services")),
        }
    )
    return render_clean(request, "pages/comparison_detail.html", context)


def _project_cards(queryset):
    items = [
        {
            "title": fix_arabic_text(project.title),
            "category": fix_arabic_text(project.get_category_display()),
            "image_url": project.image_url,
            "description": fix_arabic_text(project.description),
            "city": fix_arabic_text(project.city.name) if project.city else "",
            "district": fix_arabic_text(project.district.name) if project.district else "",
        }
        for project in queryset
    ]
    return assign_project_fallback_images(items)


def city_detail(request, city_slug):
    try:
        city_obj = CityModel.objects.filter(is_active=True, is_system=True, slug=city_slug).first()
    except (OperationalError, ProgrammingError):
        city_obj = None

    if city_obj:
        city = {
            "slug": city_obj.slug,
            "name": city_obj.name,
            "region": city_obj.region,
            "description": city_obj.short_description or city_obj.content,
        }
        city_pages = list(
            CityServicePage.objects.filter(city=city_obj, is_active=True)
            .select_related("service", "service__category")
            .order_by("service__display_order", "service__title")[:50]
        )
        districts = list(
            city_obj.districts.filter(is_active=True)
            .annotate(project_count=models.Count("projects", filter=models.Q(projects__is_visible=True)))
            .order_by("sort_order", "name")
        )
        service_links = [
            {
                "slug": item.custom_slug or item.service.slug,
                "name": item.service.title,
                "category": item.service.category.name if item.service.category else "",
                "description": strip_tags(item.content)[:220],
                "image": (get_images_by_category(resolve_service_category(item.service.slug), 1) or [{}])[0].get("image_url", ""),
                "url": reverse("city_service_detail", kwargs={"city_slug": city_slug, "service_slug": item.custom_slug or item.service.slug}),
            }
            for item in city_pages
        ]
        district_links = [
            {
                "name": district.name,
                "slug": district.slug,
                "project_count": district.project_count,
                "url": reverse("district_detail", kwargs={"city_slug": city_slug, "district_slug": district.slug}),
            }
            for district in districts
        ]
        published_filter = models.Q(publish_at__lte=timezone.now()) | models.Q(publish_at__isnull=True)
        city_posts = list(
            BlogPost.objects.filter(city=city_obj, status="published").filter(published_filter)
            .select_related("category", "district").order_by("-publish_at", "-created_at")[:12]
        )
        if not city_posts:
            city_posts = list(
                BlogPost.objects.filter(status="published").filter(published_filter)
                .select_related("category", "city", "district").order_by("-publish_at", "-created_at")[:12]
            )
        city_project_queryset = Project.objects.filter(city=city_obj, is_visible=True).select_related("city", "district").order_by("-created_at")[:9]
        city_projects = _project_cards(city_project_queryset)
        project_scope = f"مشاريع {city_obj.name}"
        if not city_projects:
            city_projects = _project_cards(Project.objects.filter(is_visible=True).select_related("city", "district").order_by("-created_at")[:9])
            project_scope = "نماذج من أعمال نخيل نجد"
    else:
        city = get_city(city_slug)
        if not city:
            raise Http404("City not found")
        districts = []
        district_links = []
        city_posts = []
        city_projects = get_projects_data()[:9]
        project_scope = "نماذج من أعمال نخيل نجد"
        service_links = [
            {
                "slug": service_slug,
                "name": service["name"],
                "category": "",
                "description": service["description"],
                "image": (get_images_by_category(resolve_service_category(service_slug), 1) or [{}])[0].get("image_url", ""),
                "url": reverse("city_service_detail", kwargs={"city_slug": city_slug, "service_slug": service_slug}),
            }
            for service_slug, service in SERVICE_SLUGS.items()
        ]

    context = build_base_context(request)
    brand = context.get("settings_obj").site_name if context.get("settings_obj") else SITE_NAME
    context.update(
        {
            "seo": build_seo(
                f"توريد نخيل ولاندسكيب في {city['name']} | {brand}",
                f"خدمات توريد وزراعة النخيل العربي والواشنطني والملوكي، وصيانة الحدائق والري والشبوك في {city['name']} وأحيائها.",
                request,
                keywords=f"توريد نخيل {city['name']}, لاندسكيب {city['name']}, شبوك {city['name']}, صيانة حدائق {city['name']}",
            ),
            "city": city,
            "service_links": service_links,
            "districts": districts,
            "district_links": district_links,
            "city_posts": city_posts,
            "city_projects": city_projects,
            "project_scope": project_scope,
            "city_stats": {
                "services": len(service_links),
                "articles": len(city_posts) if not city_obj else BlogPost.objects.filter(city=city_obj, status="published").count(),
                "districts": len(district_links),
                "projects": len(city_projects) if not city_obj else Project.objects.filter(city=city_obj, is_visible=True).count(),
            },
            "quote_message": build_quote_message(city_name=city["name"]),
            "page_images": with_fallback_media(get_page_media("city"), get_page_image_block("city")),
            "theme_css_vars": build_theme_css(settings_obj=context.get("settings_obj"), city=city_obj),
        }
    )
    return render_clean(request, "cities/detail.html", context)


def district_detail(request, city_slug, district_slug):
    city_obj = get_object_or_404(CityModel, slug=city_slug, is_active=True, is_system=True)
    district = get_object_or_404(District, city=city_obj, slug=district_slug, is_active=True)

    exact_projects = list(
        Project.objects.filter(city=city_obj, district=district, is_visible=True)
        .select_related("city", "district").order_by("-created_at")[:12]
    )
    project_scope = f"مشاريع حي {district.name}"
    projects = exact_projects
    if not projects:
        projects = list(
            Project.objects.filter(city=city_obj, is_visible=True)
            .select_related("city", "district").order_by("-created_at")[:12]
        )
        project_scope = f"مشاريع من {city_obj.name} قريبة من نطاق الحي"
    if not projects:
        projects = list(Project.objects.filter(is_visible=True).select_related("city", "district").order_by("-created_at")[:12])
        project_scope = "نماذج من أعمال نخيل نجد"

    published_filter = models.Q(publish_at__lte=timezone.now()) | models.Q(publish_at__isnull=True)
    posts = list(
        BlogPost.objects.filter(city=city_obj, district=district, status="published").filter(published_filter)
        .select_related("category", "district").order_by("-publish_at", "-created_at")[:8]
    )
    if not posts:
        posts = list(
            BlogPost.objects.filter(city=city_obj, status="published").filter(published_filter)
            .select_related("category", "district").order_by("-publish_at", "-created_at")[:8]
        )

    service_pages = list(
        CityServicePage.objects.filter(city=city_obj, district=district, is_active=True)
        .select_related("service", "service__category", "district")
        .order_by("service__display_order", "service__title")[:12]
    )
    if len(service_pages) < 6:
        excluded_ids = [item.pk for item in service_pages]
        service_pages.extend(
            CityServicePage.objects.filter(city=city_obj, is_active=True)
            .exclude(pk__in=excluded_ids)
            .select_related("service", "service__category", "district")
            .order_by("service__display_order", "service__title")[: 12 - len(service_pages)]
        )
    services = [
        {
            "name": item.service.title,
            "category": item.service.category.name if item.service.category else "",
            "description": strip_tags(item.content)[:180],
            "image": item.service.resolved_image,
            "url": reverse("city_service_detail", kwargs={"city_slug": city_slug, "service_slug": item.custom_slug or item.service.slug}),
        }
        for item in service_pages
    ]
    nearby_districts = [
        {
            "name": item.name,
            "url": reverse("district_detail", kwargs={"city_slug": city_slug, "district_slug": item.slug}),
        }
        for item in city_obj.districts.filter(is_active=True).exclude(pk=district.pk).order_by("sort_order", "name")[:12]
    ]

    context = build_base_context(request)
    brand = context.get("settings_obj").site_name if context.get("settings_obj") else SITE_NAME
    context.update(
        {
            "seo": build_seo(
                f"توريد نخيل ولاندسكيب في حي {district.name} {city_obj.name} | {brand}",
                f"صفحة حي {district.name} في {city_obj.name}: المشاريع المنشورة وخدمات توريد النخيل والحدائق والري والشبوك والمقالات المحلية.",
                request,
                keywords=f"نخيل حي {district.name}, لاندسكيب حي {district.name}, شبوك {district.name}, {city_obj.name}",
            ),
            "city": {"slug": city_obj.slug, "name": city_obj.name, "region": city_obj.region},
            "district": district,
            "projects": _project_cards(projects),
            "project_scope": project_scope,
            "exact_project_count": len(exact_projects),
            "posts": posts,
            "services": services,
            "nearby_districts": nearby_districts,
            "quote_message": build_quote_message(city_name=city_obj.name, service_name=f"خدمة في حي {district.name}"),
            "page_images": with_fallback_media(get_page_media("city"), get_page_image_block("city")),
            "theme_css_vars": build_theme_css(settings_obj=context.get("settings_obj"), city=city_obj),
        }
    )
    return render_clean(request, "cities/district_detail.html", context)

def city_service_detail(request, city_slug, service_slug):
    try:
        city_obj = CityModel.objects.filter(is_active=True, is_system=True, slug=city_slug).first()
        city_service_obj = None
        if city_obj:
            city_service_obj = CityServicePage.objects.filter(
                city=city_obj,
                is_active=True,
            ).select_related("service").filter(custom_slug=service_slug).first() or CityServicePage.objects.filter(
                city=city_obj,
                is_active=True,
                service__slug=service_slug,
            ).select_related("service").first()
        else:
            city_service_obj = None
    except (OperationalError, ProgrammingError):
        city_obj = None
        city_service_obj = None

    if city_service_obj:
        city = {"slug": city_obj.slug, "name": city_obj.name}
        service = {
            "name": city_service_obj.service.title,
            "keyword": city_service_obj.hero_title or city_service_obj.service.title,
            "description": city_service_obj.content,
            "summary": strip_tags(city_service_obj.content)[:260],
            "benefits": city_service_obj.benefits_list or city_service_obj.service.benefits_list,
        }
        related_services = [
            {
                "name": item.service.title,
                "url": reverse("city_service_detail", kwargs={"city_slug": city_slug, "service_slug": item.custom_slug or item.service.slug}),
            }
            for item in CityServicePage.objects.filter(city=city_obj, is_active=True).exclude(pk=city_service_obj.pk).select_related("service")
        ]
    else:
        city = get_city(city_slug)
        service = get_service(service_slug)
        if not city or not service:
            raise Http404("Page not found")
        service["summary"] = service.get("description", "")
        related_services = [
            {
                "name": related["name"],
                "url": reverse(
                    "city_service_detail",
                    kwargs={"city_slug": city_slug, "service_slug": related_slug},
                ),
            }
            for related_slug, related in SERVICE_SLUGS.items()
            if related_slug != service_slug
        ]

    service_category = resolve_service_category(service_slug)
    context = build_base_context(request)
    service_keyword = service["keyword"]
    page_phrase = service_keyword if city["name"] in service_keyword else f"{service_keyword} في {city['name']}"
    context.update(
        {
            "seo": build_seo(
                f"{page_phrase} | {context.get('settings_obj').site_name if context.get('settings_obj') else SITE_NAME}",
                f"{page_phrase} مع توضيح المواد ونطاق التنفيذ ومتطلبات الموقع وإرسال الطلب عبر واتساب.",
                request,
            ),
            "city": city,
            "service": service,
            "quote_message": build_quote_message(city_name=city["name"], service_name=service["name"]),
            "related_services": related_services,
            "page_images": with_fallback_media(get_page_media("city_service"), get_images_by_category(service_category, 4)),
            "theme_css_vars": build_theme_css(settings_obj=context.get("settings_obj"), city=city_obj),
        }
    )
    return render_clean(request, "cities/service_detail.html", context)


@require_GET
def health(request):
    return JsonResponse({"status": "ok"})


@require_GET
def ready(request):
    from core.health import readiness_status

    is_ready, payload = readiness_status()
    return JsonResponse(payload, status=200 if is_ready else 503)


@cache_control(public=True, max_age=3600)
def robots_txt(request):
    site_base = getattr(settings, "SITE_URL", None) or request.build_absolute_uri("/").rstrip("/")
    sitemap_url = site_base + reverse("sitemap_xml")
    host = site_base.replace("https://", "").replace("http://", "")
    lines = [
        "User-agent: *",
        "Disallow: /admin/",
        "Disallow: /__debug__/",
        "Allow: /",
        "Allow: /archive/",
        f"Host: {host}",
        f"Sitemap: {sitemap_url}",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain; charset=utf-8")


def _archive_static_pages():
    return [
        {"title": "الرئيسية", "url": reverse("home"), "kind": "صفحة رئيسية"},
        {"title": "من نحن", "url": reverse("about"), "kind": "صفحة تعريفية"},
        {"title": "الخدمات", "url": reverse("services"), "kind": "فهرس خدمات"},
        {"title": "الأعمال", "url": reverse("portfolio"), "kind": "معرض أعمال"},
        {"title": "المدن", "url": reverse("cities"), "kind": "فهرس مدن"},
        {"title": "المدونة", "url": reverse("blog"), "kind": "فهرس مقالات"},
        {"title": "اتصل بنا", "url": reverse("contact"), "kind": "تواصل"},
        {"title": "سياسة الخصوصية", "url": reverse("privacy"), "kind": "صفحة قانونية"},
        {"title": "الشروط والأحكام", "url": reverse("terms"), "kind": "صفحة قانونية"},
        {"title": "شبكة الأرشفة", "url": reverse("archive_network"), "kind": "فهرس محتوى"},
        {"title": "فهرس الخدمات", "url": reverse("archive_services"), "kind": "فهرس محتوى"},
        {"title": "فهرس المدن", "url": reverse("archive_cities"), "kind": "فهرس محتوى"},
        {"title": "فهرس المقالات", "url": reverse("archive_articles"), "kind": "فهرس محتوى"},
    ]


def _archive_services():
    services = []
    try:
        queryset = ServiceModel.objects.filter(is_visible=True).order_by("display_order", "title")
        for service in queryset:
            services.append({
                "title": fix_arabic_text(service.title),
                "description": fix_arabic_text(service.meta_description or service.description),
                "url": reverse("service_detail", kwargs={"service_slug": service.slug}),
                "slug": service.slug,
                "updated_at": service.updated_at,
            })
    except (OperationalError, ProgrammingError):
        services = []

    if not services:
        for slug, service in SERVICE_SLUGS.items():
            services.append({
                "title": fix_arabic_text(service["name"]),
                "description": fix_arabic_text(service.get("description", "")),
                "url": reverse("service_detail", kwargs={"service_slug": slug}),
                "slug": slug,
                "updated_at": None,
            })
    return services


def _archive_cities():
    cities = []
    try:
        queryset = CityModel.objects.filter(is_active=True, is_system=True).order_by("region", "name")
        for city in queryset:
            cities.append({
                "title": fix_arabic_text(city.name),
                "description": fix_arabic_text(city.meta_description or city.short_description or city.content),
                "url": reverse("city_detail", kwargs={"city_slug": city.slug}),
                "slug": city.slug,
                "region": fix_arabic_text(city.region),
                "updated_at": city.updated_at,
            })
    except (OperationalError, ProgrammingError):
        cities = []

    if not cities:
        for city in CITIES:
            cities.append({
                "title": fix_arabic_text(city["name"]),
                "description": fix_arabic_text(city.get("description", "")),
                "url": reverse("city_detail", kwargs={"city_slug": city["slug"]}),
                "slug": city["slug"],
                "region": fix_arabic_text(city.get("region", "")),
                "updated_at": None,
            })
    return cities


def _archive_districts():
    districts = []
    try:
        queryset = (
            District.objects.filter(is_active=True, city__is_active=True, city__is_system=True)
            .select_related("city")
            .order_by("city__name", "sort_order", "name")
        )
        for district in queryset:
            districts.append({
                "title": fix_arabic_text(district.name),
                "city": fix_arabic_text(district.city.name),
                "url": reverse(
                    "district_detail",
                    kwargs={"city_slug": district.city.slug, "district_slug": district.slug},
                ),
                "updated_at": district.updated_at,
            })
    except (OperationalError, ProgrammingError):
        districts = []
    return districts


def _archive_articles():
    articles = []
    categories = []
    tags = []
    try:
        posts = (
            BlogPost.objects.filter(status="published")
            .filter(models.Q(publish_at__lte=timezone.now()) | models.Q(publish_at__isnull=True))
            .select_related("category")
            .order_by("-publish_at", "-updated_at")
        )
        for post in posts:
            articles.append({
                "title": fix_arabic_text(post.title),
                "description": fix_arabic_text(post.meta_description or post.excerpt),
                "url": reverse("blog_detail", kwargs={"post_slug": post.slug}),
                "updated_at": post.updated_at,
            })
        categories = [
            {"title": fix_arabic_text(item.name), "url": reverse("blog_category", kwargs={"category_slug": item.slug})}
            for item in BlogCategory.objects.order_by("name")
        ]
        tags = [
            {"title": fix_arabic_text(item.name), "url": reverse("blog_tag", kwargs={"tag_slug": item.slug})}
            for item in BlogTag.objects.order_by("name")
        ]
    except (OperationalError, ProgrammingError):
        articles = []

    if not articles:
        for post in BLOG_POSTS:
            articles.append({
                "title": fix_arabic_text(post["title"]),
                "description": fix_arabic_text(post.get("meta_description", "")),
                "url": reverse("blog_detail", kwargs={"post_slug": post["slug"]}),
                "updated_at": None,
            })
    return articles, categories, tags


def _archive_city_service_links(limit=None):
    links = []
    try:
        queryset = (
            CityServicePage.objects.filter(is_active=True)
            .select_related("city", "service")
            .order_by("city__name", "service__display_order", "service__title")
        )
        if limit:
            queryset = queryset[:limit]
        for item in queryset:
            links.append({
                "title": fix_arabic_text(item.hero_title or f"{item.service.title} في {item.city.name}"),
                "description": fix_arabic_text(item.meta_description),
                "url": reverse("city_service_detail", kwargs={"city_slug": item.city.slug, "service_slug": item.custom_slug or item.service.slug}),
                "city": fix_arabic_text(item.city.name),
                "service": fix_arabic_text(item.service.title),
            })
    except (OperationalError, ProgrammingError):
        links = []

    if not links:
        for city in CITIES:
            for service_slug, service in SERVICE_SLUGS.items():
                links.append({
                    "title": f"{fix_arabic_text(service['name'])} في {fix_arabic_text(city['name'])}",
                    "description": fix_arabic_text(service.get("description", "")),
                    "url": reverse("city_service_detail", kwargs={"city_slug": city["slug"], "service_slug": service_slug}),
                    "city": fix_arabic_text(city["name"]),
                    "service": fix_arabic_text(service["name"]),
                })
                if limit and len(links) >= limit:
                    return links
    return links


def archive_network(request):
    context = build_base_context(request)
    services = _archive_services()
    cities = _archive_cities()
    articles, categories, tags = _archive_articles()
    city_services = _archive_city_service_links(limit=None)
    districts = _archive_districts()
    context.update({
        "seo": build_seo(
            "فهرس الموقع | الخدمات والمدن والأحياء والمقالات",
            "فهرس منظم يجمع صفحات الخدمات والمدن والأحياء والمقالات والحاسبات في مكان واحد.",
            request,
            keywords="فهرس الموقع, خريطة الموقع, خدمات النخيل, لاندسكيب, توريد أشجار, شبوك, مظلات",
        ),
        "archive_title": "فهرس الموقع",
        "archive_intro": "صفحة مركزية للوصول إلى الخدمات والمدن والأحياء والمقالات والحاسبات.",
        "static_pages": _archive_static_pages(),
        "services": services[:60],
        "calculators": [{"slug": slug, **item} for slug, item in CALCULATOR_PAGES.items()],
        "cities": cities,
        "districts": districts[:120],
        "articles": articles[:40],
        "categories": categories,
        "tags": tags,
        "city_services": city_services[:120],
        "counts": {
            "services": len(services),
            "cities": len(cities),
            "districts": len(districts),
            "articles": len(articles),
            "city_services": len(city_services),
        },
    })
    return render_clean(request, "pages/archive_network.html", context)


def archive_services(request):
    context = build_base_context(request)
    services = _archive_services()
    context.update({
        "seo": build_seo(
            "فهرس خدمات النخيل واللاندسكيب والشبوك والمظلات",
            "كل صفحات الخدمات المتخصصة في توريد النخيل، تكريب وتشذيب النخيل، اللاندسكيب، الأشجار، الثيل، الري، الشبوك والمظلات.",
            request,
        ),
        "archive_title": "فهرس الخدمات",
        "archive_intro": "روابط مباشرة لصفحات الخدمات وتصنيفاتها المحلية.",
        "items": services,
        "item_kind": "خدمة",
    })
    return render_clean(request, "pages/archive_list.html", context)


def archive_cities(request):
    context = build_base_context(request)
    context.update({
        "seo": build_seo(
            "فهرس المدن والأحياء والخدمات المحلية",
            "فهرس منظم لصفحات المدن والأحياء والخدمات المحلية داخل كل مدينة.",
            request,
        ),
        "archive_title": "فهرس المدن والأحياء والخدمات المحلية",
        "archive_intro": "روابط مباشرة للمدن والأحياء وصفحات الخدمات المرتبطة بكل مدينة.",
        "cities": _archive_cities(),
        "districts": _archive_districts(),
        "city_services": _archive_city_service_links(limit=None),
    })
    return render_clean(request, "pages/archive_cities.html", context)


def archive_articles(request):
    context = build_base_context(request)
    articles, categories, tags = _archive_articles()
    context.update({
        "seo": build_seo(
            "فهرس مقالات النخيل واللاندسكيب",
            "كل مقالات الموقع عن توريد النخيل وتكريب النخيل واللاندسكيب وتوريد الأشجار والثيل والري والشبوك والمظلات.",
            request,
        ),
        "archive_title": "فهرس المقالات والتصنيفات",
        "archive_intro": "روابط المقالات والتصنيفات والوسوم مرتبة في صفحة واحدة.",
        "articles": articles,
        "categories": categories,
        "tags": tags,
    })
    return render_clean(request, "pages/archive_articles.html", context)


def _sitemap_base(request):
    return getattr(settings, "SITE_URL", None) or request.build_absolute_uri("/").rstrip("/")


def _sitemap_absolute(request, url):
    site_base = _sitemap_base(request)
    if not url:
        return ""
    if url.startswith("http://") or url.startswith("https://"):
        return url
    if url.startswith("/"):
        return site_base + url
    return site_base + "/" + url


def _sitemap_iso(dt):
    return dt.astimezone(datetime_timezone.utc).isoformat() if dt else None


def _sitemap_image_sets(request):
    return {
        "home_gallery": [{"loc": _sitemap_absolute(request, item["image_url"]), "title": item.get("title", "")} for item in get_page_image_block("home_gallery")[:4]],
        "services": [{"loc": _sitemap_absolute(request, item["image_url"]), "title": item.get("title", "")} for item in get_page_image_block("services")[:2]],
        "city": [{"loc": _sitemap_absolute(request, item["image_url"]), "title": item.get("title", "")} for item in get_page_image_block("city")[:3]],
        "city_service": [{"loc": _sitemap_absolute(request, item["image_url"]), "title": item.get("title", "")} for item in get_page_image_block("city_service")[:2]],
        "blog_post": [{"loc": _sitemap_absolute(request, item["image_url"]), "title": item.get("title", "")} for item in get_page_image_block("blog_post")[:1]],
    }


def _unique_sitemap_images(images):
    seen = set()
    output = []
    for image in images:
        loc = image.get("loc")
        if not loc or loc in seen:
            continue
        seen.add(loc)
        output.append(image)
    return output


def _all_sitemap_images(request):
    images = []

    for group in ("home_hero", "home_gallery", "home_banners", "about", "services", "portfolio", "cities", "blog", "blog_post", "contact", "city", "city_service"):
        for item in get_page_image_block(group):
            if item.get("image_url"):
                images.append({
                    "loc": _sitemap_absolute(request, item["image_url"]),
                    "title": item.get("title", "") or item.get("display_alt", ""),
                })

    try:
        for item in PageMedia.objects.filter(is_active=True):
            if item.image_url:
                images.append({"loc": _sitemap_absolute(request, item.image_url), "title": item.title})
        for item in LibraryImage.objects.filter(is_active=True).defer("image_data"):
            if item.image_url:
                images.append({"loc": _sitemap_absolute(request, item.image_url), "title": item.title})
        for service in ServiceModel.objects.filter(is_visible=True):
            if service.resolved_image:
                images.append({"loc": _sitemap_absolute(request, service.resolved_image), "title": service.title})
        for project in Project.objects.filter(is_visible=True):
            if project.image_url:
                images.append({"loc": _sitemap_absolute(request, project.image_url), "title": project.title})
        for post in BlogPost.objects.filter(status="published").filter(models.Q(publish_at__lte=timezone.now()) | models.Q(publish_at__isnull=True)):
            if post.image_url:
                images.append({"loc": _sitemap_absolute(request, post.image_url), "title": post.title})
    except (OperationalError, ProgrammingError):
        pass

    return _unique_sitemap_images(images)


def _render_sitemap_urlset(items):
    xml = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">',
    ]
    for item in items:
        xml.append("<url>")
        xml.append(f"<loc>{escape(item['loc'])}</loc>")
        if item.get("lastmod"):
            xml.append(f"<lastmod>{escape(item['lastmod'])}</lastmod>")
        if item.get("changefreq"):
            xml.append(f"<changefreq>{escape(item['changefreq'])}</changefreq>")
        if item.get("priority"):
            xml.append(f"<priority>{escape(item['priority'])}</priority>")
        for image in item.get("images", []) or []:
            if image.get("loc"):
                xml.append("<image:image>")
                xml.append(f"<image:loc>{escape(image['loc'])}</image:loc>")
                if image.get("title"):
                    xml.append(f"<image:title>{escape(image['title'])}</image:title>")
                xml.append("</image:image>")
        xml.append("</url>")
    xml.append("</urlset>")
    return HttpResponse("".join(xml), content_type="application/xml; charset=utf-8")


def _render_sitemap_index(request, sitemaps):
    xml = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for sitemap in sitemaps:
        xml.append("<sitemap>")
        xml.append(f"<loc>{escape(_sitemap_absolute(request, sitemap['loc']))}</loc>")
        if sitemap.get("lastmod"):
            xml.append(f"<lastmod>{escape(sitemap['lastmod'])}</lastmod>")
        xml.append("</sitemap>")
    xml.append("</sitemapindex>")
    return HttpResponse("".join(xml), content_type="application/xml; charset=utf-8")


def _sitemap_collector(request):
    urls = []
    seen_locations = set()

    def add_url(location, lastmod=None, changefreq="weekly", priority="0.5", images=None):
        final_location = _sitemap_absolute(request, location)
        if final_location in seen_locations:
            return
        seen_locations.add(final_location)
        urls.append({
            "loc": final_location,
            "lastmod": lastmod,
            "changefreq": changefreq,
            "priority": priority,
            "images": images or [],
        })

    return urls, add_url


@cache_control(public=True, max_age=3600)
def sitemap_pages_xml(request):
    urls, add_url = _sitemap_collector(request)

    add_url(
        reverse("home"),
        lastmod=None,
        changefreq="daily",
        priority="1.0",
    )

    static_pages = {
        "about": "about",
        "services": "services",
        "portfolio": "portfolio",
        "cities": "cities",
        "blog": "blog",
        "contact": "contact",
        "privacy": "about",
        "terms": "about",
        "cost_calculator": "services",
        "archive_network": "services",
        "archive_services": "services",
        "archive_cities": "cities",
        "archive_articles": "blog",
    }
    for name, block_name in static_pages.items():
        add_url(
            reverse(name),
            lastmod=None,
            changefreq="monthly",
            priority="0.8",
        )

    for comparison_slug in COMPARISON_PAGES:
        add_url(
            reverse("comparison_detail", kwargs={"comparison_slug": comparison_slug}),
            lastmod=None,
            changefreq="monthly",
            priority="0.75",
        )

    for calculator_slug in CALCULATOR_PAGES:
        add_url(
            reverse("cost_calculator_detail", kwargs={"calculator_slug": calculator_slug}),
            lastmod=None,
            changefreq="monthly",
            priority="0.78",
        )

    return _render_sitemap_urlset(urls)


@cache_control(public=True, max_age=3600)
def sitemap_services_xml(request):
    urls, add_url = _sitemap_collector(request)

    for service_slug in SERVICE_SLUGS:
        add_url(
            reverse("service_detail", kwargs={"service_slug": service_slug}),
            lastmod=None,
            changefreq="weekly",
            priority="0.85",
        )

    try:
        for service in ServiceModel.objects.filter(is_visible=True):
            add_url(
                reverse("service_detail", kwargs={"service_slug": service.slug}),
                lastmod=_sitemap_iso(getattr(service, "updated_at", None)),
                changefreq="weekly",
                priority="0.85",
            )
    except (OperationalError, ProgrammingError):
        pass

    return _render_sitemap_urlset(urls)


@cache_control(public=True, max_age=3600)
def sitemap_cities_xml(request):
    urls, add_url = _sitemap_collector(request)

    for city in CITIES:
        add_url(
            reverse("city_detail", kwargs={"city_slug": city["slug"]}),
            lastmod=None,
            changefreq="weekly",
            priority="0.9",
        )

    try:
        for city in CityModel.objects.filter(is_active=True, is_system=True):
            add_url(
                reverse("city_detail", kwargs={"city_slug": city.slug}),
                lastmod=_sitemap_iso(getattr(city, "updated_at", None)),
                changefreq="weekly",
                priority="0.9",
            )
    except (OperationalError, ProgrammingError):
        pass

    return _render_sitemap_urlset(urls)


@cache_control(public=True, max_age=3600)
def sitemap_districts_xml(request):
    urls, add_url = _sitemap_collector(request)
    try:
        districts = District.objects.filter(is_active=True, city__is_active=True, city__is_system=True).select_related("city")
        for district in districts:
            add_url(
                reverse("district_detail", kwargs={"city_slug": district.city.slug, "district_slug": district.slug}),
                lastmod=_sitemap_iso(getattr(district, "updated_at", None)),
                changefreq="weekly",
                priority="0.78",
            )
    except (OperationalError, ProgrammingError):
        pass
    return _render_sitemap_urlset(urls)


@cache_control(public=True, max_age=3600)
def sitemap_local_services_xml(request):
    urls, add_url = _sitemap_collector(request)

    for city in CITIES:
        for service_slug in SERVICE_SLUGS:
            add_url(
                reverse("city_service_detail", kwargs={"city_slug": city["slug"], "service_slug": service_slug}),
                lastmod=None,
                changefreq="monthly",
                priority="0.7",
            )

    try:
        for item in CityServicePage.objects.filter(is_active=True).select_related("city", "service"):
            add_url(
                reverse(
                    "city_service_detail",
                    kwargs={"city_slug": item.city.slug, "service_slug": item.custom_slug or item.service.slug},
                ),
                lastmod=_sitemap_iso(getattr(item, "updated_at", None)),
                changefreq="monthly",
                priority="0.75",
            )
    except (OperationalError, ProgrammingError):
        pass

    return _render_sitemap_urlset(urls)


@cache_control(public=True, max_age=3600)
def sitemap_blog_xml(request):
    urls, add_url = _sitemap_collector(request)

    for post in BLOG_POSTS:
        add_url(
            reverse("blog_detail", kwargs={"post_slug": post["slug"]}),
            lastmod=None,
            changefreq="monthly",
            priority="0.6",
        )

    try:
        for category in BlogCategory.objects.all():
            add_url(reverse("blog_category", kwargs={"category_slug": category.slug}), lastmod=_sitemap_iso(getattr(category, "updated_at", None)), changefreq="monthly", priority="0.5")
        for tag in BlogTag.objects.all():
            add_url(reverse("blog_tag", kwargs={"tag_slug": tag.slug}), lastmod=_sitemap_iso(getattr(tag, "updated_at", None)), changefreq="monthly", priority="0.4")
        for post in BlogPost.objects.filter(status="published").filter(models.Q(publish_at__lte=timezone.now()) | models.Q(publish_at__isnull=True)):
            lastmod_dt = getattr(post, "publish_at", None) or getattr(post, "updated_at", None) or getattr(post, "created_at", None)
            add_url(reverse("blog_detail", kwargs={"post_slug": post.slug}), lastmod=_sitemap_iso(lastmod_dt), changefreq="monthly", priority="0.6")
    except (OperationalError, ProgrammingError):
        pass

    return _render_sitemap_urlset(urls)


@cache_control(public=True, max_age=3600)
def sitemap_images_xml(request):
    """Attach images to the pages where they are actually used."""
    urls, add_url = _sitemap_collector(request)

    def image_item(url, title):
        if not url:
            return None
        return {"loc": _sitemap_absolute(request, url), "title": title or ""}

    grouped = {}
    try:
        for item in PageMedia.objects.filter(is_active=True):
            record = image_item(item.image_url, item.display_alt)
            if record:
                grouped.setdefault(item.page, []).append(record)
        for item in LibraryImage.objects.filter(is_active=True).defer("image_data"):
            record = image_item(item.image_url, item.display_alt)
            if record:
                grouped.setdefault(item.usage_group, []).append(record)
    except (OperationalError, ProgrammingError):
        pass

    static_targets = {
        reverse("home"): grouped.get("home", []) + grouped.get("home_hero", []) + grouped.get("home_gallery", []) + grouped.get("home_banners", []),
        reverse("about"): grouped.get("about", []),
        reverse("services"): grouped.get("services", []),
        reverse("portfolio"): grouped.get("portfolio", []),
        reverse("cities"): grouped.get("cities", []) + grouped.get("city", []),
        reverse("blog"): grouped.get("blog", []),
        reverse("contact"): grouped.get("contact", []),
    }

    try:
        project_images = []
        for project in Project.objects.filter(is_visible=True).prefetch_related("gallery"):
            record = image_item(project.image_url, project.title)
            if record:
                project_images.append(record)
            for gallery_item in project.gallery.all():
                record = image_item(gallery_item.image_url, gallery_item.title or project.title)
                if record:
                    project_images.append(record)
        static_targets[reverse("portfolio")].extend(project_images)

        for service in ServiceModel.objects.filter(is_visible=True):
            record = image_item(service.resolved_image, service.title)
            if record:
                add_url(
                    reverse("service_detail", kwargs={"service_slug": service.slug}),
                    lastmod=_sitemap_iso(getattr(service, "updated_at", None)),
                    changefreq="weekly",
                    priority="0.85",
                    images=[record],
                )

        published_posts = BlogPost.objects.filter(status="published").filter(
            models.Q(publish_at__lte=timezone.now()) | models.Q(publish_at__isnull=True)
        )
        for post in published_posts:
            record = image_item(post.image_url, post.title)
            if record:
                add_url(
                    reverse("blog_detail", kwargs={"post_slug": post.slug}),
                    lastmod=_sitemap_iso(getattr(post, "updated_at", None) or getattr(post, "publish_at", None)),
                    changefreq="monthly",
                    priority="0.6",
                    images=[record],
                )
    except (OperationalError, ProgrammingError):
        pass

    for location, images in static_targets.items():
        unique_images = _unique_sitemap_images(images)
        if unique_images:
            add_url(location, changefreq="weekly", priority="0.7", images=unique_images[:1000])

    return _render_sitemap_urlset(urls)


@cache_control(public=True, max_age=3600)
def sitemap_xml(request):
    return _render_sitemap_index(
        request,
        [
            {"loc": reverse("sitemap_pages_xml")},
            {"loc": reverse("sitemap_services_xml")},
            {"loc": reverse("sitemap_cities_xml")},
            {"loc": reverse("sitemap_districts_xml")},
            {"loc": reverse("sitemap_local_services_xml")},
            {"loc": reverse("sitemap_blog_xml")},
            {"loc": reverse("sitemap_images_xml")},
        ],
    )


def custom_404(request, exception=None, **kwargs):
    context = build_base_context(request)
    context["seo"] = build_seo(
        f"الصفحة غير موجودة | {context.get('settings_obj').site_name if context.get('settings_obj') else SITE_NAME}",
        "عذرًا، الصفحة المطلوبة غير موجودة. يمكنك العودة إلى الرئيسية أو تصفح الخدمات والمدن والمشاريع.",
        request,
        robots="noindex, nofollow",
    )
    return render_clean(request, "404.html", context, status=404)
