import os
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.staticfiles import finders
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.test import Client, RequestFactory, SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.db.models.deletion import ProtectedError

from .ai_content import _get_ai_api_url, request_tokenmix_generation
from .local_seo import ensure_local_service_pages, seed_default_cities_and_services, sync_fixed_city_catalog
from .middleware import LegacyRedirectMiddleware
from .models import City, CityServicePage, District, LibraryImage, Project, ProjectImage, Service, SiteSettings, normalize_image_field_name, validate_image_source


@override_settings(DEBUG=True, ALLOWED_HOSTS=["localhost", "testserver"], SECURE_SSL_REDIRECT=False)
class PublicPageSmokeTests(TestCase):
    def setUp(self):
        self.client = Client(HTTP_HOST="localhost")
        seed_default_cities_and_services()
        ensure_local_service_pages()

    def test_public_pages_load(self):
        urls = [
            reverse("home"),
            reverse("about"),
            reverse("services"),
            reverse("portfolio"),
            reverse("cities"),
            reverse("blog"),
            reverse("contact"),
            reverse("privacy"),
            reverse("terms"),
            reverse("robots_txt"),
            reverse("sitemap_xml"),
            reverse("city_detail", kwargs={"city_slug": "riyadh"}),
        ]
        landscaping = Service.objects.get(slug="landscaping")
        urls.append(
            reverse(
                "city_service_detail",
                kwargs={"city_slug": landscaping.primary_city.slug, "service_slug": landscaping.slug},
            )
        )

        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)


@override_settings(SECURE_SSL_REDIRECT=False)
class LibraryImageDatabaseStorageTests(TestCase):
    def test_library_image_can_be_served_from_database(self):
        item = LibraryImage.objects.create(
            source_name="sample.jpg",
            title="Sample",
            image_data=b"image-bytes",
            image_stored=True,
            image_content_type="image/jpeg",
            image_filename="sample.jpg",
        )

        response = self.client.get(item.image_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/jpeg")
        self.assertEqual(response.content, b"image-bytes")


class ProjectConfigurationTests(SimpleTestCase):
    def test_sqlite_is_the_local_fallback_database(self):
        self.assertEqual(settings.DATABASES["default"]["ENGINE"], "django.db.backends.sqlite3")

    def test_root_image_assets_are_available_to_staticfiles(self):
        for sample_image in ("project-01.webp", "project-53.webp", "hero-desktop.webp", "hero-mobile.webp"):
            with self.subTest(sample_image=sample_image):
                self.assertIsNotNone(finders.find(sample_image))

    def test_site_identity_image_sources_accept_only_public_safe_paths(self):
        for value in (
            "/static/hero-mobile.webp",
            "/media/site-settings/logo.png",
            "https://res.cloudinary.com/demo/image/upload/logo.png",
        ):
            with self.subTest(value=value):
                self.assertIsNone(validate_image_source(value))

        for value in ("http://example.com/logo.png", "javascript:alert(1)", "../private/logo.png"):
            with self.subTest(value=value):
                with self.assertRaises(ValidationError):
                    validate_image_source(value)

    def test_owner_media_catalog_has_unique_complete_entries(self):
        from .project_media import HERO_DESKTOP, HERO_MOBILE, PROJECT_MEDIA

        self.assertEqual(len(PROJECT_MEDIA), 93)
        self.assertEqual(len({item["filename"] for item in PROJECT_MEDIA}), 93)
        self.assertEqual(HERO_DESKTOP, "hero-desktop.webp")
        self.assertEqual(HERO_MOBILE, "hero-mobile.webp")
        self.assertTrue(all(item["title"] and item["description"] and item["alt"] for item in PROJECT_MEDIA))

    def test_library_image_paths_are_normalized(self):
        self.assertEqual(
            normalize_image_field_name(
                "/media/library-images/library-images/IMG-20260407-WA0000.jpg",
                "library-images",
            ),
            "library-images/IMG-20260407-WA0000.jpg",
        )

from datetime import timedelta

from django.core.cache import cache
from django.core.management import call_command
from django.core.exceptions import ValidationError
from django.utils import timezone

from .html_utils import sanitize_html
from .models import BlogPost, Lead, NavigationItem


@override_settings(
    DEBUG=True,
    ALLOWED_HOSTS=["localhost", "testserver"],
    SECURE_SSL_REDIRECT=False,
    SITE_URL="https://getsiaq.online",
)
class SecuritySeoAndNavigationTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = Client(HTTP_HOST="localhost", HTTP_USER_AGENT="Nakheel-Najd-tests")

    def test_health_endpoint_is_lightweight(self):
        with (
            patch.dict(os.environ, {}, clear=False),
            patch("core.middleware.cache.get", side_effect=AssertionError("health must not read cache")),
            patch(
                "core.models.LegacyRedirect.objects.filter",
                side_effect=AssertionError("health must not query the database"),
            ),
        ):
            os.environ.pop("REDIS" + "_URL", None)
            response = self.client.get(reverse("health"))

        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {"status": "ok"})

    def test_redirect_middleware_continues_when_cache_operations_fail(self):
        request = RequestFactory().get("/missing-legacy-path/")
        middleware = LegacyRedirectMiddleware(lambda _request: HttpResponse("ok"))

        with (
            patch("core.middleware.cache.get", side_effect=RuntimeError("cache read failed")),
            patch("core.middleware.cache.set", side_effect=RuntimeError("cache write failed")),
        ):
            response = middleware(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"ok")

    def test_canonical_drops_tracking_query_parameters(self):
        response = self.client.get(f'{reverse("about")}?utm_source=test&gclid=123')
        self.assertContains(response, '<link rel="canonical" href="https://getsiaq.online/about/">', html=True)
        self.assertNotContains(response, "utm_source")

    def test_custom_404_is_noindex(self):
        response = self.client.get("/this-page-does-not-exist/too/deep/")
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, 'content="noindex, nofollow"', status_code=404)

    def test_local_fast_navigation_is_present_without_external_swup(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, 'id="swup"')
        self.assertContains(response, "js/site-v4-4.js")
        self.assertContains(response, "css/site-v4-4.css")
        self.assertContains(response, 'class="nn-brand-marquee"')
        self.assertContains(response, "hero-desktop.webp")
        self.assertContains(response, "hero-mobile.webp")
        self.assertNotContains(response, "unpkg.com/swup")

    def test_html_sanitizer_removes_script_and_event_handlers(self):
        cleaned = sanitize_html(
            '<p onclick="alert(1)">نص</p><script>alert(1)</script>'
            '<a href="javascript:alert(1)">رابط</a>'
        )
        self.assertIn("<p>نص</p>", cleaned)
        self.assertNotIn("script", cleaned.lower())
        self.assertNotIn("onclick", cleaned.lower())
        self.assertNotIn("javascript:", cleaned.lower())

    def test_html_sanitizer_accepts_source_rel_without_nh3_conflict(self):
        cleaned = sanitize_html(
            '<a href="https://example.com" target="_blank" rel="noopener nofollow">مرجع</a>'
        )
        self.assertIn('href="https://example.com"', cleaned)
        self.assertIn("noopener", cleaned)
        self.assertIn("noreferrer", cleaned)
        self.assertNotIn("nofollow", cleaned)

    def test_future_posts_are_excluded_from_blog_sitemap(self):
        future = BlogPost.objects.create(
            title="مقال مستقبلي",
            slug="future-post",
            content="<p>محتوى</p>",
            status="published",
            publish_at=timezone.now() + timedelta(days=1),
        )
        past = BlogPost.objects.create(
            title="مقال منشور",
            slug="published-post",
            content="<p>محتوى</p>",
            status="published",
            publish_at=timezone.now() - timedelta(days=1),
        )
        response = self.client.get(reverse("sitemap_blog_xml"))
        body = response.content.decode()
        self.assertNotIn(future.slug, body)
        self.assertIn(past.slug, body)

    def test_invalid_phone_is_rejected(self):
        response = self.client.post(reverse("capture_lead"), {"name": "اختبار", "phone": "abc"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "invalid_phone")

    def test_phone_with_no_digits_is_rejected(self):
        response = self.client.post(reverse("capture_lead"), {"name": "اختبار", "phone": "------"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "invalid_phone")

    def test_lead_honeypot_is_silently_ignored(self):
        before = Lead.objects.count()
        response = self.client.post(
            reverse("capture_lead"),
            {"name": "Bot", "phone": "+966500000000", "website": "https://spam.invalid"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {"ok": True})
        self.assertEqual(Lead.objects.count(), before)

    def test_tracking_endpoints_reject_get_requests(self):
        self.assertEqual(self.client.get(reverse("capture_lead")).status_code, 405)
        self.assertEqual(self.client.get(reverse("track_conversion")).status_code, 405)

    def test_read_tracking_requires_post_and_deduplicates(self):
        post = BlogPost.objects.create(
            title="اختبار قراءة",
            slug="read-test",
            content="<p>محتوى</p>",
            status="published",
            publish_at=timezone.now() - timedelta(minutes=1),
        )
        url = reverse("blog_track_read", kwargs={"post_slug": post.slug})
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertEqual(self.client.post(url, {"seconds": "40"}).status_code, 200)
        self.assertEqual(self.client.post(url, {"seconds": "40"}).status_code, 200)
        post.refresh_from_db()
        self.assertEqual(post.total_read_seconds, 40)

    def test_navigation_item_requires_exactly_one_target(self):
        with self.assertRaises(ValidationError):
            NavigationItem(label="بدون رابط").full_clean()
        with self.assertRaises(ValidationError):
            NavigationItem(label="رابطان", route_name="home", external_url="https://example.com").full_clean()
        NavigationItem(label="الرئيسية", route_name="home").full_clean()

    def test_blog_pagination_has_unique_canonical_and_navigation_links(self):
        for index in range(14):
            BlogPost.objects.create(
                title=f"مقال {index}",
                slug=f"post-{index}",
                content="<p>محتوى</p>",
                status="published",
                publish_at=timezone.now() - timedelta(minutes=index + 1),
            )
        response = self.client.get(f'{reverse("blog")}?page=2&utm_source=ignored')
        self.assertContains(response, 'href="https://getsiaq.online/blog/?page=2"')
        self.assertContains(response, 'rel="prev" href="https://getsiaq.online/blog/"')
        self.assertNotContains(response, "utm_source=ignored")

    def test_lead_captures_attribution_for_crm(self):
        response = self.client.post(
            reverse("capture_lead"),
            {
                "name": "عميل اختبار",
                "phone": "+966500000000",
                "city": "الرياض",
                "service": "تنسيق حدائق",
                "page_url": "https://getsiaq.online/services/",
                "utm_source": "google",
                "utm_medium": "cpc",
                "utm_campaign": "summer-landscape",
            },
        )
        self.assertEqual(response.status_code, 200)
        lead = Lead.objects.get(pk=response.json()["lead_id"])
        self.assertEqual(lead.source, "website")
        self.assertEqual(lead.page_url, "https://getsiaq.online/services/")
        self.assertEqual(lead.utm_source, "google")
        self.assertEqual(lead.utm_campaign, "summer-landscape")



@override_settings(SECURE_SSL_REDIRECT=False)
class LocationAndTaxonomyAutomationTests(TestCase):
    def setUp(self):
        sync_fixed_city_catalog()

    def test_fixed_catalog_and_location_endpoint_are_available(self):
        self.assertEqual(City.objects.filter(is_system=True).count(), 12)
        self.assertEqual(District.objects.filter(is_system=True).count(), 330)
        response = self.client.get(reverse("location_options_json"))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload), 12)
        self.assertTrue(all(item["districts"] for item in payload))

    def test_fixed_city_and_district_cannot_be_deleted(self):
        city = City.objects.get(slug="riyadh")
        district = city.districts.first()

        with self.assertRaises(ProtectedError):
            city.delete()
        with self.assertRaises(ProtectedError):
            City.objects.filter(pk=city.pk).delete()
        with self.assertRaises(ProtectedError):
            district.delete()

    def test_project_selects_district_when_only_city_is_chosen(self):
        city = City.objects.get(slug="riyadh")
        project = Project.objects.create(
            title="حديقة منزلية",
            slug="automatic-district-project",
            category="shades",
            city=city,
            description="تنسيق حديقة منزلية في الرياض",
        )
        self.assertIsNotNone(project.district_id)
        self.assertEqual(project.district.city_id, city.pk)

    def test_blog_post_creates_taxonomy_and_location_automatically(self):
        post = BlogPost.objects.create(
            title="دليل زراعة النخيل والري",
            slug="automatic-blog-taxonomy",
            excerpt="نصائح لزراعة النخيل",
            content="<p>دليل زراعة النخيل وتركيب شبكات الري.</p>",
        )
        post.refresh_from_db()
        self.assertIsNotNone(post.category_id)
        self.assertIsNotNone(post.city_id)
        self.assertIsNotNone(post.district_id)
        self.assertEqual(post.district.city_id, post.city_id)
        self.assertTrue(post.tags.exists())

    def test_service_creates_taxonomy_location_tags_and_local_page(self):
        service = Service.objects.create(
            title="صيانة شبكات الري",
            slug="automatic-service-taxonomy",
            description="صيانة شبكات الري والتسميد للحدائق",
        )
        service.refresh_from_db()
        self.assertIsNotNone(service.category_id)
        self.assertIsNotNone(service.primary_city_id)
        self.assertIsNotNone(service.primary_district_id)
        self.assertEqual(service.primary_district.city_id, service.primary_city_id)
        self.assertTrue(service.tags.exists())
        self.assertTrue(service.cities.filter(pk=service.primary_city_id).exists())
        self.assertTrue(service.city_pages.filter(city_id=service.primary_city_id).exists())

    def test_city_service_page_selects_a_district_automatically(self):
        city = City.objects.get(slug="riyadh")
        service = Service.objects.create(
            title="توريد نخيل ملوكي",
            slug="royal-palms-district-test",
            description="توريد وزراعة نخيل ملوكي للمداخل والحدائق.",
            auto_classify=False,
            auto_distribute=False,
        )
        page = CityServicePage.objects.create(
            city=city,
            service=service,
            content="<p>خدمة محلية في مدينة الرياض.</p>",
        )
        self.assertIsNotNone(page.district_id)
        self.assertEqual(page.district.city_id, city.pk)

    def test_district_page_lists_its_projects_and_has_local_seo(self):
        city = City.objects.get(slug="riyadh")
        district = city.districts.first()
        project = Project.objects.create(
            title="مشروع نخيل داخل الحي",
            slug="district-page-project",
            category="palm",
            city=city,
            district=district,
            description="توريد وزراعة نخيل داخل الحي.",
        )
        response = self.client.get(
            reverse("district_detail", kwargs={"city_slug": city.slug, "district_slug": district.slug})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, project.title)
        self.assertContains(response, f"حي {district.name}")
        self.assertContains(response, "نخيل نجد")

    def test_district_sitemap_contains_fixed_district_pages(self):
        city = City.objects.get(slug="riyadh")
        district = city.districts.first()
        response = self.client.get(reverse("sitemap_districts_xml"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            reverse("district_detail", kwargs={"city_slug": city.slug, "district_slug": district.slug}),
        )


class UnicodeSlugRoutingTests(SimpleTestCase):
    def test_district_route_accepts_arabic_slug(self):
        url = reverse(
            "district_detail",
            kwargs={"city_slug": "khobar", "district_slug": "الخبر-الشمالية"},
        )
        self.assertEqual(url, "/khobar/districts/%D8%A7%D9%84%D8%AE%D8%A8%D8%B1-%D8%A7%D9%84%D8%B4%D9%85%D8%A7%D9%84%D9%8A%D8%A9/")

    def test_blog_taxonomy_routes_accept_arabic_slugs(self):
        category_url = reverse("blog_category", kwargs={"category_slug": "العناية-بالنخيل"})
        tag_url = reverse("blog_tag", kwargs={"tag_slug": "تنسيق-حدائق"})
        self.assertIn("/blog/category/", category_url)
        self.assertIn("/blog/tag/", tag_url)



class TokenMixCompatibilityTests(SimpleTestCase):
    @patch.dict(
        "os.environ",
        {
            "TOKENMIX_API_KEY": "test-token",
            "TOKENMIX_BASE_URL": "https://api.tokenmix.ai/v1",
            "TOKENMIX_MODEL": "gpt-4o-mini",
        },
        clear=False,
    )
    def test_tokenmix_uses_openai_compatible_chat_completions(self):
        self.assertEqual(_get_ai_api_url(), "https://api.tokenmix.ai/v1/chat/completions")

        form = SimpleNamespace(
            cleaned_data={
                "content_type": "service",
                "mode": "create",
                "object_id": None,
                "title_hint": "تنسيق حدائق",
                "prompt": "أنشئ خدمة تنسيق حدائق",
                "blog_category": None,
                "blog_tags": "",
                "city": None,
                "service": None,
                "page_template_key": "",
            }
        )
        response = Mock()
        response.status_code = 200
        response.json.return_value = {
            "id": "chatcmpl-test",
            "choices": [{"message": {"content": '{"title":"تنسيق حدائق","slug":"garden-design","description":"وصف"}'}}],
        }

        with patch("core.ai_content.requests.post", return_value=response) as mocked_post:
            payload, meta, _ = request_tokenmix_generation(form, [])

        self.assertEqual(payload["title"], "تنسيق حدائق")
        self.assertEqual(meta["provider"], "TokenMix")
        request_kwargs = mocked_post.call_args.kwargs
        self.assertEqual(request_kwargs["json"]["model"], "gpt-4o-mini")
        self.assertEqual(request_kwargs["json"]["response_format"], {"type": "json_object"})
        self.assertEqual(request_kwargs["headers"]["Authorization"], "Bearer test-token")


@override_settings(SECURE_SSL_REDIRECT=False)
class BootstrapNakheelNajdRegressionTests(TestCase):
    def test_bootstrap_resolves_legacy_slug_and_is_idempotent(self):
        from core.management.commands import bootstrap_nakheel_najd as bootstrap_module
        from core.nakheel_content import ARTICLE_TOPICS, SERVICE_SPECS

        sync_fixed_city_catalog()
        city = City.objects.get(slug="riyadh")
        district = city.districts.first()
        target_spec = SERVICE_SPECS[0]
        legacy_service = Service.objects.create(
            title="خدمة قديمة",
            slug="legacy-service-collision-test",
            description="صفحة قديمة لا يجب حذفها.",
            auto_classify=False,
            auto_distribute=False,
        )
        legacy_page = CityServicePage.objects.create(
            city=city,
            district=district,
            service=legacy_service,
            custom_slug=target_spec.slug,
            content='<p><a href="https://example.com" rel="noopener nofollow">مرجع قديم</a></p>',
        )
        legacy_post = BlogPost.objects.create(
            title="مقال بصورة قديمة",
            slug="legacy-post-image-test",
            content="<p>محتوى قديم</p>",
            featured_image_url="https://example.com/old-article.jpg",
        )
        legacy_project = Project.objects.create(
            title="مشروع بصورة قديمة",
            slug="legacy-project-image-test",
            category="palm",
            city=city,
            district=district,
            description="مشروع اختبار",
            featured_image_url="https://example.com/old-project.jpg",
        )
        ProjectImage.objects.create(
            project=legacy_project,
            title="صورة معرض قديمة",
            external_url="https://example.com/old-gallery.jpg",
        )

        with patch.object(bootstrap_module, "SERVICE_SPECS", (target_spec,)), patch.object(
            bootstrap_module, "ALL_SERVICE_SPECS", (target_spec,)
        ), patch.object(bootstrap_module, "ARTICLE_TOPICS", (ARTICLE_TOPICS[0],)):
            call_command("bootstrap_nakheel_najd")
            call_command("bootstrap_nakheel_najd")

        legacy_page.refresh_from_db()
        self.assertNotEqual(legacy_page.custom_slug, target_spec.slug)
        generated_service = Service.objects.get(slug=target_spec.slug)
        self.assertEqual(
            CityServicePage.objects.filter(city=city, service=generated_service).count(),
            1,
        )
        self.assertEqual(
            BlogPost.objects.filter(slug__startswith="nakheel-najd-").count(),
            City.objects.filter(is_active=True, is_system=True).count(),
        )
        self.assertEqual(Project.objects.filter(slug__startswith="nakheel-najd-project-").count(), 93)
        self.assertEqual(Project.objects.filter(slug__startswith="nakheel-najd-project-", city__isnull=True).count(), 93)
        self.assertEqual(Project.objects.filter(slug__startswith="nakheel-najd-project-", district__isnull=True).count(), 93)
        legacy_post.refresh_from_db()
        legacy_project.refresh_from_db()
        self.assertTrue(legacy_post.featured_image_url.startswith("/static/project-"))
        self.assertTrue(legacy_project.featured_image_url.startswith("/static/project-"))
        self.assertFalse(ProjectImage.objects.filter(project=legacy_project).exists())
        site_settings = SiteSettings.load()
        self.assertEqual(site_settings.homepage_hero_background_url, "/static/hero-desktop.webp")
        self.assertEqual(site_settings.default_og_image_url, "/static/hero-desktop.webp")


class EnsureAdminUserCommandTests(TestCase):
    def test_refuses_to_create_admin_without_password(self):
        username = "admin-without-password"
        with patch.dict(
            os.environ,
            {"DJANGO_SUPERUSER_USERNAME": username, "DJANGO_SUPERUSER_PASSWORD": ""},
            clear=False,
        ):
            call_command("ensure_admin_user")

        self.assertFalse(get_user_model().objects.filter(username=username).exists())

    def test_creates_admin_with_usable_password(self):
        username = "deployment-admin"
        password = "test-only-strong-password"
        with patch.dict(
            os.environ,
            {"DJANGO_SUPERUSER_USERNAME": username, "DJANGO_SUPERUSER_PASSWORD": password},
            clear=False,
        ):
            call_command("ensure_admin_user")

        user = get_user_model().objects.get(username=username)
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.check_password(password))
