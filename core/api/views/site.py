from django.db.models import Count, Prefetch, Q
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.serializers import (
    ArticleCardSerializer,
    CitySerializer,
    HomeCitySerializer,
    NavigationSerializer,
    ProjectCardSerializer,
    ServiceCardSerializer,
    SiteSettingsSerializer,
    TestimonialSerializer,
)
from core.api.utils import absolute_media_url, cap_repeated_media, clean_text, image_payload, seo_payload
from core.context_processors import resolve_navigation_items
from core.health import readiness_status
from core.models import (
    BlogCategory,
    BlogPost,
    BlogTag,
    City,
    CityServicePage,
    District,
    HomeSection,
    HomeSectionMedia,
    LegacyRedirect,
    LibraryImage,
    Page,
    Project,
    Service,
    ServiceCategory,
    SiteSettings,
    Testimonial,
)


FRONTEND_PUBLIC_MEDIA_PREFIXES = ("/videos/", "/video-posters/", "/editorial/", "/images/")


def _home_media_url(request, value):
    if not value:
        return ""
    if hasattr(value, "url"):
        try:
            value = value.url
        except (OSError, ValueError):
            return ""
    raw_value = str(value)
    if raw_value.startswith(FRONTEND_PUBLIC_MEDIA_PREFIXES):
        return raw_value
    return absolute_media_url(request, raw_value)


def _home_image_payload(request, value, alt):
    payload = image_payload(request, value, alt)
    if payload and isinstance(value, str) and value.startswith(FRONTEND_PUBLIC_MEDIA_PREFIXES):
        payload["url"] = value
    return payload


def _home_section_payload(request, section):
    items = []
    for item in getattr(section, "active_items", ()):
        items.append(
            {
                "id": item.pk,
                "media_type": item.media_type,
                "label": clean_text(item.label),
                "title": clean_text(item.title),
                "description": clean_text(item.description),
                "alt": clean_text(item.alt_text or item.title),
                "image": _home_image_payload(request, item.image or item.image_url, item.alt_text or item.title),
                "video": _home_media_url(request, item.video or item.video_url),
                "mobile_video": _home_media_url(request, item.mobile_video or item.mobile_video_url),
                "poster": _home_media_url(request, item.poster or item.poster_url),
                "link": {"label": clean_text(item.link_label), "url": item.link_url},
                "sort_order": item.sort_order,
            }
        )
    return {
        "key": section.key,
        "eyebrow": clean_text(section.eyebrow),
        "kicker": clean_text(section.kicker),
        "title": clean_text(section.title),
        "description": clean_text(section.description),
        "supporting_text": clean_text(section.supporting_text),
        "primary_cta": {"label": clean_text(section.primary_cta_label), "url": section.primary_cta_url},
        "secondary_cta": {"label": clean_text(section.secondary_cta_label), "url": section.secondary_cta_url},
        "media": {
            "image": _home_image_payload(request, section.image or section.image_url, section.media_alt or section.title),
            "video": _home_media_url(request, section.video or section.video_url),
            "mobile_video": _home_media_url(request, section.mobile_video or section.mobile_video_url),
            "poster": _home_media_url(request, section.poster or section.poster_url),
            "alt": clean_text(section.media_alt or section.title),
            "overlay_opacity": section.overlay_opacity,
        },
        "theme": section.theme,
        "sort_order": section.sort_order,
        "is_visible": section.is_visible,
        "items": items,
        "updated_at": section.updated_at.isoformat(),
    }


class HealthView(APIView):
    def get(self, request):
        return Response({"ok": True, "service": "cxa-api", "version": "v1"})


class ReadyView(APIView):
    def get(self, request):
        ready, payload = readiness_status()
        return Response(payload, status=status.HTTP_200_OK if ready else status.HTTP_503_SERVICE_UNAVAILABLE)


class SiteView(APIView):
    def get(self, request):
        settings_obj = SiteSettings.load()
        return Response(SiteSettingsSerializer(settings_obj, context={"request": request}).data)


class NavigationView(APIView):
    def get(self, request):
        items = resolve_navigation_items()
        if not items:
            items = [
                {"label": "الرئيسية", "url": "/", "new_tab": False},
                {"label": "الخدمات", "url": "/services/", "new_tab": False},
                {"label": "المشاريع", "url": "/projects/", "new_tab": False},
                {"label": "المدن", "url": "/cities/", "new_tab": False},
                {"label": "المقالات", "url": "/blog/", "new_tab": False},
                {"label": "تواصل معنا", "url": "/contact/", "new_tab": False},
            ]
        return Response(NavigationSerializer(items, many=True).data)


class HomeView(APIView):
    def get(self, request):
        settings_obj = SiteSettings.load()
        home_page = Page.objects.filter(is_visible=True, template_key="home").first()
        active_home_items = HomeSectionMedia.objects.filter(is_active=True).order_by("sort_order", "id")
        home_sections = list(
            HomeSection.objects.prefetch_related(
                Prefetch("items", queryset=active_home_items, to_attr="active_items")
            ).order_by("sort_order", "key")
        )
        section_payloads = [_home_section_payload(request, section) for section in home_sections]
        sections_by_key = {section.key: section for section in home_sections}
        hero_section = sections_by_key.get("hero")
        services = Service.objects.filter(is_visible=True).select_related(
            "category", "primary_city"
        )[:8]
        projects = Project.objects.filter(is_visible=True, record_type="portfolio").select_related(
            "city", "district", "coverage_city", "coverage_district"
        )[:8]
        active_districts = District.objects.filter(is_active=True).order_by("sort_order", "name")
        cities = list(
            City.objects.filter(is_active=True)
            .annotate(district_count=Count("districts", filter=Q(districts__is_active=True), distinct=True))
            .prefetch_related(Prefetch("districts", queryset=active_districts, to_attr="active_districts"))[:12]
        )
        articles = BlogPost.objects.filter(
            Q(status="published"), Q(publish_at__lte=timezone.now()) | Q(publish_at__isnull=True)
        ).select_related("category", "city", "district")[:6]
        testimonials = Testimonial.objects.filter(is_visible=True, is_verified=True).order_by("display_order", "-created_at")[:8]

        hero_source = (
            (hero_section.image or hero_section.image_url)
            if hero_section and (hero_section.image or hero_section.image_url)
            else settings_obj.homepage_hero_background or settings_obj.homepage_hero_background_url
        )
        if not hero_source:
            hero_record = LibraryImage.objects.filter(is_active=True, usage_group="home_hero").order_by("sort_order").first()
            hero_source = hero_record.image_url if hero_record else ""
        hero_mobile_source = (
            settings_obj.homepage_hero_mobile_background
            or settings_obj.homepage_hero_mobile_background_url
        )
        hero_title = (
            hero_section.title
            if hero_section and hero_section.title
            else home_page.hero_title if home_page and home_page.hero_title else settings_obj.homepage_meta_title
        )
        hero_text = (
            hero_section.description
            if hero_section and hero_section.description
            else home_page.intro_text if home_page and home_page.intro_text else settings_obj.homepage_meta_description
        )
        service_count = Service.objects.filter(is_visible=True).count()
        project_counts = Project.objects.filter(is_visible=True).aggregate(
            portfolio=Count("pk", filter=Q(record_type="portfolio")),
            local_solutions=Count("pk", filter=Q(record_type="local_solution")),
        )
        district_count = sum(len(getattr(city, "active_districts", ())) for city in cities)
        context = {"request": request}
        navigation = resolve_navigation_items()
        if not navigation:
            navigation = NavigationView().get(request).data
        payload = {
                "site": SiteSettingsSerializer(settings_obj, context=context).data,
                "navigation": NavigationSerializer(navigation, many=True).data,
                "hero": {
                    "eyebrow": clean_text(hero_section.eyebrow) if hero_section else "نخيل نجد",
                    "kicker": clean_text(hero_section.kicker) if hero_section else "PALMS · LANDSCAPE · SAUDI ARABIA",
                    "title": clean_text(hero_title),
                    "description": clean_text(hero_text),
                    "image": image_payload(
                        request,
                        hero_source,
                        settings_obj.homepage_hero_alt or hero_title,
                    ),
                    "mobile_image": image_payload(
                        request,
                        hero_mobile_source,
                        settings_obj.homepage_hero_alt or hero_title,
                    ),
                    "focus_x": settings_obj.homepage_hero_focus_x,
                    "focus_y": settings_obj.homepage_hero_focus_y,
                    "overlay_opacity": hero_section.overlay_opacity if hero_section else settings_obj.homepage_hero_overlay_opacity,
                    "video": _home_media_url(request, hero_section.video or hero_section.video_url) if hero_section else "",
                    "mobile_video": _home_media_url(request, hero_section.mobile_video or hero_section.mobile_video_url) if hero_section else "",
                    "poster": _home_media_url(request, hero_section.poster or hero_section.poster_url) if hero_section else "",
                    "primary_cta": {
                        "label": clean_text(hero_section.primary_cta_label) if hero_section and hero_section.primary_cta_label else "اطلب معاينة",
                        "url": hero_section.primary_cta_url if hero_section and hero_section.primary_cta_url else "/contact/",
                    },
                    "secondary_cta": {
                        "label": clean_text(hero_section.secondary_cta_label) if hero_section and hero_section.secondary_cta_label else "استعرض خدماتنا",
                        "url": hero_section.secondary_cta_url if hero_section and hero_section.secondary_cta_url else "/services/",
                    },
                },
                "sections": section_payloads,
                "services": ServiceCardSerializer(services, many=True, context=context).data,
                "projects": ProjectCardSerializer(projects, many=True, context=context).data,
                "cities": HomeCitySerializer(cities, many=True, context=context).data,
                "articles": ArticleCardSerializer(articles, many=True, context=context).data,
                "testimonials": TestimonialSerializer(testimonials, many=True).data,
                "counts": {
                    "services": Service.objects.filter(is_visible=True).count(),
                    "projects": Project.objects.filter(is_visible=True, record_type="portfolio").count(),
                    "portfolio_projects": Project.objects.filter(is_visible=True, record_type="portfolio").count(),
                    "local_solutions": Project.objects.filter(is_visible=True, record_type="local_solution").count(),
                    "cities": City.objects.filter(is_active=True).count(),
                    "districts": District.objects.filter(is_active=True, city__is_active=True).count(),
                },
                "seo": seo_payload(
                    path="/",
                    title=settings_obj.homepage_meta_title,
                    description=settings_obj.homepage_meta_description,
                    image=settings_obj.default_og_image_resolved or hero_source,
                    request=request,
                    schema={"@type": settings_obj.business_type or "LocalBusiness", "name": clean_text(settings_obj.site_name)},
                    modified_time=home_page.updated_at if home_page else settings_obj.updated_at,
                ),
            }
        response = Response(cap_repeated_media(payload))
        response["Cache-Control"] = "no-store, max-age=0"
        response["Pragma"] = "no-cache"
        return response


class TestimonialListView(APIView):
    def get(self, request):
        queryset = Testimonial.objects.filter(is_visible=True).order_by("display_order", "-created_at")
        return Response(TestimonialSerializer(queryset, many=True).data)


class RedirectListView(APIView):
    def get(self, request):
        redirects = []
        for item in LegacyRedirect.objects.filter(is_active=True).only("old_path", "target_path", "is_permanent"):
            source = item.old_path.strip()
            destination = item.target_path.strip()
            if (
                source.startswith("/")
                and not source.startswith("//")
                and destination.startswith("/")
                and not destination.startswith("//")
            ):
                redirects.append({"source": source, "destination": destination, "permanent": item.is_permanent})
        return Response(redirects)


class ToolContentView(APIView):
    def get(self, request):
        from core.views import CALCULATOR_PAGES, COMPARISON_PAGES, LEGAL_PAGES

        calculators = [{"slug": slug, **item} for slug, item in CALCULATOR_PAGES.items()]
        comparisons = [{"slug": slug, **item} for slug, item in COMPARISON_PAGES.items()]
        return Response({"calculators": calculators, "comparisons": comparisons, "legal_pages": LEGAL_PAGES})


class PublicUrlsView(APIView):
    def get(self, request):
        settings_obj = SiteSettings.load()
        items = [
            {"url": "/", "updated_at": settings_obj.updated_at, "priority": 1.0, "change_frequency": "weekly"},
            {"url": "/services/", "priority": 0.9, "change_frequency": "weekly"},
            {"url": "/projects/", "priority": 0.8, "change_frequency": "weekly"},
            {"url": "/cities/", "priority": 0.9, "change_frequency": "weekly"},
            {"url": "/districts/", "priority": 0.9, "change_frequency": "weekly"},
            {"url": "/blog/", "priority": 0.8, "change_frequency": "daily"},
            {"url": "/about/", "priority": 0.6, "change_frequency": "monthly"},
            {"url": "/contact/", "priority": 0.6, "change_frequency": "monthly"},
            {"url": "/privacy/", "priority": 0.3, "change_frequency": "yearly"},
            {"url": "/terms/", "priority": 0.3, "change_frequency": "yearly"},
            {"url": "/cost-calculator/", "priority": 0.6, "change_frequency": "monthly"},
            {"url": "/archive/", "priority": 0.4, "change_frequency": "weekly"},
            {"url": "/archive/services/", "priority": 0.4, "change_frequency": "weekly"},
            {"url": "/archive/cities/", "priority": 0.4, "change_frequency": "weekly"},
            {"url": "/archive/articles/", "priority": 0.4, "change_frequency": "daily"},
        ]

        def append(url, updated_at=None, priority=0.7, change_frequency="monthly"):
            items.append(
                {
                    "url": url,
                    "updated_at": updated_at,
                    "priority": priority,
                    "change_frequency": change_frequency,
                }
            )

        route_map = {
            "home": "/",
            "about": "/about/",
            "services": "/services/",
            "portfolio": "/projects/",
            "cities": "/cities/",
            "blog": "/blog/",
            "contact": "/contact/",
        }
        for page in Page.objects.filter(is_visible=True).only("template_key", "custom_url", "slug", "updated_at"):
            append(route_map.get(page.template_key, f"/pages/{page.resolved_path.strip('/')}/"), page.updated_at, 0.6)
        for service in Service.objects.filter(is_visible=True).only("slug", "updated_at"):
            append(f"/services/{service.slug}/", service.updated_at, 0.8)
        for category in ServiceCategory.objects.filter(services__is_visible=True).distinct().only("slug", "updated_at"):
            append(f"/services/category/{category.slug}/", category.updated_at, 0.7)
        for project in Project.objects.filter(is_visible=True, is_indexable=True).only("slug", "updated_at"):
            append(f"/projects/{project.slug}/", project.updated_at, 0.7)
        for city in City.objects.filter(is_active=True).only("slug", "updated_at"):
            append(f"/{city.slug}/", city.updated_at, 0.8)
        for district in District.objects.filter(is_active=True, city__is_active=True).select_related("city").only(
            "slug", "updated_at", "city__slug"
        ):
            append(f"/{district.city.slug}/districts/{district.slug}/", district.updated_at, 0.7)
        local_pages = CityServicePage.objects.filter(
            is_active=True,
            city__is_active=True,
            service__is_visible=True,
        ).select_related("city", "service").only(
            "custom_slug", "updated_at", "city__slug", "service__slug"
        )
        for local_page in local_pages:
            append(
                f"/{local_page.city.slug}/{local_page.custom_slug or local_page.service.slug}/",
                local_page.updated_at,
                0.8,
            )
        articles = BlogPost.objects.filter(
            Q(status="published"),
            Q(publish_at__lte=timezone.now()) | Q(publish_at__isnull=True),
        ).only("slug", "updated_at")
        for article in articles:
            append(f"/blog/{article.slug}/", article.updated_at, 0.7)
        published_categories = BlogCategory.objects.filter(posts__status="published").filter(
            Q(posts__publish_at__lte=timezone.now()) | Q(posts__publish_at__isnull=True)
        ).distinct().only("slug", "updated_at")
        for category in published_categories:
            append(f"/blog/category/{category.slug}/", category.updated_at, 0.5)
        published_tags = BlogTag.objects.filter(posts__status="published").filter(
            Q(posts__publish_at__lte=timezone.now()) | Q(posts__publish_at__isnull=True)
        ).distinct().only("slug", "updated_at")
        for tag in published_tags:
            append(f"/blog/tag/{tag.slug}/", tag.updated_at, 0.4)
        from core.views import CALCULATOR_PAGES, COMPARISON_PAGES

        for slug in CALCULATOR_PAGES:
            append(f"/cost-calculator/{slug}/", priority=0.5, change_frequency="yearly")
        for slug in COMPARISON_PAGES:
            append(f"/compare/{slug}/", priority=0.5, change_frequency="yearly")

        unique = {}
        for item in items:
            unique[item["url"]] = item
        return Response(list(unique.values()))
