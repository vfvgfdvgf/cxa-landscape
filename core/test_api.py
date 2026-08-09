from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.contrib.auth import get_user_model
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from core.models import (
    BlogCategory,
    BlogPost,
    BlogTag,
    City,
    CityServicePage,
    District,
    HomeSection,
    HomeSectionMedia,
    Lead,
    LegacyRedirect,
    Page,
    Project,
    Service,
    SiteSettings,
    Testimonial,
)
from core.middleware import SecurityHeadersMiddleware
from core.api.utils import cap_repeated_media


class MediaBudgetTests(SimpleTestCase):
    def test_repeated_media_is_limited_without_mutating_source(self):
        source = [
            {"image": {"url": "https://cdn.example.com/shared.webp?version=1"}, "video": "/videos/shared.mp4"}
            for _ in range(5)
        ]

        result = cap_repeated_media(source)

        self.assertEqual(sum(item["image"] is not None for item in result), 3)
        self.assertEqual(sum(bool(item["video"]) for item in result), 3)
        self.assertTrue(all(item["image"] is not None for item in source))


@override_settings(
    ALLOWED_HOSTS=["testserver"],
    CORS_ALLOWED_ORIGINS=["https://getsiaq.online"],
    SECURE_SSL_REDIRECT=False,
    FRONTEND_API_SECRET="test-frontend-secret",
)
class PublicApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        settings_obj = SiteSettings.load()
        settings_obj.site_name = "نخيل نجد"
        settings_obj.homepage_meta_title = "نخيل نجد لخدمات اللاندسكيب"
        settings_obj.site_logo_url = "https://res.cloudinary.com/demo/image/upload/logo.png"
        settings_obj.site_logo_alt = "شعار نخيل نجد"
        settings_obj.homepage_hero_mobile_background_url = "https://res.cloudinary.com/demo/image/upload/hero-mobile.jpg"
        settings_obj.homepage_hero_alt = "نخيل مزروع في مساحة خارجية"
        settings_obj.homepage_hero_focus_x = 64
        settings_obj.homepage_hero_focus_y = 38
        settings_obj.homepage_hero_overlay_opacity = 68
        settings_obj.save()
        hero_section = HomeSection.objects.get(key="hero")
        hero_section.overlay_opacity = 68
        hero_section.save()
        Page.objects.create(
            title="الرئيسية",
            slug="home",
            template_key="home",
            hero_title="حلول خارجية تعيش طويلًا",
            intro_text="خدمات نخيل ولاندسكيب من البيانات الحقيقية.",
        )
        cls.city = City.objects.get(slug="riyadh")
        cls.district = cls.city.districts.filter(is_active=True).first()
        cls.service = Service.objects.create(
            title="تنسيق الحدائق",
            short_title="تنسيق حدائق",
            slug="api-test-landscaping",
            description="تصميم وتنفيذ مساحات خارجية متكاملة.",
            image_url="https://res.cloudinary.com/demo/image/upload/sample.jpg",
            auto_classify=False,
            auto_distribute=False,
            is_visible=True,
        )
        cls.service.cities.add(cls.city)
        cls.local_page = CityServicePage.objects.get(city=cls.city, service=cls.service)
        cls.local_page.district = cls.district
        cls.local_page.hero_title = "تنسيق حدائق في الرياض"
        cls.local_page.content = "خدمة محلية منشورة."
        cls.local_page.custom_slug = "api-test-landscaping"
        cls.local_page.save()
        cls.project = Project.objects.create(
            title="حديقة منزلية في الرياض",
            slug="riyadh-garden",
            category="shades",
            city=cls.city,
            district=cls.district,
            description="مشروع حقيقي منشور ضمن معرض الأعمال.",
            featured_image_url="https://res.cloudinary.com/demo/image/upload/sample.jpg",
            is_visible=True,
        )
        cls.category = BlogCategory.objects.create(name="دليل الحدائق", slug="garden-guide")
        cls.article = BlogPost.objects.create(
            title="دليل تنسيق الحدائق",
            slug="garden-landscaping-guide",
            excerpt="خطوات عملية لتخطيط الحديقة.",
            content="محتوى المقال المنشور.",
            category=cls.category,
            city=cls.city,
            district=cls.district,
            status="published",
            publish_at=timezone.now(),
            auto_classify=False,
            auto_distribute=False,
        )
        cls.tag = BlogTag.objects.create(name="تنسيق حدائق", slug="garden-landscaping")
        cls.article.tags.add(cls.tag)
        BlogPost.objects.create(
            title="مسودة داخلية",
            slug="internal-draft",
            content="يجب ألا تظهر للعامة.",
            status="draft",
            auto_classify=False,
            auto_distribute=False,
        )
        Testimonial.objects.create(name="عميل موثق", review="تنفيذ منظم ودقيق.", is_visible=True, is_verified=True)

    def setUp(self):
        cache.clear()
        self.client = APIClient()

    def test_health_site_and_home_endpoints(self):
        health = self.client.get("/api/v1/health/")
        site = self.client.get("/api/v1/site/")
        home = self.client.get("/api/v1/home/")

        self.assertEqual(health.status_code, 200)
        self.assertTrue(health.data["ok"])
        self.assertEqual(site.status_code, 200)
        self.assertEqual(site.data["site_name"], "نخيل نجد")
        self.assertEqual(site.data["logo"]["alt"], "شعار نخيل نجد")
        self.assertIn("hero-mobile.jpg", site.data["hero_mobile_image"]["url"])
        self.assertEqual(site.data["hero_settings"]["focus_x"], 64)
        self.assertEqual(home.status_code, 200)
        self.assertEqual(home.data["hero"]["title"], "تنسيق حدائق\nولاندسكيب\nيصنع الفرق.")
        self.assertIn("hero-mobile.jpg", home.data["hero"]["mobile_image"]["url"])
        self.assertEqual(home.data["hero"]["overlay_opacity"], 68)
        self.assertTrue(home.data["services"])
        self.assertTrue(home.data["sections"])
        self.assertEqual(home.data["hero"]["video"], "/videos/hero-triptych.mp4")
        self.assertIn("faq", {item["key"] for item in home.data["sections"]})

    def test_homepage_cms_content_is_exposed_without_code_changes(self):
        manifesto = HomeSection.objects.get(key="manifesto")
        manifesto.title = "عنوان قابل للتحرير من لوحة التحكم"
        manifesto.description = "نص محدث ينعكس في الواجهة من خلال API."
        manifesto.save()

        response = self.client.get("/api/v1/home/")

        self.assertEqual(response.status_code, 200)
        payload = next(item for item in response.data["sections"] if item["key"] == "manifesto")
        self.assertEqual(payload["title"], "عنوان قابل للتحرير من لوحة التحكم")
        self.assertEqual(payload["description"], "نص محدث ينعكس في الواجهة من خلال API.")

    def test_home_media_repetition_is_blocked_after_three_placements(self):
        gallery = HomeSection.objects.get(key="gallery")
        shared_source = "/editorial/gallery/shared-quality-check.webp"
        for index in range(3):
            item = HomeSectionMedia(
                section=gallery,
                media_type="image",
                title=f"عنصر اختبار {index}",
                image_url=shared_source,
            )
            item.full_clean()
            item.save()

        fourth = HomeSectionMedia(
            section=gallery,
            media_type="image",
            title="عنصر رابع مكرر",
            image_url=shared_source,
        )
        with self.assertRaises(ValidationError):
            fourth.full_clean()

    def test_home_media_upload_and_url_cannot_be_selected_together(self):
        gallery = HomeSection.objects.get(key="gallery")
        item = HomeSectionMedia(
            section=gallery,
            media_type="image",
            title="مصدران للصورة",
            image="home-sections/items/images/example.webp",
            image_url="/editorial/gallery/example.webp",
        )
        with self.assertRaises(ValidationError):
            item.full_clean()

    def test_service_list_never_returns_one_image_more_than_three_times(self):
        source = "https://res.cloudinary.com/demo/image/upload/repeated-list-image.jpg"
        for index in range(5):
            Service.objects.create(
                title=f"خدمة متكررة {index}",
                slug=f"repeated-media-service-{index}",
                description="خدمة لاختبار ميزانية الوسائط.",
                image_url=source,
                auto_classify=False,
                auto_distribute=False,
                is_visible=True,
            )

        response = self.client.get("/api/v1/services/", {"page_size": 24})
        repeated = [
            item["image"]["url"]
            for item in response.data["results"]
            if item.get("image") and "repeated-list-image.jpg" in item["image"]["url"]
        ]
        self.assertEqual(len(repeated), 3)

    def test_frontend_origin_receives_cors_headers(self):
        response = self.client.get(
            "/api/v1/health/",
            HTTP_ORIGIN="https://getsiaq.online",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Access-Control-Allow-Origin"], "https://getsiaq.online")

    def test_static_images_allow_cross_origin_frontend_embedding(self):
        request = RequestFactory().get("/static/project-14.webp")
        response = SecurityHeadersMiddleware(lambda _request: HttpResponse())(request)

        self.assertEqual(response["Cross-Origin-Resource-Policy"], "cross-origin")

    def test_content_lists_and_details_use_published_records(self):
        checks = [
            ("/api/v1/services/", self.service.slug),
            ("/api/v1/projects/", self.project.slug),
            ("/api/v1/cities/", self.city.slug),
            ("/api/v1/blog/", self.article.slug),
        ]
        for url, slug in checks:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertIn(slug, [item["slug"] for item in response.data["results"]])

        detail_urls = [
            f"/api/v1/services/{self.service.slug}/",
            f"/api/v1/projects/{self.project.slug}/",
            f"/api/v1/cities/{self.city.slug}/",
            f"/api/v1/cities/{self.city.slug}/districts/{self.district.slug}/",
            f"/api/v1/blog/{self.article.slug}/",
        ]
        for url in detail_urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

        articles = self.client.get("/api/v1/blog/").data["results"]
        self.assertNotIn("internal-draft", [item["slug"] for item in articles])
        self.assertEqual(self.client.get("/api/v1/blog/internal-draft/").status_code, 404)
        self.assertEqual(self.client.get("/api/v1/services/does-not-exist/").status_code, 404)

    def test_district_index_supports_city_filter_and_search(self):
        response = self.client.get(
            "/api/v1/districts/",
            {"city": self.city.slug, "q": self.district.name, "page_size": 24},
        )

        self.assertEqual(response.status_code, 200)
        self.assertGreater(response.data["count"], 0)
        self.assertTrue(all(item["city"]["slug"] == self.city.slug for item in response.data["results"]))
        self.assertIn(self.district.slug, [item["slug"] for item in response.data["results"]])

    def test_local_static_images_expose_responsive_variants(self):
        self.service.image_url = "/static/project-01.webp"
        self.service.save(update_fields=["image_url", "updated_at"])
        image = self.client.get(f"/api/v1/services/{self.service.slug}/").data["image"]

        self.assertTrue(image["url"].startswith("https://"))
        self.assertTrue(image["width"])
        self.assertTrue(image["height"])
        self.assertTrue(image["variants"])
        self.assertTrue(all(item["url"].startswith("https://") for item in image["variants"]))

    def test_local_service_routes_and_absolute_image_urls(self):
        city_url = f"/api/v1/cities/{self.city.slug}/services/{self.service.slug}/"
        district_url = (
            f"/api/v1/cities/{self.city.slug}/districts/{self.district.slug}/"
            f"services/{self.service.slug}/"
        )
        self.assertEqual(self.client.get(city_url).status_code, 200)
        self.assertEqual(self.client.get(district_url).status_code, 200)
        service = self.client.get(f"/api/v1/services/{self.service.slug}/").data
        self.assertTrue(service["image"]["url"].startswith("https://"))

    def test_hidden_services_are_excluded_from_local_content(self):
        self.service.is_visible = False
        self.service.save(update_fields=["is_visible", "updated_at"])

        city = self.client.get(f"/api/v1/cities/{self.city.slug}/").data
        district = self.client.get(
            f"/api/v1/cities/{self.city.slug}/districts/{self.district.slug}/"
        ).data
        local_url = f"/api/v1/cities/{self.city.slug}/services/{self.service.slug}/"

        self.assertNotIn(self.service.slug, [item["service"]["slug"] for item in city["services"]])
        self.assertNotIn(self.service.slug, [item["service"]["slug"] for item in district["services"]])
        self.assertEqual(self.client.get(local_url).status_code, 404)

    def test_rich_content_is_sanitized_at_the_api_boundary(self):
        Page.objects.create(
            title="صفحة آمنة",
            slug="safe-page",
            template_key="custom",
            body='<h2>عنوان مفيد</h2><script>alert("unsafe")</script>',
        )
        response = self.client.get("/api/v1/pages/safe-page/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("<h2>عنوان مفيد</h2>", response.data["body"])
        self.assertNotIn("<script", response.data["body"])

    def test_read_endpoints_do_not_accept_content_writes(self):
        response = self.client.post("/api/v1/services/", {"title": "غير مسموح"}, format="json")
        self.assertEqual(response.status_code, 405)

    def test_submission_requires_valid_server_secret(self):
        payload = {
            "name": "محمد علي",
            "phone": "0551234567",
            "email": "client@example.com",
            "city": "الرياض",
            "district": "حي النخيل",
            "service": "تنسيق الحدائق",
            "message": "أرغب في معاينة الموقع وتقدير نطاق العمل.",
            "privacy_consent": True,
            "company": "",
            "page_url": "https://getsiaq.online/contact/",
        }
        self.assertEqual(self.client.post("/api/v1/contact/", payload, format="json").status_code, 403)
        self.client.credentials(HTTP_X_FRONTEND_SECRET="wrong-secret")
        self.assertEqual(self.client.post("/api/v1/contact/", payload, format="json").status_code, 403)
        self.client.credentials(HTTP_X_FRONTEND_SECRET="test-frontend-secret")
        response = self.client.post("/api/v1/contact/", payload, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertTrue(Lead.objects.filter(phone="0551234567").exists())

        invalid_payload = {**payload, "phone": "123", "privacy_consent": False}
        self.assertEqual(self.client.post("/api/v1/contact/", invalid_payload, format="json").status_code, 400)
        self.assertEqual(
            self.client.post("/api/v1/contact/", {**payload, "company": "bot"}, format="json").status_code,
            400,
        )

    def test_submission_throttle_isolated_by_frontend_client_identifier(self):
        self.client.credentials(
            HTTP_X_FRONTEND_SECRET="test-frontend-secret",
            HTTP_X_SUBMISSION_CLIENT="visitor-a",
        )
        payload = {
            "name": "محمد علي",
            "phone": "0551234567",
            "message": "أرغب في معاينة الموقع وتقدير نطاق العمل.",
            "privacy_consent": True,
            "company": "",
        }
        for _ in range(10):
            self.assertEqual(self.client.post("/api/v1/contact/", payload, format="json").status_code, 201)
        self.assertEqual(self.client.post("/api/v1/contact/", payload, format="json").status_code, 429)

        self.client.credentials(
            HTTP_X_FRONTEND_SECRET="test-frontend-secret",
            HTTP_X_SUBMISSION_CLIENT="visitor-b",
        )
        self.assertEqual(self.client.post("/api/v1/contact/", payload, format="json").status_code, 201)

    def test_page_custom_url_rejects_multi_segment_or_query_values(self):
        for custom_url in ("offers/summer", "offers?ref=1", "https://example.com/path", "offers#top"):
            page = Page(title="صفحة اختبار", slug=f"test-{abs(hash(custom_url))}", template_key="custom", custom_url=custom_url)
            with self.subTest(custom_url=custom_url), self.assertRaises(ValidationError):
                page.full_clean()

    def test_quote_request_details_are_saved_without_new_models(self):
        self.client.credentials(HTTP_X_FRONTEND_SECRET="test-frontend-secret")
        payload = {
            "name": "سارة محمد",
            "phone": "0557654321",
            "email": "sara@example.com",
            "city": self.city.name,
            "district": self.district.name,
            "service": self.service.title,
            "project_area": "350 متر مربع",
            "budget": "50,000 - 80,000 ريال",
            "preferred_contact_time": "مساءً (4 - 8)",
            "message": "أرغب في معاينة الموقع وإعداد عرض سعر تفصيلي.",
            "privacy_consent": True,
            "company": "",
            "page_url": "https://getsiaq.online/quote-request/",
        }
        response = self.client.post("/api/v1/quote-request/", payload, format="json")

        self.assertEqual(response.status_code, 201)
        lead = Lead.objects.get(phone="0557654321")
        self.assertIn("مساحة المشروع: 350 متر مربع", lead.notes)
        self.assertIn("الميزانية التقريبية: 50,000 - 80,000 ريال", lead.notes)
        self.assertIn("الوقت المفضل للتواصل: مساءً (4 - 8)", lead.notes)

    def test_public_url_inventory_and_backend_noindex_header(self):
        response = self.client.get("/api/v1/public-urls/")
        urls = {item["url"] for item in response.data}
        self.assertIn(f"/services/{self.service.slug}/", urls)
        self.assertIn(f"/{self.city.slug}/districts/{self.district.slug}/", urls)
        self.assertIn("/districts/", urls)
        self.assertIn("/about/", urls)
        self.assertIn("/archive/services/", urls)
        self.assertIn("/archive/cities/", urls)
        self.assertIn("/archive/articles/", urls)
        self.assertIn(f"/blog/category/{self.category.slug}/", urls)
        self.assertIn(f"/blog/tag/{self.tag.slug}/", urls)
        self.assertNotIn("onrender.com", "".join(urls))
        self.assertEqual(response["X-Robots-Tag"], "noindex, nofollow, noarchive")

    def test_legacy_redirects_cannot_leave_the_site(self):
        LegacyRedirect.objects.create(
            old_path="/unsafe-old/",
            target_path="//evil.example/path",
            is_active=True,
            is_permanent=True,
        )
        response = self.client.get("/unsafe-old/")

        self.assertEqual(response.status_code, 404)
        self.assertNotIn("Location", response)


@override_settings(ALLOWED_HOSTS=["testserver"], SECURE_SSL_REDIRECT=False)
class HomepageAdminTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="cms-auditor",
            email="audit@example.com",
            password="strong-test-password",
        )
        self.client.force_login(self.user)

    def test_homepage_cms_dashboard_and_edit_screens_open(self):
        hero = HomeSection.objects.get(key="hero")
        urls = (
            "/admin/",
            "/admin/core/homesection/",
            f"/admin/core/homesection/{hero.pk}/change/",
            "/admin/core/homesectionmedia/",
        )
        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)

        dashboard = self.client.get("/admin/").content.decode("utf-8")
        self.assertIn("أقسام الصفحة الرئيسية", dashboard)
        self.assertIn("عناصر أقسام الرئيسية", dashboard)
