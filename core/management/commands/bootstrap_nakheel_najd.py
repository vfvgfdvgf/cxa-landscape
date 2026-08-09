from __future__ import annotations

from datetime import timedelta
import hashlib

from django.core.management import BaseCommand, CommandError, call_command
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.text import slugify

from core.models import (
    BlogCategory,
    BlogPost,
    BlogTag,
    City,
    CityServicePage,
    ContactNumber,
    LibraryImage,
    Page,
    PageMedia,
    Project,
    ProjectImage,
    Service,
    ServiceCategory,
    ServiceTag,
    SiteSettings,
)
from core.nakheel_content import (
    ALL_SERVICE_SPECS,
    ARTICLE_TOPICS,
    SERVICE_SPECS,
    article_html,
    service_catalog_html,
    service_meta_description,
    service_page_html,
)
from core.project_media import IMAGE_GROUPS, PROJECT_MEDIA


BRAND_NAME = "نخيل نجد"
PHONE = "0554882724"

CATEGORY_SLUGS = {
    "النخيل والأشجار": "palms-trees",
    "تصميم الحدائق": "garden-design",
    "الري والصيانة": "irrigation-maintenance",
    "اللاندسكيب": "landscape",
    "المظلات والشبوك": "shades-fencing",
    "دليل وتكاليف": "guides-costs",
    "تصميم وتنفيذ الحدائق": "garden-design-build",
    "النخيل والتشجير": "palms-planting",
    "اللاندسكيب الصلب": "hardscape",
}

SOURCE_TAGS = {
    "palm": "النخيل",
    "weevil": "صحة النخيل",
    "irrigation": "الري",
    "landscape": "اللاندسكيب",
    "fence": "الشبوك والتسوير",
}

# Eight local decision-aid records per city. These reuse owner-supplied imagery,
# are clearly labelled as local solution models, and stay noindex to avoid SEO duplication.
LOCAL_SOLUTION_CATEGORIES = (
    "palm", "fencing", "traditional", "shades",
    "palm", "traditional", "fencing", "shades",
)


def unicode_slug(value: str, fallback: str) -> str:
    clean = slugify(value, allow_unicode=True)[:130]
    if clean:
        return clean
    digest = hashlib.sha1((value or fallback).encode("utf-8")).hexdigest()[:12]
    return f"{fallback[:115]}-{digest}"


class Command(BaseCommand):
    help = (
        "Apply Nakheel Najd branding, seed a 250-service nationwide catalogue, "
        "50 strong local services per city, and 50 editorial topics per city."
    )

    def add_arguments(self, parser):
        parser.add_argument("--skip-content", action="store_true", help="Only apply branding and fixed locations.")
        parser.add_argument(
            "--catalog-only",
            action="store_true",
            help="Sync the 250-service catalogue, local service pages and project showcase without generating articles.",
        )
        parser.add_argument("--draft", action="store_true", help="Keep generated articles as drafts (this is also the safe default).")
        parser.add_argument("--publish", action="store_true", help="Explicitly publish generated articles after editorial review.")
        parser.add_argument("--refresh", action="store_true", help="Rebuild generated services and articles even when the seed is complete.")

    def _catalog_is_complete(self):
        cities = list(City.objects.filter(is_active=True, is_system=True).only("pk"))
        if not cities:
            return False
        all_service_slugs = [spec.slug for spec in ALL_SERVICE_SPECS]
        local_service_slugs = [spec.slug for spec in SERVICE_SPECS]
        if Service.objects.filter(slug__in=all_service_slugs).count() != len(ALL_SERVICE_SPECS):
            return False
        for city in cities:
            if (
                CityServicePage.objects.filter(city=city, service__slug__in=local_service_slugs).count()
                < len(SERVICE_SPECS)
            ):
                return False
        return True

    def _content_is_complete(self):
        if not self._catalog_is_complete():
            return False
        cities = list(City.objects.filter(is_active=True, is_system=True).only("pk"))
        for city in cities:
            if (
                BlogPost.objects.filter(city=city, slug__startswith="nakheel-najd-").count()
                < len(ARTICLE_TOPICS)
            ):
                return False
        return True

    @transaction.atomic
    def handle(self, *args, **options):
        if options["draft"] and options["publish"]:
            raise CommandError("Use either --draft or --publish, not both.")
        call_command("sync_fixed_locations")
        self._apply_brand()
        self._ensure_managed_pages()
        self._sync_media_and_projects(refresh=bool(options["refresh"]))
        if not options["skip_content"]:
            if options["catalog_only"]:
                if options["refresh"] or not self._catalog_is_complete():
                    self._seed_services(refresh=bool(options["refresh"]))
                if not self._catalog_is_complete():
                    raise CommandError(
                        "Nakheel Najd catalogue verification failed: expected 250 catalogue services "
                        "and 50 local service pages per city."
                    )
                self.stdout.write(self.style.SUCCESS("Nakheel Najd catalogue-only sync completed."))
                return
            if options["refresh"] or not self._content_is_complete():
                self._seed_services(refresh=bool(options["refresh"]))
                # Generated local articles are intentionally drafts unless an editor
                # explicitly opts into publication. This prevents bulk low-value pages
                # from being indexed merely because a bootstrap command was run.
                self._seed_articles(publish=bool(options["publish"]))
                if not self._content_is_complete():
                    raise CommandError(
                        "Nakheel Najd seed verification failed: expected 250 catalogue services, "
                        "50 local service pages per city, and 50 articles per city."
                    )
            else:
                self.stdout.write("Generated city content is already complete; skipping the heavy seed step.")
        self.stdout.write(self.style.SUCCESS("Nakheel Najd bootstrap completed."))

    def _apply_brand(self):
        """Fill safe brand defaults without overwriting admin customizations."""
        existed = SiteSettings.objects.filter(pk=1).exists()
        settings_obj = SiteSettings.load()
        defaults = {
            "site_name": BRAND_NAME,
            "contact_phone": PHONE,
            "whatsapp_number": PHONE,
            "legal_name": BRAND_NAME,
            "tagline": "توريد وزراعة النخيل وتنسيق الحدائق والشبوك في مدن المملكة",
            "homepage_meta_title": "نخيل نجد | توريد وزراعة النخيل واللاندسكيب والشبوك",
            "homepage_meta_description": "نخيل نجد لتوريد وزراعة النخيل العربي والواشنطني والملوكي، وصيانة الحدائق، وتنفيذ اللاندسكيب والشبوك في مدن المملكة وأحيائها.",
            "service_highlights": "توريد النخيل العربي\nتوريد النخيل الواشنطني والملوكي\nصيانة الحدائق واللاندسكيب\nشبكات الري\nالشبوك والسياجات",
            "seo_default_keywords": "نخيل نجد, توريد نخيل, نخيل عربي, نخيل واشنطني, نخيل ملوكي, صيانة حدائق, لاندسكيب, شبوك, شبكات ري, السعودية",
            "seo_default_description": "نخيل نجد لتوريد وزراعة النخيل العربي والواشنطني والملوكي، وصيانة الحدائق، وتنفيذ اللاندسكيب والشبوك في مدن المملكة وأحيائها.",
            "footer_text": "توريد وزراعة النخيل العربي والواشنطني والملوكي، وتنفيذ وصيانة الحدائق واللاندسكيب وشبكات الري والشبوك.",
            "homepage_hero_background_url": "/static/hero-desktop.webp",
            "homepage_hero_mobile_background_url": "/static/hero-mobile.webp",
            "homepage_hero_alt": "نخيل ولاندسكيب في مساحة خارجية من تنفيذ نخيل نجد",
            "blog_hero_background_url": "/static/project-19.webp",
            "default_og_image_url": "/static/hero-desktop.webp",
            "google_search_console_property": "https://getsiaq.online/",
        }
        changed = []
        for field, value in defaults.items():
            current = getattr(settings_obj, field)
            if not existed or current in (None, ""):
                setattr(settings_obj, field, value)
                changed.append(field)
        if not settings_obj.area_served:
            settings_obj.area_served = "\n".join(City.objects.filter(is_active=True, is_system=True).values_list("name", flat=True))
            changed.append("area_served")
        if changed:
            settings_obj.save(update_fields=sorted(set(changed + ["updated_at"])))

        if not ContactNumber.objects.filter(site_settings=settings_obj, is_active=True).exists():
            ContactNumber.objects.create(
                site_settings=settings_obj, phone=settings_obj.contact_phone or PHONE,
                label="واتساب نخيل نجد", is_primary=True, enable_whatsapp=True, is_active=True, sort_order=0,
            )
        home_page = Page.objects.filter(template_key="home").first()
        if home_page:
            page_updates = []
            for field, value in (
                ("hero_title", "توريد وزراعة النخيل وتنفيذ الحدائق والري والشبوك"),
                ("intro_text", "نورّد ونزرع النخيل العربي والواشنطني والملوكي، وننفذ اللاندسكيب وشبكات الري والشبوك مع تغطية المدن والأحياء."),
                ("meta_title", settings_obj.homepage_meta_title),
                ("meta_description", settings_obj.homepage_meta_description),
            ):
                if not getattr(home_page, field):
                    setattr(home_page, field, value)
                    page_updates.append(field)
            if page_updates:
                home_page.save(update_fields=sorted(set(page_updates + ["updated_at"])))
        self.stdout.write("Brand defaults verified without overwriting admin customizations.")

    def _ensure_managed_pages(self):
        """Seed stable Page rows without overwriting editor-authored body copy."""
        page_specs = (
            ("home", "الرئيسية", "home", "الرئيسية", 0, "توريد وزراعة النخيل وتنفيذ الحدائق والري والشبوك", "حلول نخيل ولاندسكيب تبدأ من معاينة الموقع وتحديد نطاق العمل."),
            ("about", "من نحن", "about", "من نحن", 10, "خبرة ميدانية وتفاصيل واضحة", "تعرف على طريقة عمل نخيل نجد ونطاق الخدمات التي نقدمها."),
            ("services", "الخدمات", "services", "الخدمات", 20, "خدمات النخيل واللاندسكيب والري والشبوك", "استعرض الخدمات حسب التخصص قبل طلب المعاينة وعرض السعر."),
            ("portfolio", "المشاريع", "portfolio", "المشاريع", 30, "معرض الأعمال ونماذج الحلول", "صور أعمال موردة من مالك الموقع مع توضيح نطاق الخدمة عندما لا يكون موقع التنفيذ موثقًا."),
            ("cities", "المدن", "cities", "المدن", 40, "تغطية محلية في مدن المملكة", "انتقل إلى مدينتك ثم الحي والخدمة المناسبة لموقعك."),
            ("blog", "المقالات", "blog", "المقالات", 50, "أدلة عملية قبل التنفيذ", "مقالات تساعدك على فهم النخيل والري والحدائق والتسوير قبل اتخاذ القرار."),
            ("contact", "تواصل معنا", "contact", "تواصل معنا", 60, "ابدأ بطلب واضح لموقعك", "أرسل تفاصيل الموقع والخدمة المطلوبة وسنتواصل معك لاستكمال المعاينة."),
        )
        for slug, title, template_key, menu_title, menu_order, hero_title, intro_text in page_specs:
            page, created = Page.objects.get_or_create(
                slug=slug,
                defaults={
                    "title": title, "menu_title": menu_title, "template_key": template_key,
                    "menu_order": menu_order, "hero_title": hero_title, "intro_text": intro_text,
                    "is_visible": True, "show_in_menu": template_key != "home",
                },
            )
            update_fields = []
            if page.template_key == "custom" or created:
                page.template_key = template_key; update_fields.append("template_key")
            for field, value in (("menu_title", menu_title), ("hero_title", hero_title), ("intro_text", intro_text)):
                if not getattr(page, field):
                    setattr(page, field, value); update_fields.append(field)
            if update_fields:
                page.save(update_fields=sorted(set(update_fields + ["updated_at"])))
        self.stdout.write("Managed public pages verified.")

    def _sync_media_and_projects(self, refresh=False):
        """Replace legacy visuals and distribute supplied project photos locally."""
        filenames = [item["filename"] for item in PROJECT_MEDIA]
        metadata = {item["filename"]: item for item in PROJECT_MEDIA}
        metadata.update(
            {
                "hero-desktop.webp": {
                    "title": "توريد وزراعة النخيل",
                    "alt": "مشروع نخيل نجد لتوريد وزراعة النخيل",
                    "category": "palm",
                },
                "hero-mobile.webp": {
                    "title": "خدمات نخيل نجد",
                    "alt": "تنفيذ خدمات النخيل واللاندسكيب",
                    "category": "palm",
                },
            }
        )
        usage_by_filename = {}
        for usage_group, group_files in IMAGE_GROUPS.items():
            for filename in group_files:
                usage_by_filename.setdefault(filename, usage_group)

        for index, item in enumerate(PROJECT_MEDIA, start=1):
            library_defaults = {
                "title": item["title"],
                "alt_text": item["alt"],
                "category": item["category"],
                "usage_group": usage_by_filename.get(item["filename"], "portfolio"),
                "sort_order": index,
                "is_active": True,
            }
            library_image, created = LibraryImage.objects.get_or_create(
                source_name=item["filename"], defaults=library_defaults
            )
            if not created:
                update_fields = []
                # Treat library metadata and uploaded replacements as editor-owned.
                # --refresh can rebuild generated labels, but normal deploy repair only
                # reactivates a missing seed row and never clears external/uploaded media.
                if not library_image.is_active:
                    library_image.is_active = True
                    update_fields.append("is_active")
                if refresh:
                    for field, value in library_defaults.items():
                        if field == "is_active":
                            continue
                        if getattr(library_image, field) != value:
                            setattr(library_image, field, value)
                            update_fields.append(field)
                if update_fields:
                    library_image.updated_at = timezone.now()
                    library_image.save(update_fields=sorted(set(update_fields + ["updated_at"])))

        # Seed defaults only when an admin has not already supplied media.
        page_groups = {
            "home": ("hero", IMAGE_GROUPS["home_hero"][:2]),
            "about": ("hero", IMAGE_GROUPS["about"][:2]),
            "services": ("hero", IMAGE_GROUPS["services"][:3]),
            "portfolio": ("hero", IMAGE_GROUPS["portfolio"][:3]),
            "cities": ("hero", IMAGE_GROUPS["cities"][:3]),
            "contact": ("hero", IMAGE_GROUPS["contact"][:2]),
            "blog": ("hero", IMAGE_GROUPS["blog"][:3]),
            "blog_post": ("hero", IMAGE_GROUPS["blog_post"][:3]),
            "city": ("hero", IMAGE_GROUPS["city"][:3]),
            "city_service": ("hero", IMAGE_GROUPS["city_service"][:3]),
        }
        for page, (section, group_files) in page_groups.items():
            if PageMedia.objects.filter(page=page, section=section, is_active=True).exists():
                continue
            for sort_order, filename in enumerate(group_files):
                item = metadata[filename]
                PageMedia.objects.create(
                    page=page, section=section, title=item["title"], alt_text=item["alt"],
                    external_url=f"/static/{filename}", sort_order=sort_order, is_active=True,
                )

        category_files = {
            category: [item["filename"] for item in PROJECT_MEDIA if item["category"] == category]
            for category in {"palm", "fencing", "traditional"}
        }
        category_files["shades"] = IMAGE_GROUPS["home_gallery"]

        now = timezone.now()
        seeded_service_slugs = [spec.slug for spec in ALL_SERVICE_SPECS]
        services = list(Service.objects.filter(is_visible=True, slug__in=seeded_service_slugs).select_related("category").order_by("display_order", "pk"))
        changed_services = []
        for index, service in enumerate(services):
            if service.image or service.image_url:
                continue
            category_name = service.category.name if service.category else ""
            if "شبك" in category_name or "مظلات" in category_name:
                media_category = "fencing"
            elif "ري" in category_name or "صيانة" in category_name:
                media_category = "traditional"
            else:
                media_category = "palm"
            candidates = category_files.get(media_category) or filenames
            service.image_url = f"/static/{candidates[index % len(candidates)]}"
            service.updated_at = now
            changed_services.append(service)
        if changed_services:
            Service.objects.bulk_update(changed_services, ["image_url", "updated_at"], batch_size=100)

        posts = list(
            BlogPost.objects.filter(
                Q(featured_image_url="") | Q(featured_image_url__startswith="https://example.com/")
            )
            .filter(Q(featured_image__isnull=True) | Q(featured_image=""))
            .only("pk", "featured_image_url", "updated_at")
            .order_by("city_id", "publish_at", "pk")
        )
        for index, post in enumerate(posts):
            post.featured_image_url = f"/static/{filenames[(index * 7 + 18) % len(filenames)]}"
            post.updated_at = now
        if posts:
            BlogPost.objects.bulk_update(posts, ["featured_image_url", "updated_at"], batch_size=200)

        # ProjectImage rows belong to editors and must never be deleted by an automatic seed/deploy command.

        cities = list(City.objects.filter(is_active=True, is_system=True).prefetch_related("districts").order_by("id"))
        seeded_slugs = []
        for index, item in enumerate(PROJECT_MEDIA, start=1):
            slug = f"nakheel-najd-project-{index:02d}"
            seeded_slugs.append(slug)
            coverage_city = cities[(index - 1) % len(cities)] if cities else None
            city_districts = list(coverage_city.districts.filter(is_active=True).order_by("sort_order", "id")) if coverage_city else []
            coverage_district = city_districts[((index - 1) * 3) % len(city_districts)] if city_districts else None
            project_defaults = {
                "title": item["title"],
                "category": item["category"],
                # The supplied photos do not carry verified execution geography.
                # Keep the factual location empty, but associate each record with
                # a coverage city/district so local pages can show relevant work
                # without falsely claiming the photo was taken there.
                "city": None,
                "district": None,
                "coverage_city": coverage_city,
                "coverage_district": coverage_district,
                "record_type": "portfolio",
                "is_indexable": True,
                "description": f"{item['description']} صورة ضمن معرض نماذج أعمال نخيل نجد الموردة من مالك الموقع.",
                "featured_image_url": f"/static/{item['filename']}",
                "is_visible": True,
                "meta_title": f"{item['title']} | مشاريع نخيل نجد",
                "meta_description": f"{item['description']} ضمن معرض مشاريع ونماذج أعمال نخيل نجد.",
                "meta_keywords": f"{item['title']}, مشاريع لاندسكيب, نخيل نجد",
            }
            project, created = Project.objects.get_or_create(slug=slug, defaults=project_defaults)
            if not created:
                update_fields = []
                # Automatic deploy/catalog repair must preserve editor copy and uploaded
                # imagery. --refresh may rebuild generated text, but even then an uploaded
                # image remains authoritative.
                repair_fields = (
                    "record_type", "is_indexable", "is_visible", "coverage_city", "coverage_district",
                )
                if refresh:
                    repair_fields += ("title", "category", "description", "meta_title", "meta_description", "meta_keywords")
                for field in repair_fields:
                    value = project_defaults[field]
                    if getattr(project, field) != value:
                        setattr(project, field, value)
                        update_fields.append(field)
                if not project.featured_image and not project.featured_image_url:
                    project.featured_image_url = project_defaults["featured_image_url"]
                    update_fields.append("featured_image_url")
                if update_fields:
                    project.updated_at = now
                    project.save(update_fields=sorted(set(update_fields + ["updated_at"])))

        # Add clearly-labelled local solution records so every coverage city has a
        # richer project feed. These records are intentionally noindex because they
        # are navigation/decision aids, not claims of completed work in that district.
        local_labels = {
            "palm": "توريد وزراعة نخيل",
            "fencing": "شبوك وتسوير",
            "shades": "مظلات وتنسيق خارجي",
            "traditional": "ري وصيانة لاندسكيب",
        }
        local_categories = LOCAL_SOLUTION_CATEGORIES
        local_solution_count = 0
        for city_index, city in enumerate(cities):
            city_districts = list(city.districts.filter(is_active=True).order_by("sort_order", "id"))
            if not city_districts:
                continue
            for slot, category in enumerate(local_categories):
                district = city_districts[(city_index * 5 + slot * 7) % len(city_districts)]
                media_pool = [item for item in PROJECT_MEDIA if item["category"] == category] or list(PROJECT_MEDIA)
                media = media_pool[(city_index * len(local_categories) + slot) % len(media_pool)]
                slug = f"local-solution-{city.slug}-{slot + 1:02d}"
                seeded_slugs.append(slug)
                label = local_labels[category]
                local_defaults = {
                    "title": f"نموذج {label} لحي {district.name} – {city.name}",
                    "category": category,
                    "city": None,
                    "district": None,
                    "coverage_city": city,
                    "coverage_district": district,
                    "record_type": "local_solution",
                    "is_indexable": False,
                    "description": (
                        f"نموذج عرض محلي يوضح أسلوب تخطيط خدمة {label} ضمن نطاق حي {district.name} في {city.name}. "
                        "هذا السجل يوضح نطاق الخدمة وطريقة الحل ولا يعني أن الصورة نُفذت في هذا الحي بعينه."
                    ),
                    "featured_image_url": f"/static/{media['filename']}",
                    "is_visible": True,
                    "meta_title": f"{label} في {city.name} | نموذج خدمة نخيل نجد",
                    "meta_description": f"نموذج خدمة محلي لـ{label} ضمن تغطية {city.name} وحي {district.name} دون ادعاء موقع تنفيذ غير موثق.",
                    "meta_keywords": f"{label}, {city.name}, {district.name}, نخيل نجد",
                }
                project, created = Project.objects.get_or_create(slug=slug, defaults=local_defaults)
                if not created:
                    update_fields = []
                    repair_fields = (
                        "record_type", "is_indexable", "is_visible", "coverage_city", "coverage_district",
                    )
                    if refresh:
                        repair_fields += ("title", "category", "description", "meta_title", "meta_description", "meta_keywords")
                    for field in repair_fields:
                        value = local_defaults[field]
                        if getattr(project, field) != value:
                            setattr(project, field, value)
                            update_fields.append(field)
                    if not project.featured_image and not project.featured_image_url:
                        project.featured_image_url = local_defaults["featured_image_url"]
                        update_fields.append("featured_image_url")
                    if update_fields:
                        project.updated_at = now
                        project.save(update_fields=sorted(set(update_fields + ["updated_at"])))
                local_solution_count += 1

        # Preserve custom project records and any verified location supplied by an
        # editor.  Only replace legacy/missing imagery; never auto-assign geography.
        legacy_projects = list(
            Project.objects.filter(is_visible=True)
            .exclude(slug__in=seeded_slugs)
            .select_related("city", "district")
            .order_by("pk")
        )
        changed_legacy_projects = []
        for index, project in enumerate(legacy_projects):
            placeholder_image = project.featured_image_url.startswith("https://example.com/")
            if project.featured_image or (project.featured_image_url and not placeholder_image):
                continue
            project.featured_image_url = f"/static/{filenames[index % len(filenames)]}"
            project.updated_at = now
            changed_legacy_projects.append(project)
        if changed_legacy_projects:
            Project.objects.bulk_update(changed_legacy_projects, ["featured_image_url", "updated_at"], batch_size=100)

        # Remove only explicit development placeholders; real editor-owned gallery
        # rows and uploaded replacements remain untouched.
        ProjectImage.objects.filter(
            project__in=legacy_projects,
            external_url__startswith="https://example.com/",
        ).delete()

        self.stdout.write(
            f"Synced {len(PROJECT_MEDIA)} supplied project photos, distributed them by coverage scope, "
            f"and added {local_solution_count} clearly-labelled local solution records without fabricating execution locations."
        )

    def _service_category(self, name):
        slug = CATEGORY_SLUGS.get(name, unicode_slug(name, "services"))
        obj, _ = ServiceCategory.objects.update_or_create(
            slug=slug,
            defaults={
                "name": name,
                "description": (
                    f"خدمات {name} من نخيل نجد، مرتبة حسب نوع الموقع ونطاق التنفيذ لتسهيل "
                    "اختيار الخدمة المناسبة قبل طلب المعاينة."
                ),
                "meta_title": f"خدمات {name} | نخيل نجد",
                "meta_description": f"استعرض خدمات {name} ونطاق كل خدمة وخطواتها العملية قبل طلب المعاينة وعرض السعر.",
            },
        )
        return obj

    def _service_tag(self, name):
        slug = unicode_slug(name, "service-tag")
        obj, _ = ServiceTag.objects.update_or_create(
            slug=slug,
            defaults={
                "name": name,
                "meta_title": f"{name} | خدمات نخيل نجد",
                "meta_description": f"خدمات ومعلومات مرتبطة بـ {name}.",
            },
        )
        return obj

    def _release_city_service_slug_collision(self, city, service, custom_slug):
        """Preserve legacy rows while freeing the canonical local-service slug."""
        collision = (
            CityServicePage.objects.filter(city=city, custom_slug=custom_slug)
            .exclude(service=service)
            .select_related("service")
            .first()
        )
        if not collision:
            return

        base = (collision.custom_slug or collision.service.slug or "legacy-service")[:130]
        suffix = f"-legacy-{collision.pk}"
        candidate = f"{base[:160 - len(suffix)]}{suffix}"
        counter = 2
        while CityServicePage.objects.filter(city=city, custom_slug=candidate).exclude(pk=collision.pk).exists():
            suffix = f"-legacy-{collision.pk}-{counter}"
            candidate = f"{base[:160 - len(suffix)]}{suffix}"
            counter += 1

        collision.custom_slug = candidate
        collision.save(update_fields=["custom_slug"])
        self.stdout.write(
            self.style.WARNING(
                f"Resolved legacy slug collision in {city.name}: {custom_slug} -> {candidate}"
            )
        )

    def _seed_services(self, refresh=False):
        """Create/repair the managed catalogue while preserving editor copy by default."""
        cities = list(City.objects.filter(is_active=True, is_system=True).prefetch_related("districts").order_by("id"))
        categories = {spec.category: self._service_category(spec.category) for spec in ALL_SERVICE_SPECS}
        tag_names = {tag for spec in ALL_SERVICE_SPECS for tag in spec.tags}
        service_tags = {name: self._service_tag(name) for name in sorted(tag_names)}
        local_slugs = {spec.slug for spec in SERVICE_SPECS}
        for index, spec in enumerate(ALL_SERVICE_SPECS, start=1):
            is_local_service = spec.slug in local_slugs
            defaults = {
                "title": spec.title, "short_title": spec.title, "description": service_catalog_html(spec),
                "image_url": f"/static/{PROJECT_MEDIA[(index - 1) % len(PROJECT_MEDIA)]['filename']}",
                "benefits": "\n".join(spec.benefits), "category": categories[spec.category],
                "primary_city": None, "primary_district": None,
                "meta_title": f"{spec.title} | نخيل نجد", "meta_description": service_meta_description(spec),
                "meta_keywords": ", ".join((*spec.tags, "نخيل نجد", "السعودية")),
                "auto_classify": False, "auto_distribute": False, "is_visible": True, "display_order": index,
            }
            service, created = Service.objects.get_or_create(slug=spec.slug, defaults=defaults)
            updates = []
            if not created and refresh:
                for field, value in defaults.items():
                    if field == "image_url" and service.image:
                        continue
                    setattr(service, field, value); updates.append(field)
            elif not created:
                if not service.is_visible: service.is_visible=True; updates.append("is_visible")
                if not service.category_id: service.category=categories[spec.category]; updates.append("category")
                if not service.image and not service.image_url: service.image_url=defaults["image_url"]; updates.append("image_url")
                for field in ("short_title","description","benefits","meta_title","meta_description","meta_keywords"):
                    if not getattr(service, field): setattr(service, field, defaults[field]); updates.append(field)
            if updates:
                service.save(update_fields=sorted(set(updates+["updated_at"])))
            through=Service.cities.through
            if is_local_service:
                existing=set(through.objects.filter(service_id=service.pk).values_list("city_id",flat=True))
                through.objects.bulk_create([through(service_id=service.pk,city_id=c.pk) for c in cities if c.pk not in existing], ignore_conflicts=True)
            else:
                through.objects.filter(service_id=service.pk).delete()
                CityServicePage.objects.filter(service=service).update(is_active=False)
            if created or refresh or not service.tags.exists(): service.tags.set([service_tags[n] for n in spec.tags])
            if is_local_service:
                for city_index, city in enumerate(cities):
                    districts=list(city.districts.filter(is_active=True).order_by("sort_order","name"))
                    if not districts: continue
                    district=districts[(index+city_index)%len(districts)]
                    self._release_city_service_slug_collision(city,service,spec.slug)
                    ldefs={
                        "district":district,"hero_title":f"{spec.title} في {city.name}","content":service_page_html(spec,city,district),
                        "benefits":"\n".join(spec.benefits),"is_active":True,"custom_slug":spec.slug,
                        "meta_title":f"{spec.title} في {city.name} | نخيل نجد",
                        "meta_description":f"خدمة {spec.title} في {city.name} مع تغطية الأحياء ومنها {district.name}. معاينة وتحديد نطاق العمل وطلب عبر واتساب.",
                        "meta_keywords":", ".join((*spec.tags,city.name,district.name,"نخيل نجد")),
                    }
                    lp, lc=CityServicePage.objects.get_or_create(city=city,service=service,defaults=ldefs)
                    lu=[]
                    if not lc and refresh:
                        for field,value in ldefs.items(): setattr(lp,field,value); lu.append(field)
                    elif not lc:
                        if not lp.is_active: lp.is_active=True; lu.append("is_active")
                        if not lp.custom_slug: lp.custom_slug=spec.slug; lu.append("custom_slug")
                        if not lp.district_id: lp.district=district; lu.append("district")
                        for field in ("hero_title","content","benefits","meta_title","meta_description","meta_keywords"):
                            if not getattr(lp,field): setattr(lp,field,ldefs[field]); lu.append(field)
                    if lu: lp.save(update_fields=sorted(set(lu+["updated_at"])))
            if index%25==0 or index==len(ALL_SERVICE_SPECS): self.stdout.write(f"Service seed progress: {index}/{len(ALL_SERVICE_SPECS)}")
        self.stdout.write(f"Seeded/repaired {len(ALL_SERVICE_SPECS)} catalogue services; only {len(SERVICE_SPECS)} core services receive local city pages.")

    def _blog_category(self, name):
        slug = CATEGORY_SLUGS.get(name, unicode_slug(name, "articles"))
        obj, _ = BlogCategory.objects.update_or_create(
            slug=slug,
            defaults={
                "name": name,
                "description": f"أدلة ومقالات عملية عن {name} من نخيل نجد.",
                "meta_title": f"{name} | مدونة نخيل نجد",
                "meta_description": f"مقالات عملية عن {name} وخدمات المدن والأحياء.",
            },
        )
        return obj

    def _blog_tag(self, name):
        slug = unicode_slug(name, "blog-tag")
        obj, _ = BlogTag.objects.update_or_create(
            slug=slug,
            defaults={
                "name": name,
                "meta_title": f"{name} | مدونة نخيل نجد",
                "meta_description": f"مقالات مرتبطة بـ {name}.",
            },
        )
        return obj

    def _seed_articles(self, publish=True):
        now = timezone.now()
        cities = list(City.objects.filter(is_active=True, is_system=True).prefetch_related("districts").order_by("id"))
        categories = {topic[1]: self._blog_category(topic[1]) for topic in ARTICLE_TOPICS}
        generic_tags = {name: self._blog_tag(name) for name in set(SOURCE_TAGS.values()) | set(categories)}
        city_tags = {city.pk: self._blog_tag(city.name) for city in cities}
        services = list(Service.objects.filter(slug__in=[spec.slug for spec in SERVICE_SPECS]).order_by("display_order"))
        service_by_index = {index: service for index, service in enumerate(services)}

        created_or_updated = 0
        for city_index, city in enumerate(cities):
            districts = list(city.districts.filter(is_active=True).order_by("sort_order", "name"))
            if not districts:
                continue
            for topic_index, topic in enumerate(ARTICLE_TOPICS):
                district = districts[(topic_index + city_index) % len(districts)]
                related_service = service_by_index.get(topic_index % max(len(service_by_index), 1))
                related_service_title = related_service.title if related_service else "خدمات النخيل واللاندسكيب"
                title = f"{topic[0]} في {city.name}: دليل حي {district.name}"
                slug = f"nakheel-najd-{city.slug}-{topic_index + 1:02d}"
                excerpt = f"{topic[2]} دليل محلي لمدينة {city.name} وحي {district.name}."
                post, _ = BlogPost.objects.update_or_create(
                    slug=slug,
                    defaults={
                        "title": title[:200],
                        "excerpt": excerpt,
                        "content": article_html(topic, city, district, related_service_title),
                        "featured_image": None,
                        "featured_image_url": f"/static/{PROJECT_MEDIA[(city_index * len(ARTICLE_TOPICS) + topic_index) % len(PROJECT_MEDIA)]['filename']}",
                        "category": categories[topic[1]],
                        "city": city,
                        "district": district,
                        "auto_classify": False,
                        "auto_distribute": False,
                        "status": "published" if publish else "draft",
                        "is_featured": topic_index < 3,
                        "publish_at": now - timedelta(days=(city_index * 50 + topic_index) % 360),
                        "meta_title": f"{topic[0]} في {city.name} | نخيل نجد"[:255],
                        "meta_description": excerpt[:300],
                        "meta_keywords": ", ".join((topic[0], city.name, district.name, SOURCE_TAGS.get(topic[4], "لاندسكيب"), "نخيل نجد")),
                    },
                )
                tags = [generic_tags[topic[1]], generic_tags[SOURCE_TAGS.get(topic[4], "اللاندسكيب")], city_tags[city.pk]]
                post.tags.set(tags)
                created_or_updated += 1
            self.stdout.write(
                f"Article seed progress: {city_index + 1}/{len(cities)} cities "
                f"({created_or_updated} articles)"
            )

        self.stdout.write(f"Seeded or updated {created_or_updated} localized articles.")
