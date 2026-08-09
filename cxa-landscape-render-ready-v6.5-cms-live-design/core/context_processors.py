from django.conf import settings
from django.core.cache import cache
from django.db.utils import OperationalError, ProgrammingError
from django.urls import NoReverseMatch, reverse

from .data import LANGUAGES, PHONE_NUMBER, SERVICE_SLUGS, SITE_NAME
from .html_utils import safe_json_dumps
from .models import ContactNumber, NavigationItem, Page, SiteSettings, SiteVerification, Testimonial
from .text_utils import fix_arabic_text


def resolve_navigation_items():
    cached_items = cache.get("site:navigation_items")
    if cached_items is not None:
        return cached_items

    items = []
    try:
        route_map = {
            "home": "/",
            "about": reverse("about"),
            "services": reverse("services"),
            "portfolio": reverse("portfolio"),
            "cities": reverse("cities"),
            "blog": reverse("blog"),
            "contact": reverse("contact"),
        }
        queryset = NavigationItem.objects.filter(is_visible=True).select_related("linked_page")
        for item in queryset:
            url = ""
            if item.external_url:
                url = item.external_url
            elif item.linked_page:
                url = route_map.get(item.linked_page.template_key) or reverse(
                    "managed_page", kwargs={"page_slug": item.linked_page.resolved_path}
                )
            elif item.route_name:
                try:
                    url = reverse(item.route_name)
                except NoReverseMatch:
                    url = "#"
            if url:
                items.append({"label": fix_arabic_text(item.label), "url": url, "new_tab": item.open_in_new_tab})

        if items:
            cache.set("site:navigation_items", items, 300)
            return items

        for page in Page.objects.filter(show_in_menu=True, is_visible=True).order_by("menu_order"):
            url = route_map.get(page.template_key) or reverse("managed_page", kwargs={"page_slug": page.resolved_path})
            items.append({"label": fix_arabic_text(page.menu_title or page.title), "url": url, "new_tab": False})
    except (OperationalError, ProgrammingError):
        return []
    cache.set("site:navigation_items", items, 300)
    return items


def build_theme_css(settings_obj=None, city=None):
    if not settings_obj and not city:
        return ""

    primary = city.primary_color if city and getattr(city, "primary_color", "") else getattr(settings_obj, "primary_color", "#83643b")
    secondary = city.secondary_color if city and getattr(city, "secondary_color", "") else getattr(settings_obj, "secondary_color", "#0f5b54")
    accent = city.accent_color if city and getattr(city, "accent_color", "") else getattr(settings_obj, "accent_color", "#c6a56d")
    background = city.background_color if city and getattr(city, "background_color", "") else getattr(settings_obj, "background_color", "#f7f1e8")
    text = getattr(settings_obj, "text_color", "#1c1915")
    return f"--primary:{primary};--secondary:{secondary};--accent:{accent};--bg:{background};--text:{text};"


def _to_whatsapp_digits(raw_phone):
    digits = "".join(char for char in (raw_phone or "") if char.isdigit())
    if digits.startswith("0"):
        digits = f"966{digits[1:]}"
    return digits


def site_defaults(request):
    cached_defaults = cache.get("site:defaults")
    if cached_defaults is not None:
        return cached_defaults

    site_name = SITE_NAME
    phone = PHONE_NUMBER
    whatsapp_number = PHONE_NUMBER
    tagline = "توريد نخيل ولاندسكيب وري وشبوك ضمن مدن التغطية المنشورة"
    settings_obj = None
    service_highlights = []
    contact_numbers = []
    default_keywords = ""
    default_description = ""
    default_og_image = ""
    twitter_handle = ""
    site_verifications = []
    review_summary = None

    try:
        settings_obj = SiteSettings.load()
        site_name = fix_arabic_text(settings_obj.site_name)
        phone = settings_obj.contact_phone
        whatsapp_number = settings_obj.whatsapp_number
        tagline = fix_arabic_text(settings_obj.tagline)
        service_highlights = [fix_arabic_text(item) for item in settings_obj.service_highlights_list]
        default_keywords = fix_arabic_text(settings_obj.seo_default_keywords)
        default_description = fix_arabic_text(settings_obj.seo_default_description)
        default_og_image = settings_obj.default_og_image_resolved
        twitter_handle = settings_obj.seo_twitter_handle
        site_verifications = list(SiteVerification.objects.filter(is_active=True))
        visible_reviews = Testimonial.objects.filter(is_visible=True, is_verified=True)
        review_count = visible_reviews.count()
        if review_count:
            total_rating = sum(item.rating for item in visible_reviews)
            review_summary = {
                "count": review_count,
                "rating": round(total_rating / review_count, 1),
                "items": list(visible_reviews.order_by("display_order", "-created_at")[:5]),
            }

        number_rows = list(
            ContactNumber.objects.filter(site_settings=settings_obj, is_active=True).order_by("-is_primary", "sort_order", "id")
        )
        contact_numbers = [
            {
                "label": fix_arabic_text(row.label),
                "phone": row.phone,
                "is_primary": row.is_primary,
                "enable_whatsapp": row.enable_whatsapp,
                "whatsapp_digits": row.whatsapp_digits,
            }
            for row in number_rows
        ]
        primary_number = next((row for row in contact_numbers if row["is_primary"]), None)
        selected_number = primary_number or (contact_numbers[0] if contact_numbers else None)
        if selected_number:
            phone = selected_number["phone"]
            if selected_number["enable_whatsapp"]:
                whatsapp_number = selected_number["phone"]
    except (OperationalError, ProgrammingError):
        pass

    whatsapp_digits = _to_whatsapp_digits(whatsapp_number)

    if not contact_numbers:
        contact_numbers = [
            {
                "label": "رقم التواصل",
                "phone": phone,
                "is_primary": True,
                "enable_whatsapp": True,
                "whatsapp_digits": whatsapp_digits,
            }
        ]

    if not service_highlights:
        service_highlights = ["لاندسكيب", "تصميم حدائق", "أشجار ونخيل", "شبوك", "مظلات"]

    site_url = getattr(settings, "SITE_URL", "").rstrip("/") or request.build_absolute_uri("/").rstrip("/")
    site_domain = getattr(settings, "SITE_DOMAIN", "") or request.get_host()
    if default_og_image and not default_og_image.startswith(("http://", "https://")):
        default_og_image = f"{site_url}/{default_og_image.lstrip('/')}"

    organization_schema = {
        "@context": "https://schema.org",
        "@type": getattr(settings_obj, "business_type", "LocalBusiness") or "LocalBusiness",
        "name": site_name,
        "legalName": getattr(settings_obj, "legal_name", "") or site_name,
        "url": site_url,
        "telephone": phone,
        "description": default_description,
        "sameAs": getattr(settings_obj, "same_as_list", []) if settings_obj else [],
        "areaServed": getattr(settings_obj, "area_served_list", []) if settings_obj else ["SA"],
    }
    if default_og_image:
        organization_schema["image"] = default_og_image if default_og_image.startswith("http") else f"{site_url}{default_og_image}"
    if settings_obj and (settings_obj.street_address or settings_obj.address):
        organization_schema["address"] = {
            "@type": "PostalAddress",
            "streetAddress": settings_obj.street_address or settings_obj.address,
            "addressLocality": settings_obj.address_locality,
            "addressRegion": settings_obj.address_region,
            "postalCode": settings_obj.postal_code,
            "addressCountry": settings_obj.address_country or "SA",
        }
    if settings_obj and settings_obj.latitude is not None and settings_obj.longitude is not None:
        organization_schema["geo"] = {
            "@type": "GeoCoordinates",
            "latitude": str(settings_obj.latitude),
            "longitude": str(settings_obj.longitude),
        }
    if settings_obj and settings_obj.opening_hours_list:
        organization_schema["openingHours"] = settings_obj.opening_hours_list

    defaults = {
        "organization_schema_json": safe_json_dumps(organization_schema),
        "site_name": site_name,
        "contact_phone": phone,
        "contact_numbers": contact_numbers,
        "site_tagline": tagline,
        "site_url": site_url,
        "site_domain": site_domain,
        "whatsapp_url": f"https://wa.me/{whatsapp_digits}",
        "service_highlights": service_highlights,
        "seo_default_keywords": default_keywords,
        "seo_default_description": default_description,
        "seo_default_og_image": default_og_image,
        "seo_twitter_handle": twitter_handle,
        "request_quote_label": "اطلب عرض سعر",
        "site_languages": LANGUAGES,
        "service_slugs": SERVICE_SLUGS,
        "nav_items": resolve_navigation_items(),
        "theme_css_vars": build_theme_css(settings_obj=settings_obj),
        "site_settings_obj": settings_obj,
        "site_verifications": site_verifications,
        "review_summary": review_summary,
    }
    cache.set("site:defaults", defaults, 300)
    return defaults
