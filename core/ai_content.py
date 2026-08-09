import base64
import json
import mimetypes
import os
import re

import requests
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.text import slugify
from django.utils import timezone

from .html_utils import sanitize_html
from .local_seo import ensure_local_service_pages
from .models import BlogCategory, BlogPost, BlogTag, City, CityServicePage, Page, PageMedia, Service, SiteSettings


TOKENMIX_DEFAULT_BASE_URL = "https://api.tokenmix.ai/v1"


class AIContentError(Exception):
    def __init__(self, message, raw_text="", raw_response=None):
        super().__init__(message)
        self.raw_text = raw_text
        self.raw_response = raw_response or {}


def _sanitize_env_value(value):
    """
    Ensure env values used in HTTP headers are single-line and trimmed.
    This prevents invalid header errors caused by accidental pasted lines.
    """
    if not value:
        return ""
    cleaned = str(value).replace("\r", "").strip()
    if "\n" in cleaned:
        cleaned = cleaned.split("\n", 1)[0].strip()
    return cleaned.strip("\"'")


def _get_ai_model():
    model = _sanitize_env_value(os.environ.get("TOKENMIX_MODEL") or "gpt-4o-mini")
    return model or "gpt-4o-mini"


def _get_ai_api_key():
    api_key = _sanitize_env_value(os.environ.get("TOKENMIX_API_KEY") or "")
    if not api_key:
        return ""
    for marker in ("TOKENMIX_MODEL=", "TOKENMIX_BASE_URL="):
        if marker in api_key:
            api_key = api_key.split(marker, 1)[0].strip()
    return api_key


def _get_ai_base_url():
    base_url = _sanitize_env_value(os.environ.get("TOKENMIX_BASE_URL", TOKENMIX_DEFAULT_BASE_URL))
    return (base_url or TOKENMIX_DEFAULT_BASE_URL).rstrip("/")


def _get_ai_api_url():
    return f"{_get_ai_base_url()}/chat/completions"


def is_tokenmix_configured():
    return bool(_get_ai_api_key())


def _dedupe_list(values):
    seen = set()
    output = []
    for value in values:
        normalized = (value or "").strip()
        key = normalized.lower()
        if not normalized or key in seen:
            continue
        seen.add(key)
        output.append(normalized)
    return output


def _sanitize_article_html(value):
    """Clean AI-generated HTML with a strict allowlist sanitizer."""
    return sanitize_html(value)


def _json_loads_maybe(text):
    if not text:
        raise AIContentError("لم يرجع الذكاء الاصطناعي أي نص.")

    cleaned = text.strip()
    if cleaned.startswith("```"):
        parts = cleaned.split("```")
        cleaned = next((part for part in parts if "{" in part or "[" in part), cleaned)
        cleaned = cleaned.replace("json", "", 1).strip()

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise AIContentError("تعذر قراءة JSON من استجابة TokenMix.")
    json_text = cleaned[start : end + 1]
    try:
        return json.loads(json_text)
    except json.JSONDecodeError as exc:
        raise AIContentError(
            f"رجع الذكاء الاصطناعي JSON غير صالح عند السطر {exc.lineno} والعمود {exc.colno}.",
            raw_text=json_text,
        ) from exc


def _extract_response_text(result):
    """Read OpenAI-compatible Chat Completions and legacy Responses payloads."""
    choices = result.get("choices") or []
    if choices:
        content = (choices[0].get("message") or {}).get("content", "")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return "".join(
                item.get("text", "")
                for item in content
                if isinstance(item, dict) and item.get("type") in {"text", "output_text"}
            )

    raw_text = result.get("output_text") or ""
    if raw_text:
        return raw_text
    for item in result.get("output", []):
        for content in item.get("content", []):
            if content.get("type") == "output_text" and content.get("text"):
                return content["text"]
    return ""


def _repair_json_with_tokenmix(api_key, raw_text):
    repair_payload = {
        "model": _get_ai_model(),
        "messages": [
            {
                "role": "system",
                "content": "You repair malformed JSON. Return one valid JSON object only. Do not add markdown or explanations.",
            },
            {
                "role": "user",
                "content": (
                    "Fix this malformed JSON so it parses correctly. Preserve the same keys and Arabic text. "
                    "Return valid JSON only:\n\n"
                    f"{raw_text}"
                ),
            },
        ],
        "response_format": {"type": "json_object"},
        "max_tokens": min(max(len(raw_text) // 2, 4000), 16000),
        "temperature": 0.1,
    }
    response = requests.post(
        _get_ai_api_url(),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=repair_payload,
        timeout=120,
    )
    if response.status_code >= 400:
        raise AIContentError("فشل إصلاح JSON عبر TokenMix.", raw_text=raw_text, raw_response={"error": response.text[:2000]})
    repaired_text = _extract_response_text(response.json())
    return _json_loads_maybe(repaired_text)


def _unique_slug(model, value, object_id=None, fallback_prefix="item"):
    base = slugify((value or "").strip())
    if not base:
        base = f"{fallback_prefix}-{timezone.now():%Y%m%d%H%M%S}"

    candidate = base
    counter = 2
    while model.objects.filter(slug=candidate).exclude(pk=object_id).exists():
        candidate = f"{base}-{counter}"
        counter += 1
    return candidate


def _unique_custom_slug(model, field_name, value, object_id=None, fallback_prefix="item"):
    base = slugify((value or "").strip())
    if not base:
        base = f"{fallback_prefix}-{timezone.now():%Y%m%d%H%M%S}"

    candidate = base
    counter = 2
    filter_kwargs = {field_name: candidate}
    while model.objects.filter(**filter_kwargs).exclude(pk=object_id).exists():
        candidate = f"{base}-{counter}"
        filter_kwargs = {field_name: candidate}
        counter += 1
    return candidate


def _encode_uploaded_image(uploaded_file):
    uploaded_file.seek(0)
    raw = uploaded_file.read()
    uploaded_file.seek(0)
    content_type = getattr(uploaded_file, "content_type", "") or mimetypes.guess_type(uploaded_file.name)[0] or "image/jpeg"
    encoded = base64.b64encode(raw).decode("utf-8")
    return f"data:{content_type};base64,{encoded}"


def _field_schema(content_type):
    schemas = {
        "blog_post": {
            "title": "عنوان المقال",
            "slug": "slug إنجليزي قصير باستخدام الشرطة فقط",
            "excerpt": "ملخص قصير من فقرتين كحد أقصى",
            "content": "محتوى HTML خفيف أو نص منسق بعناوين وفقرات فقط",
            "meta_title": "عنوان SEO لا يتجاوز 60 حرفًا تقريبًا",
            "meta_description": "وصف SEO لا يتجاوز 160 حرفًا تقريبًا",
            "meta_keywords": "كلمات مفتاحية مفصولة بفواصل",
            "category_name": "اسم التصنيف المناسب",
            "tag_names": ["وسم 1", "وسم 2", "وسم 3"],
        },
        "service": {
            "title": "عنوان الخدمة",
            "slug": "slug إنجليزي قصير باستخدام الشرطة فقط",
            "short_title": "عنوان مختصر للخدمة",
            "description": "وصف الخدمة بشكل مقنع وواضح",
            "benefits": ["ميزة 1", "ميزة 2", "ميزة 3"],
            "meta_title": "عنوان SEO",
            "meta_description": "وصف SEO",
            "meta_keywords": "كلمات مفتاحية مفصولة بفواصل",
        },
        "city": {
            "name": "اسم المدينة",
            "slug": "slug إنجليزي قصير باستخدام الشرطة فقط",
            "region": "المنطقة",
            "hero_title": "عنوان بارز للمدينة",
            "short_description": "وصف مختصر للمدينة",
            "content": "محتوى الصفحة",
            "meta_title": "عنوان SEO",
            "meta_description": "وصف SEO",
            "meta_keywords": "كلمات مفتاحية مفصولة بفواصل",
        },
        "page": {
            "title": "عنوان الصفحة",
            "slug": "slug إنجليزي قصير باستخدام الشرطة فقط",
            "menu_title": "عنوان القائمة",
            "hero_title": "عنوان الهيرو",
            "intro_text": "مقدمة الصفحة",
            "body": "محتوى الصفحة",
            "template_key": "أحد القوالب المتاحة أو custom",
            "meta_title": "عنوان SEO",
            "meta_description": "وصف SEO",
            "meta_keywords": "كلمات مفتاحية مفصولة بفواصل",
        },
        "city_service": {
            "hero_title": "عنوان الصفحة",
            "custom_slug": "slug إنجليزي قصير باستخدام الشرطة فقط",
            "content": "محتوى الخدمة داخل المدينة",
            "benefits": ["ميزة 1", "ميزة 2", "ميزة 3"],
            "meta_title": "عنوان SEO",
            "meta_description": "وصف SEO",
            "meta_keywords": "كلمات مفتاحية مفصولة بفواصل",
        },
        "bulk": {
            "cities": [{"name": " ", "slug": "english-slug", "region": "", "hero_title": " ", "short_description": " ", "content": " ", "meta_title": " SEO", "meta_description": " SEO", "meta_keywords": " "}],
            "services": [{"title": " ", "slug": "english-slug", "short_title": " ", "description": " ", "benefits": [" 1", " 2"], "meta_title": " SEO", "meta_description": " SEO", "meta_keywords": " "}],
            "city_services": [{"city_slug": "english-city-slug", "service_slug": "english-service-slug", "hero_title": " ", "custom_slug": "english-service-url-slug", "content": "    ", "benefits": [" 1", " 2"], "meta_title": " SEO", "meta_description": " SEO", "meta_keywords": " "}],
            "pages": [],
            "blog_posts": [],
            "site_settings": {},
        },    }
    return schemas[content_type]


def _system_prompt():
    return (
        "أنت مساعد تحرير عربي متخصص في مواقع الخدمات داخل السعودية. "
        "أنشئ أو حدّث أنواع المحتوى الموجودة في النظام: مقالات، خدمات، صفحات، وخدمات داخل المدن. "
        "المدن والأحياء كتالوج ثابت: لا تنشئها ولا تغيّر أسماءها أو روابطها؛ يمكنك فقط تحسين محتوى مدينة موجودة. "
        "التزم بالعربية الفصحى الواضحة، وبأسلوب مهني واقعي مناسب للـ SEO دون مبالغة أو ادعاءات غير موثقة. "
        "أخرج JSON صالحًا فقط دون أي شرح خارجي. "
        "لا تضف حقولًا غير مطلوبة. "
        "اجعل الروابط المختصرة slugs إنجليزية وصالحة لحقل slug."
    )


def generate_content_payload(form, uploaded_files):
    content_type = form.cleaned_data["content_type"]
    mode = form.cleaned_data["mode"]
    user_content = [
        {"type": "text", "text": _build_generation_prompt(form.cleaned_data)},
    ]
    for uploaded in uploaded_files:
        user_content.append({"type": "image_url", "image_url": {"url": _encode_uploaded_image(uploaded)}})

    body = {
        "model": _get_ai_model(),
        "messages": [
            {"role": "system", "content": _system_prompt()},
            {"role": "user", "content": user_content},
        ],
        "response_format": {"type": "json_object"},
        "max_tokens": 16000 if content_type == "bulk" else 6000,
        "temperature": 0.35,
    }
    return body, {
        "provider": "TokenMix",
        "model": _get_ai_model(),
        "content_type": content_type,
        "mode": mode,
        "image_count": len(uploaded_files),
    }


def _build_generation_prompt(data):
    schema = _field_schema(data["content_type"])
    existing_context = []
    if data.get("object_id"):
        existing_context.append(f"object_id المطلوب تحديثه: {data['object_id']}")
    if data.get("title_hint"):
        existing_context.append(f"عنوان/فكرة أولية: {data['title_hint']}")
    if data.get("blog_category"):
        existing_context.append(f"تصنيف المقال المطلوب: {data['blog_category'].name}")
    if data.get("blog_tags"):
        existing_context.append(f"وسوم مقترحة: {data['blog_tags']}")
    if data.get("city"):
        existing_context.append(f"المدينة المحددة: {data['city'].name}")
    if data.get("service"):
        existing_context.append(f"الخدمة المحددة: {data['service'].title}")
    if data.get("page_template_key"):
        existing_context.append(f"قالب الصفحة المطلوب: {data['page_template_key']}")

    return (
        f"نوع المحتوى: {data['content_type']}\n"
        f"الوضع: {data['mode']}\n"
        f"تعليمات المستخدم:\n{data['prompt']}\n\n"
        f"سياق إضافي:\n" + ("\n".join(existing_context) if existing_context else "لا يوجد") + "\n\n"
        f"الحقول المطلوبة في JSON:\n{json.dumps(schema, ensure_ascii=False, indent=2)}\n\n"
        "قواعد إضافية:\n"
        "- اجعل النص العربي طبيعيًا وقويًا للبيع.\n"
        "- اجعل الـ meta title والوصف مناسبين لمحركات البحث.\n"
        "- إن وُجدت صور فاستفد منها لفهم نوع المشروع والأسلوب البصري.\n"
        "- في حقل المحتوى استخدم فقرات وعناوين فرعية واضحة.\n"
        "- في benefits أعد مصفوفة نصوص قصيرة وواضحة.\n"
        "- لا تكتب أي شيء خارج JSON."
    )


def request_tokenmix_generation(form, uploaded_files):
    api_key = _get_ai_api_key()
    if not api_key:
        raise AIContentError("لم يتم ضبط TOKENMIX_API_KEY في متغيرات البيئة.")

    payload, request_meta = generate_content_payload(form, uploaded_files)
    response = requests.post(
        _get_ai_api_url(),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=180,
    )
    if response.status_code >= 400:
        try:
            error_payload = response.json()
        except Exception:
            error_payload = response.text
        raise AIContentError(f"فشل طلب TokenMix: {error_payload}")

    result = response.json()
    raw_text = _extract_response_text(result)
    if not raw_text:
        raise AIContentError("رجع TokenMix استجابة فارغة.", raw_response=result)
    try:
        parsed = _json_loads_maybe(raw_text)
    except AIContentError as exc:
        if not exc.raw_text:
            exc.raw_text = raw_text
        try:
            parsed = _repair_json_with_tokenmix(api_key, exc.raw_text or raw_text)
            request_meta["json_repaired"] = True
        except AIContentError as repair_exc:
            repair_exc.raw_text = repair_exc.raw_text or exc.raw_text or raw_text
            repair_exc.raw_response = result
            raise repair_exc from exc
    return parsed, request_meta, result


def _get_target_instance(content_type, object_id):
    model_map = {
        "blog_post": BlogPost,
        "service": Service,
        "city": City,
        "page": Page,
        "city_service": CityServicePage,
    }
    model = model_map[content_type]
    if not object_id:
        return None
    try:
        return model.objects.get(pk=object_id)
    except model.DoesNotExist as exc:
        raise ValidationError("العنصر المطلوب تحديثه غير موجود.") from exc


def _get_or_create_category(name):
    normalized = (name or "").strip()
    if not normalized:
        return None
    slug = _unique_slug(BlogCategory, normalized, fallback_prefix="category")
    category, _ = BlogCategory.objects.get_or_create(
        name=normalized,
        defaults={
            "slug": slug,
            "meta_title": normalized,
            "meta_description": normalized,
        },
    )
    return category


def _get_or_create_tags(tag_names):
    tags = []
    for tag_name in _dedupe_list(tag_names):
        slug = _unique_slug(BlogTag, tag_name, fallback_prefix="tag")
        tag, _ = BlogTag.objects.get_or_create(
            name=tag_name,
            defaults={
                "slug": slug,
                "meta_title": tag_name,
                "meta_description": tag_name,
            },
        )
        tags.append(tag)
    return tags


def _save_page_media(content_type, instance, uploaded_files):
    page_map = {
        "blog_post": "blog_post",
        "service": "services",
        "city": "city",
        "city_service": "city_service",
    }
    if content_type == "page":
        page_key = instance.template_key if instance.template_key in {choice[0] for choice in PageMedia.PAGE_CHOICES} else ""
    else:
        page_key = page_map.get(content_type, "")
    if not page_key:
        return

    for index, uploaded in enumerate(uploaded_files, start=1):
        PageMedia.objects.create(
            page=page_key,
            section="gallery",
            title=f"{getattr(instance, 'title', getattr(instance, 'name', 'محتوى'))} {index}",
            alt_text=f"{getattr(instance, 'title', getattr(instance, 'name', 'محتوى'))} {index}",
            image=uploaded,
            sort_order=index,
            is_active=True,
        )


@transaction.atomic
def save_generated_content(form, generated_payload, uploaded_files):
    content_type = form.cleaned_data["content_type"]
    mode = form.cleaned_data["mode"]
    object_id = form.cleaned_data.get("object_id")
    if content_type == "city" and mode == "update" and form.cleaned_data.get("city"):
        instance = form.cleaned_data["city"]
    else:
        instance = _get_target_instance(content_type, object_id) if mode == "update" else None

    if content_type == "blog_post":
        instance = _save_blog_post(instance, form, generated_payload, uploaded_files)
    elif content_type == "service":
        instance = _save_service(instance, form, generated_payload, uploaded_files)
    elif content_type == "city":
        instance = _save_city(instance, generated_payload, uploaded_files, form.cleaned_data.get("create_page_media"))
    elif content_type == "page":
        instance = _save_page(instance, form, generated_payload, uploaded_files)
    elif content_type == "city_service":
        instance = _save_city_service(instance, form, generated_payload, uploaded_files, form.cleaned_data.get("create_page_media"))
    elif content_type == "bulk":
        instance = save_bulk_generated_content(generated_payload, publish_now=form.cleaned_data.get("publish_now"))
    else:
        raise ValidationError("نوع المحتوى غير مدعوم.")

    return instance


def _save_blog_post(instance, form, payload, uploaded_files):
    category = form.cleaned_data.get("blog_category") or _get_or_create_category(payload.get("category_name"))
    is_create = instance is None
    instance = instance or BlogPost()
    instance.title = payload.get("title", "").strip()
    instance.slug = _unique_slug(BlogPost, payload.get("slug") or instance.title, object_id=instance.pk, fallback_prefix="blog")
    instance.excerpt = payload.get("excerpt", "").strip()
    instance.content = _sanitize_article_html(payload.get("content", ""))
    instance.meta_title = payload.get("meta_title", "").strip()
    instance.meta_description = payload.get("meta_description", "").strip()
    instance.meta_keywords = payload.get("meta_keywords", "").strip()
    instance.category = category
    if form.cleaned_data.get("city"):
        instance.city = form.cleaned_data["city"]
        instance.district = None
    instance.status = "published" if form.cleaned_data.get("publish_now") else "draft"
    if form.cleaned_data.get("publish_now") and not instance.publish_at:
        instance.publish_at = timezone.now()
    if uploaded_files:
        instance.featured_image = uploaded_files[0]
        instance.featured_image_url = ""
    instance.save()
    explicit_tag_names = payload.get("tag_names", []) or [
        value.strip() for value in (form.cleaned_data.get("blog_tags") or "").split(",") if value.strip()
    ]
    if explicit_tag_names:
        instance.tags.set(_get_or_create_tags(explicit_tag_names))
    if uploaded_files and is_create and form.cleaned_data.get("create_page_media"):
        _save_page_media("blog_post", instance, uploaded_files[1:])
    return instance


def _save_service(instance, form, payload, uploaded_files):
    instance = instance or Service()
    instance.title = payload.get("title", "").strip()
    instance.slug = _unique_slug(Service, payload.get("slug") or instance.title, object_id=instance.pk, fallback_prefix="service")
    instance.short_title = payload.get("short_title", "").strip()
    instance.description = payload.get("description", "").strip()
    instance.benefits = "\n".join(_dedupe_list(payload.get("benefits", [])))
    instance.meta_title = payload.get("meta_title", "").strip()
    instance.meta_description = payload.get("meta_description", "").strip()
    instance.meta_keywords = payload.get("meta_keywords", "").strip()
    city = form.cleaned_data.get("city")
    if city:
        instance.primary_city = city
        instance.primary_district = None
    instance.is_visible = True
    if uploaded_files:
        instance.image = uploaded_files[0]
        instance.image_url = ""
    instance.save()
    if city:
        instance.cities.add(city)
    return instance


def _save_city(instance, payload, uploaded_files, create_page_media):
    if instance is None:
        requested_slug = slugify(payload.get("slug") or "")
        requested_name = (payload.get("name") or "").strip()
        instance = City.objects.filter(is_system=True, slug=requested_slug).first() or City.objects.filter(is_system=True, name=requested_name).first()
    if instance is None:
        raise ValidationError("المدن ثابتة. اختر مدينة موجودة لتحديث محتواها بدل إنشاء مدينة جديدة.")
    # City identity is immutable; AI may improve only presentation and SEO fields.
    instance.name = instance.name
    instance.slug = instance.slug
    instance.region = instance.region
    instance.hero_title = payload.get("hero_title", "").strip()
    instance.short_description = payload.get("short_description", "").strip()
    instance.content = payload.get("content", "").strip()
    instance.meta_title = payload.get("meta_title", "").strip()
    instance.meta_description = payload.get("meta_description", "").strip()
    instance.meta_keywords = payload.get("meta_keywords", "").strip()
    instance.is_active = True
    instance.save()
    if uploaded_files and create_page_media:
        _save_page_media("city", instance, uploaded_files)
    return instance


def _save_page(instance, form, payload, uploaded_files):
    instance = instance or Page()
    instance.title = payload.get("title", "").strip()
    instance.slug = _unique_slug(Page, payload.get("slug") or instance.title, object_id=instance.pk, fallback_prefix="page")
    instance.menu_title = payload.get("menu_title", "").strip()
    instance.hero_title = payload.get("hero_title", "").strip()
    instance.intro_text = payload.get("intro_text", "").strip()
    instance.body = payload.get("body", "").strip()
    instance.template_key = form.cleaned_data.get("page_template_key") or payload.get("template_key") or "custom"
    if instance.template_key not in dict(Page.TEMPLATE_CHOICES):
        instance.template_key = "custom"
    instance.meta_title = payload.get("meta_title", "").strip()
    instance.meta_description = payload.get("meta_description", "").strip()
    instance.meta_keywords = payload.get("meta_keywords", "").strip()
    instance.is_visible = True
    instance.show_in_menu = True
    instance.save()
    if uploaded_files and form.cleaned_data.get("create_page_media"):
        _save_page_media("page", instance, uploaded_files)
    return instance


def _save_city_service(instance, form, payload, uploaded_files, create_page_media):
    city = form.cleaned_data.get("city")
    service = form.cleaned_data.get("service")
    if not city or not service:
        raise ValidationError("إنشاء خدمة داخل مدينة يحتاج إلى تحديد المدينة والخدمة.")

    instance = instance or CityServicePage(city=city, service=service)
    instance.city = city
    instance.service = service
    instance.hero_title = payload.get("hero_title", "").strip()
    instance.custom_slug = slugify(payload.get("custom_slug") or service.slug) or service.slug
    instance.content = payload.get("content", "").strip()
    instance.benefits = "\n".join(_dedupe_list(payload.get("benefits", [])))
    instance.meta_title = payload.get("meta_title", "").strip()
    instance.meta_description = payload.get("meta_description", "").strip()
    instance.meta_keywords = payload.get("meta_keywords", "").strip()
    instance.is_active = True
    instance.save()
    if uploaded_files and create_page_media:
        _save_page_media("city_service", instance, uploaded_files)
    return instance


def _set_if_payload(obj, payload, fields):
    changed = False
    for field in fields:
        if field in payload and payload[field] not in (None, ""):
            value = payload[field]
            if isinstance(value, list):
                value = "\n".join(_dedupe_list(value))
            if getattr(obj, field, None) != value:
                setattr(obj, field, value)
                changed = True
    return changed


@transaction.atomic
def save_bulk_generated_content(payload, publish_now=False):
    counts = {"cities": 0, "services": 0, "city_services": 0, "pages": 0, "blog_posts": 0, "site_settings": 0}

    for city_payload in payload.get("cities", []) or []:
        name = (city_payload.get("name") or "").strip()
        if not name:
            continue
        slug = slugify(city_payload.get("slug") or name)
        city = City.objects.filter(is_system=True, slug=slug).first() or City.objects.filter(is_system=True, name=name).first()
        if not city:
            continue
        _set_if_payload(
            city,
            city_payload,
            ["hero_title", "short_description", "content", "meta_title", "meta_description", "meta_keywords"],
        )
        city.is_active = True
        city.auto_generate_service_pages = True
        city.save()
        counts["cities"] += 1

    for service_payload in payload.get("services", []) or []:
        title = (service_payload.get("title") or "").strip()
        if not title:
            continue
        slug = slugify(service_payload.get("slug") or title) or f"service-{timezone.now():%Y%m%d%H%M%S}"
        service, _ = Service.objects.get_or_create(slug=slug, defaults={"title": title, "description": title})
        _set_if_payload(
            service,
            service_payload,
            ["title", "short_title", "description", "benefits", "meta_title", "meta_description", "meta_keywords"],
        )
        service.is_visible = True
        service.save()
        counts["services"] += 1

    for item in payload.get("city_services", []) or []:
        city = City.objects.filter(is_system=True, slug=item.get("city_slug")).first()
        service = Service.objects.filter(slug=item.get("service_slug")).first()
        if not city or not service:
            continue
        page, _ = CityServicePage.objects.get_or_create(city=city, service=service, defaults={"content": item.get("content", "")})
        _set_if_payload(page, item, ["hero_title", "content", "benefits", "meta_title", "meta_description", "meta_keywords"])
        if item.get("custom_slug"):
            page.custom_slug = slugify(item["custom_slug"]) or service.slug
        elif not page.custom_slug:
            page.custom_slug = service.slug
        page.is_active = True
        page.save()
        service.cities.add(city)
        counts["city_services"] += 1

    for page_payload in payload.get("pages", []) or []:
        title = (page_payload.get("title") or "").strip()
        if not title:
            continue
        slug = slugify(page_payload.get("slug") or title) or f"page-{timezone.now():%Y%m%d%H%M%S}"
        page, _ = Page.objects.get_or_create(slug=slug, defaults={"title": title})
        _set_if_payload(
            page,
            page_payload,
            ["title", "menu_title", "hero_title", "intro_text", "body", "template_key", "meta_title", "meta_description", "meta_keywords"],
        )
        page.is_visible = True
        page.save()
        counts["pages"] += 1

    for post_payload in payload.get("blog_posts", []) or []:
        title = (post_payload.get("title") or "").strip()
        if not title:
            continue
        slug = slugify(post_payload.get("slug") or title) or f"blog-{timezone.now():%Y%m%d%H%M%S}"
        post, _ = BlogPost.objects.get_or_create(slug=slug, defaults={"title": title, "content": post_payload.get("content", title)})
        _set_if_payload(post, post_payload, ["title", "excerpt", "content", "meta_title", "meta_description", "meta_keywords"])
        post.content = _sanitize_article_html(post.content)
        if publish_now:
            post.status = "published"
            if not post.publish_at:
                post.publish_at = timezone.now()
        post.save()
        counts["blog_posts"] += 1

    settings_payload = payload.get("site_settings") or {}
    if settings_payload:
        settings_obj = SiteSettings.load()
        _set_if_payload(
            settings_obj,
            settings_payload,
            [
                "site_name",
                "tagline",
                "footer_text",
                "homepage_meta_title",
                "homepage_meta_description",
                "seo_default_keywords",
                "seo_default_description",
                "seo_twitter_handle",
                "business_type",
                "legal_name",
                "street_address",
                "address_locality",
                "address_region",
                "postal_code",
                "address_country",
                "opening_hours",
                "area_served",
                "same_as_links",
            ],
        )
        settings_obj.save()
        counts["site_settings"] = 1

    ensure_local_service_pages(overwrite=False)
    return counts
