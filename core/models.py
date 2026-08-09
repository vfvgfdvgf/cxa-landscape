import mimetypes
import re
from pathlib import PurePath
from urllib.parse import urlsplit

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, MaxValueValidator, MinValueValidator
from django.core.files.storage import default_storage
from django.db import models
from django.db.models.deletion import ProtectedError
from django.db.models import Q
from django.templatetags.static import static

from .html_utils import sanitize_html
from .image_utils import optimize_uploaded_image


def validate_image_source(value):
    """Allow secure remote images and the local public media paths used by the project."""
    if not value:
        return
    if value.startswith((
        "/static/",
        "/media/",
        "/media-db/",
        "/editorial/",
        "/video-posters/",
        "/images/",
    )):
        return
    parsed = urlsplit(value)
    if parsed.scheme == "https" and parsed.netloc:
        return
    raise ValidationError("استخدم رابط HTTPS أو مسار وسائط عامًا معتمدًا مثل /media/ أو /editorial/.")


def validate_video_source(value):
    """Allow secure remote videos and the optimized public video paths."""
    if not value:
        return
    if value.startswith(("/videos/", "/media/")):
        return
    parsed = urlsplit(value)
    if parsed.scheme == "https" and parsed.netloc:
        return
    raise ValidationError("استخدم رابط فيديو HTTPS أو مسارًا يبدأ بـ /videos/ أو /media/.")


def validate_link_target(value):
    """Keep CMS CTA targets internal or on secure external destinations."""
    if not value:
        return
    if value.startswith("/") and not value.startswith("//"):
        return
    parsed = urlsplit(value)
    if parsed.scheme == "https" and parsed.netloc:
        return
    raise ValidationError("استخدم رابطًا داخليًا يبدأ بـ / أو رابط HTTPS كاملًا.")


def validate_home_video_size(value):
    if value and getattr(value, "size", 0) > 30 * 1024 * 1024:
        raise ValidationError("حجم الفيديو يجب ألا يتجاوز 30 ميجابايت بعد الضغط.")


def home_video_storage():
    """Use Cloudinary's video resource type only when production media is enabled."""
    if getattr(settings, "USE_CLOUDINARY_MEDIA", False):
        from cloudinary_storage.storage import VideoMediaCloudinaryStorage

        return VideoMediaCloudinaryStorage()
    return default_storage


HOME_MEDIA_SOURCE_FIELDS = (
    "image", "image_url", "video", "video_url", "mobile_video",
    "mobile_video_url", "poster", "poster_url",
)


def home_media_source_values(instance):
    """Return unique stored media identities for one homepage placement."""
    sources = set()
    for field_name in HOME_MEDIA_SOURCE_FIELDS:
        value = getattr(instance, field_name, None)
        if hasattr(value, "name"):
            value = value.name
        normalized = str(value or "").strip()
        if normalized:
            sources.add(normalized)
    return sources


def home_media_source_usage(source, exclude_instance=None):
    """Count homepage placements using a source, not alternative fields in one placement."""
    source = str(source or "").strip()
    if not source:
        return 0
    lookup = Q()
    for field_name in HOME_MEDIA_SOURCE_FIELDS:
        lookup |= Q(**{field_name: source})
    count = 0
    for model in (HomeSection, HomeSectionMedia):
        queryset = model.objects.filter(lookup)
        if exclude_instance and isinstance(exclude_instance, model) and exclude_instance.pk:
            queryset = queryset.exclude(pk=exclude_instance.pk)
        count += queryset.count()
    return count


def validate_home_media_repetition(instance, max_placements=3):
    errors = []
    for source in sorted(home_media_source_values(instance)):
        existing = home_media_source_usage(source, exclude_instance=instance)
        if existing >= max_placements:
            filename = PurePath(urlsplit(source).path).name or source
            errors.append(
                f"الوسيط «{filename}» مستخدم في {existing} مواضع أخرى. "
                f"الحد الأقصى {max_placements} مواضع؛ اختر صورة أو فيديو مختلفًا."
            )
    if errors:
        raise ValidationError(errors)


def validate_media_pair(instance, upload_field, url_field, label):
    if getattr(instance, upload_field, None) and getattr(instance, url_field, ""):
        raise ValidationError(
            {url_field: f"اختر {label} مرفوعًا أو رابطًا خارجيًا، وليس الاثنين معًا."}
        )


def validate_cta_pair(instance, label_field, url_field, label):
    has_label = bool(str(getattr(instance, label_field, "") or "").strip())
    has_url = bool(str(getattr(instance, url_field, "") or "").strip())
    if has_label != has_url:
        raise ValidationError(
            {url_field if has_label else label_field: f"أكمل نص {label} ورابطه معًا، أو اتركهما فارغين."}
        )


def normalize_image_field_name(name, upload_prefix):
    if not name:
        return name

    clean_name = str(name).replace("\\", "/").lstrip("/")
    media_prefix = settings.MEDIA_URL.strip("/")
    if media_prefix and clean_name.startswith(f"{media_prefix}/"):
        clean_name = clean_name[len(media_prefix) + 1 :]

    upload_prefix = upload_prefix.strip("/")
    repeated_prefix = f"{upload_prefix}/{upload_prefix}/"
    while clean_name.startswith(repeated_prefix):
        clean_name = f"{upload_prefix}/{clean_name[len(repeated_prefix):]}"

    return clean_name


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SeoFields(models.Model):
    meta_title = models.CharField(max_length=255, blank=True)
    meta_description = models.TextField(blank=True)
    meta_keywords = models.CharField(max_length=500, blank=True)

    class Meta:
        abstract = True


class SiteSettings(TimeStampedModel):
    site_name = models.CharField(max_length=200, default="نخيل نجد")
    contact_phone = models.CharField(max_length=20, default="0554882724")
    whatsapp_number = models.CharField(max_length=20, default="0554882724")
    email = models.EmailField(blank=True)
    address = models.CharField(max_length=255, blank=True)
    facebook_url = models.URLField(blank=True)
    instagram_url = models.URLField(blank=True)
    x_url = models.URLField(blank=True)
    linkedin_url = models.URLField(blank=True)
    tagline = models.CharField(max_length=255, default="خدمات متكاملة في جميع مدن السعودية")
    homepage_meta_title = models.CharField(
        max_length=255,
        default="تنسيق حدائق ولاندسكيب وزراعة نخيل في السعودية | نخيل نجد",
    )
    homepage_meta_description = models.TextField(
        default="تصميم وتنفيذ تنسيق الحدائق واللاندسكيب وزراعة ونقل النخيل وشبكات الري وصيانة المساحات الخارجية في مدن السعودية بخطة واضحة تناسب الموقع والمناخ."
    )
    homepage_hero_background = models.ImageField(upload_to="site-settings/", blank=True, null=True)
    homepage_hero_background_url = models.CharField(max_length=500, blank=True, validators=[validate_image_source])
    homepage_hero_mobile_background = models.ImageField(
        upload_to="site-settings/branding/",
        blank=True,
        null=True,
        verbose_name="صورة هيرو الهاتف",
        help_text="صورة عمودية اختيارية للهاتف. عند تركها فارغة تُستخدم صورة الهيرو الرئيسية.",
    )
    homepage_hero_mobile_background_url = models.CharField(
        max_length=500,
        blank=True,
        validators=[validate_image_source],
        verbose_name="رابط صورة هيرو الهاتف",
    )
    homepage_hero_alt = models.CharField(
        max_length=180,
        blank=True,
        verbose_name="وصف صورة الهيرو",
        help_text="وصف مختصر ودقيق للصورة لتحسين الوصول وSEO الصور.",
    )
    homepage_hero_focus_x = models.PositiveSmallIntegerField(
        default=50,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="تركيز الهيرو أفقيًا (%)",
    )
    homepage_hero_focus_y = models.PositiveSmallIntegerField(
        default=50,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="تركيز الهيرو رأسيًا (%)",
    )
    homepage_hero_overlay_opacity = models.PositiveSmallIntegerField(
        default=62,
        validators=[MinValueValidator(20), MaxValueValidator(90)],
        verbose_name="قوة تعتيم الهيرو (%)",
        help_text="قيمة بين 20 و90 لضمان وضوح النص فوق الصورة.",
    )
    site_logo = models.ImageField(
        upload_to="site-settings/branding/",
        blank=True,
        null=True,
        verbose_name="شعار الموقع",
    )
    site_logo_url = models.CharField(
        max_length=500,
        blank=True,
        validators=[validate_image_source],
        verbose_name="رابط شعار الموقع",
    )
    site_logo_alt = models.CharField(
        max_length=160,
        blank=True,
        verbose_name="وصف الشعار",
        help_text="يُستخدم اسم الموقع تلقائيًا عند تركه فارغًا.",
    )
    blog_hero_background = models.ImageField(upload_to="site-settings/", blank=True, null=True)
    blog_hero_background_url = models.CharField(max_length=500, blank=True, validators=[validate_image_source])
    primary_color = models.CharField(max_length=7, default="#83643b")
    secondary_color = models.CharField(max_length=7, default="#0f5b54")
    accent_color = models.CharField(max_length=7, default="#c6a56d")
    background_color = models.CharField(max_length=7, default="#f7f1e8")
    text_color = models.CharField(max_length=7, default="#1c1915")
    footer_text = models.TextField(blank=True)
    service_highlights = models.TextField(
        default="تصميم حدائق\nلاندسكيب\nأشجار ونخيل\nشبوك\nمظلات",
        help_text="أدخل خدمة في كل سطر لتظهر في محتوى الموقع وتهيئة SEO.",
    )
    seo_default_keywords = models.CharField(
        max_length=500,
        blank=True,
        default="تنسيق حدائق, شركة تنسيق حدائق, لاندسكيب, تصميم حدائق منزلية, زراعة نخيل, نقل نخيل, شبكات ري, صيانة حدائق, السعودية",
        help_text="كلمات مفتاحية افتراضية مفصولة بفواصل.",
    )
    seo_default_description = models.TextField(
        blank=True,
        default="شركة متخصصة في خدمات اللاندسكيب وتنسيق الحدائق والأشجار والنخيل والمظلات والشبوك في السعودية.",
    )
    seo_twitter_handle = models.CharField(
        max_length=50,
        blank=True,
        help_text="مثال: @yourbrand",
    )
    default_og_image = models.ImageField(upload_to="site-settings/", blank=True, null=True)
    default_og_image_url = models.CharField(max_length=500, blank=True, validators=[validate_image_source])
    business_type = models.CharField(max_length=80, default="LocalBusiness")
    legal_name = models.CharField(max_length=220, blank=True)
    street_address = models.CharField(max_length=255, blank=True)
    address_locality = models.CharField(max_length=120, blank=True)
    address_region = models.CharField(max_length=120, blank=True)
    postal_code = models.CharField(max_length=40, blank=True)
    address_country = models.CharField(max_length=2, default="SA")
    latitude = models.DecimalField(max_digits=10, decimal_places=7, blank=True, null=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, blank=True, null=True)
    opening_hours = models.TextField(blank=True, help_text="سطر لكل يوم بصيغة schema.org مثل Mo-Sa 08:00-20:00")
    area_served = models.TextField(blank=True, help_text="سطر لكل مدينة أو منطقة خدمة")
    same_as_links = models.TextField(blank=True, help_text="سطر لكل رابط اجتماعي أو ملف تعريفي خارجي")
    google_search_console_property = models.CharField(max_length=255, blank=True, help_text="مثال URL-prefix: https://getsiaq.online/ أو Domain: sc-domain:getsiaq.online")
    google_service_account_json = models.TextField(blank=True, help_text="JSON لحساب الخدمة الخاص بـ Google Search Console. احفظه فقط في بيئة موثوقة.")
    ai_seo_enabled = models.BooleanField(default=True, help_text="تشغيل منظومة تحسين SEO اليومية.")
    ai_seo_auto_apply = models.BooleanField(default=False, help_text="تطبيق تعديلات الذكاء الاصطناعي تلقائيًا عند تشغيل أمر الأتمتة.")
    ai_seo_research_queries = models.TextField(
        blank=True,
        help_text="استعلامات بحث إضافية، سطر لكل استعلام. تستخدمها الأتمتة اليومية مع Search Console.",
    )
    class Meta:
        verbose_name = "إعدادات الموقع"
        verbose_name_plural = "إعدادات الموقع"

    def __str__(self):
        return self.site_name

    def save(self, *args, **kwargs):
        if self.homepage_hero_background:
            optimize_uploaded_image(self.homepage_hero_background, max_size=(2200, 1600))
        if self.homepage_hero_mobile_background:
            optimize_uploaded_image(self.homepage_hero_mobile_background, max_size=(1200, 1600))
        if self.site_logo:
            optimize_uploaded_image(self.site_logo, max_size=(1000, 500))
        if self.blog_hero_background:
            optimize_uploaded_image(self.blog_hero_background, max_size=(2200, 1600))
        if self.default_og_image:
            optimize_uploaded_image(self.default_og_image, max_size=(2200, 1600))
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        instance, _ = cls.objects.get_or_create(pk=1)
        return instance

    @property
    def homepage_hero_background_resolved(self):
        if self.homepage_hero_background:
            return self.homepage_hero_background.url
        return self.homepage_hero_background_url

    @property
    def homepage_hero_mobile_background_resolved(self):
        if self.homepage_hero_mobile_background:
            return self.homepage_hero_mobile_background.url
        return self.homepage_hero_mobile_background_url

    @property
    def site_logo_resolved(self):
        if self.site_logo:
            return self.site_logo.url
        return self.site_logo_url

    @property
    def blog_hero_background_resolved(self):
        if self.blog_hero_background:
            return self.blog_hero_background.url
        return self.blog_hero_background_url

    @property
    def default_og_image_resolved(self):
        if self.default_og_image:
            return self.default_og_image.url
        return self.default_og_image_url

    @property
    def service_highlights_list(self):
        return [item.strip() for item in (self.service_highlights or "").splitlines() if item.strip()]

    @property
    def opening_hours_list(self):
        return [item.strip() for item in (self.opening_hours or "").splitlines() if item.strip()]

    @property
    def area_served_list(self):
        return [item.strip() for item in (self.area_served or "").splitlines() if item.strip()]

    @property
    def same_as_list(self):
        links = [self.instagram_url, self.facebook_url, self.x_url, self.linkedin_url]
        links += [item.strip() for item in (self.same_as_links or "").splitlines() if item.strip()]
        seen = set()
        output = []
        for link in links:
            if link and link not in seen:
                seen.add(link)
                output.append(link)
        return output


class ContactNumber(TimeStampedModel):
    site_settings = models.ForeignKey(
        SiteSettings,
        on_delete=models.CASCADE,
        related_name="contact_numbers",
        default=1,
    )
    label = models.CharField(max_length=80, default="رقم التواصل")
    phone = models.CharField(max_length=20)
    sort_order = models.PositiveIntegerField(default=0)
    is_primary = models.BooleanField(default=False)
    enable_whatsapp = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "رقم تواصل"
        verbose_name_plural = "أرقام التواصل"
        ordering = ["-is_primary", "sort_order", "id"]

    def __str__(self):
        return f"{self.label} - {self.phone}"

    @property
    def whatsapp_digits(self):
        digits = "".join(char for char in (self.phone or "") if char.isdigit())
        if digits.startswith("0"):
            digits = f"966{digits[1:]}"
        return digits


class PageMedia(models.Model):
    PAGE_CHOICES = [
        ("home", "الرئيسية"),
        ("about", "من نحن"),
        ("services", "الخدمات"),
        ("portfolio", "المشاريع"),
        ("cities", "المدن"),
        ("contact", "اتصل بنا"),
        ("blog", "المدونة"),
        ("blog_post", "تفاصيل المقال"),
        ("city", "صفحة المدينة"),
        ("city_service", "صفحة خدمة داخل مدينة"),
    ]

    page = models.CharField(max_length=30, choices=PAGE_CHOICES)
    section = models.CharField(
        max_length=50,
        default="hero",
        help_text="مثال: hero, gallery, secondary",
    )
    folder = models.ForeignKey(
        "MediaFolder",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="images",
    )
    title = models.CharField(max_length=150)
    alt_text = models.CharField(max_length=180, blank=True)
    image = models.ImageField(upload_to="site-media/", blank=True, null=True)
    external_url = models.CharField(max_length=500, blank=True, validators=[validate_image_source])
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "صورة صفحة"
        verbose_name_plural = "صور الصفحات"
        ordering = ["page", "section", "sort_order", "-created_at"]
        indexes = [models.Index(fields=["page", "section", "is_active"], name="page_media_lookup_idx")]

    def __str__(self):
        return f"{self.get_page_display()} - {self.title}"

    def clean(self):
        if not self.image and not self.external_url:
            raise ValidationError("يجب رفع صورة من الجهاز أو إدخال رابط صورة خارجي.")

    def save(self, *args, **kwargs):
        if self.image:
            optimize_uploaded_image(self.image)
        super().save(*args, **kwargs)

    @property
    def image_url(self):
        if self.image:
            return self.image.url
        return self.external_url

    @property
    def display_alt(self):
        return self.alt_text or self.title


class HomeSection(TimeStampedModel):
    """Editable presentation and media settings for each fixed homepage section."""

    SECTION_CHOICES = [
        ("hero", "الهيرو الرئيسي"),
        ("manifesto", "الرؤية والتعريف"),
        ("stories", "قصص من الميدان"),
        ("gallery", "معرض الصور"),
        ("services", "الخدمات"),
        ("process", "منهج التنفيذ"),
        ("feature", "المشروع المميز"),
        ("coverage", "نطاق التغطية"),
        ("projects", "معرض الأعمال"),
        ("testimonials", "آراء العملاء"),
        ("insights", "المقالات"),
        ("faq", "الأسئلة الشائعة"),
        ("closing", "دعوة التواصل الختامية"),
        ("marquee", "الشريط المتحرك"),
    ]
    THEME_CHOICES = [
        ("dark", "داكن"),
        ("paper", "فاتح"),
        ("media", "صورة أو فيديو كامل"),
    ]
    video_validators = [
        FileExtensionValidator(allowed_extensions=["mp4", "webm", "mov"]),
        validate_home_video_size,
    ]

    key = models.CharField(max_length=30, choices=SECTION_CHOICES, unique=True, verbose_name="القسم")
    eyebrow = models.CharField(max_length=140, blank=True, verbose_name="العنوان الصغير")
    kicker = models.CharField(max_length=180, blank=True, verbose_name="السطر التعريفي")
    title = models.TextField(blank=True, verbose_name="العنوان الرئيسي", help_text="يمكن وضع كل جزء من العنوان في سطر مستقل.")
    description = models.TextField(blank=True, verbose_name="النص الوصفي")
    supporting_text = models.TextField(blank=True, verbose_name="نص إضافي")
    primary_cta_label = models.CharField(max_length=80, blank=True, verbose_name="نص الزر الرئيسي")
    primary_cta_url = models.CharField(max_length=500, blank=True, validators=[validate_link_target], verbose_name="رابط الزر الرئيسي")
    secondary_cta_label = models.CharField(max_length=80, blank=True, verbose_name="نص الزر الثاني")
    secondary_cta_url = models.CharField(max_length=500, blank=True, validators=[validate_link_target], verbose_name="رابط الزر الثاني")
    image = models.ImageField(upload_to="home-sections/images/", blank=True, null=True, verbose_name="صورة القسم")
    image_url = models.CharField(max_length=500, blank=True, validators=[validate_image_source], verbose_name="رابط صورة القسم")
    video = models.FileField(upload_to="home-sections/videos/", storage=home_video_storage, blank=True, null=True, validators=video_validators, verbose_name="فيديو القسم")
    video_url = models.CharField(max_length=500, blank=True, validators=[validate_video_source], verbose_name="رابط فيديو القسم")
    mobile_video = models.FileField(upload_to="home-sections/videos/mobile/", storage=home_video_storage, blank=True, null=True, validators=video_validators, verbose_name="فيديو الجوال")
    mobile_video_url = models.CharField(max_length=500, blank=True, validators=[validate_video_source], verbose_name="رابط فيديو الجوال")
    poster = models.ImageField(upload_to="home-sections/posters/", blank=True, null=True, verbose_name="صورة انتظار الفيديو")
    poster_url = models.CharField(max_length=500, blank=True, validators=[validate_image_source], verbose_name="رابط صورة انتظار الفيديو")
    media_alt = models.CharField(max_length=220, blank=True, verbose_name="وصف الصورة أو الفيديو")
    overlay_opacity = models.PositiveSmallIntegerField(
        default=62,
        validators=[MinValueValidator(0), MaxValueValidator(95)],
        verbose_name="تعتيم الوسائط (%)",
    )
    theme = models.CharField(max_length=12, choices=THEME_CHOICES, default="paper", verbose_name="نمط القسم")
    sort_order = models.PositiveSmallIntegerField(default=0, verbose_name="ترتيب القسم")
    is_visible = models.BooleanField(default=True, verbose_name="إظهار القسم")

    class Meta:
        verbose_name = "قسم ثابت في الرئيسية"
        verbose_name_plural = "أقسام الصفحة الرئيسية"
        ordering = ["sort_order", "key"]
        indexes = [models.Index(fields=["is_visible", "sort_order"], name="home_section_visible_idx")]

    def __str__(self):
        return self.get_key_display()

    def clean(self):
        super().clean()
        if self.key == "hero":
            self.is_visible = True
            self.sort_order = 0
        validate_media_pair(self, "image", "image_url", "صورة القسم")
        validate_media_pair(self, "video", "video_url", "فيديو القسم")
        validate_media_pair(self, "mobile_video", "mobile_video_url", "فيديو الجوال")
        validate_media_pair(self, "poster", "poster_url", "صورة انتظار الفيديو")
        # The featured-project button can intentionally inherit the selected project's URL.
        if self.key != "feature" or self.primary_cta_url:
            validate_cta_pair(self, "primary_cta_label", "primary_cta_url", "الزر الرئيسي")
        validate_cta_pair(self, "secondary_cta_label", "secondary_cta_url", "الزر الثاني")
        if (self.video or self.video_url) and (self.image or self.image_url):
            raise ValidationError("اختر صورة القسم أو فيديو القسم. استخدم Poster كصورة احتياطية للفيديو.")
        validate_home_media_repetition(self)

    def save(self, *args, **kwargs):
        if self.key == "hero":
            self.is_visible = True
            self.sort_order = 0
        if self.image:
            optimize_uploaded_image(self.image, max_size=(2200, 1600))
        if self.poster:
            optimize_uploaded_image(self.poster, max_size=(2200, 1600))
        super().save(*args, **kwargs)

    @property
    def image_resolved(self):
        return self.image.url if self.image else self.image_url

    @property
    def video_resolved(self):
        return self.video.url if self.video else self.video_url

    @property
    def mobile_video_resolved(self):
        return self.mobile_video.url if self.mobile_video else self.mobile_video_url

    @property
    def poster_resolved(self):
        return self.poster.url if self.poster else self.poster_url


class HomeSectionMedia(TimeStampedModel):
    MEDIA_CHOICES = [
        ("text", "نص أو خطوة"),
        ("image", "صورة"),
        ("video", "فيديو"),
    ]
    video_validators = [
        FileExtensionValidator(allowed_extensions=["mp4", "webm", "mov"]),
        validate_home_video_size,
    ]

    section = models.ForeignKey(HomeSection, on_delete=models.CASCADE, related_name="items", verbose_name="القسم")
    media_type = models.CharField(max_length=10, choices=MEDIA_CHOICES, default="text", verbose_name="نوع العنصر")
    label = models.CharField(max_length=140, blank=True, verbose_name="التصنيف أو الرقم")
    title = models.CharField(max_length=240, verbose_name="العنوان")
    description = models.TextField(blank=True, verbose_name="الوصف")
    alt_text = models.CharField(max_length=220, blank=True, verbose_name="الوصف البديل")
    image = models.ImageField(upload_to="home-sections/items/images/", blank=True, null=True, verbose_name="الصورة")
    image_url = models.CharField(max_length=500, blank=True, validators=[validate_image_source], verbose_name="رابط الصورة")
    video = models.FileField(upload_to="home-sections/items/videos/", storage=home_video_storage, blank=True, null=True, validators=video_validators, verbose_name="الفيديو")
    video_url = models.CharField(max_length=500, blank=True, validators=[validate_video_source], verbose_name="رابط الفيديو")
    mobile_video = models.FileField(upload_to="home-sections/items/videos/mobile/", storage=home_video_storage, blank=True, null=True, validators=video_validators, verbose_name="فيديو الجوال")
    mobile_video_url = models.CharField(max_length=500, blank=True, validators=[validate_video_source], verbose_name="رابط فيديو الجوال")
    poster = models.ImageField(upload_to="home-sections/items/posters/", blank=True, null=True, verbose_name="صورة انتظار الفيديو")
    poster_url = models.CharField(max_length=500, blank=True, validators=[validate_image_source], verbose_name="رابط صورة انتظار الفيديو")
    link_label = models.CharField(max_length=80, blank=True, verbose_name="نص الرابط")
    link_url = models.CharField(max_length=500, blank=True, validators=[validate_link_target], verbose_name="الرابط")
    sort_order = models.PositiveSmallIntegerField(default=0, verbose_name="الترتيب")
    is_active = models.BooleanField(default=True, verbose_name="إظهار العنصر")

    class Meta:
        verbose_name = "عنصر داخل قسم رئيسي"
        verbose_name_plural = "عناصر أقسام الرئيسية"
        ordering = ["section__sort_order", "sort_order", "id"]
        indexes = [models.Index(fields=["section", "is_active", "sort_order"], name="home_media_active_idx")]

    def __str__(self):
        return f"{self.section.get_key_display()} — {self.title}"

    def clean(self):
        super().clean()
        validate_media_pair(self, "image", "image_url", "الصورة")
        validate_media_pair(self, "video", "video_url", "الفيديو")
        validate_media_pair(self, "mobile_video", "mobile_video_url", "فيديو الجوال")
        validate_media_pair(self, "poster", "poster_url", "صورة انتظار الفيديو")
        validate_cta_pair(self, "link_label", "link_url", "الرابط")
        if self.media_type == "image" and not (self.image or self.image_url):
            raise ValidationError("عنصر الصورة يحتاج صورة مرفوعة أو رابط صورة.")
        if self.media_type == "video" and not (self.video or self.video_url):
            raise ValidationError("عنصر الفيديو يحتاج فيديو مرفوع أو رابط فيديو.")
        has_image = bool(self.image or self.image_url)
        has_video = bool(self.video or self.video_url or self.mobile_video or self.mobile_video_url or self.poster or self.poster_url)
        if self.media_type == "text" and (has_image or has_video):
            raise ValidationError("عنصر النص لا يعرض وسائط. اختر نوع صورة أو فيديو قبل الرفع.")
        if self.media_type == "image" and has_video:
            raise ValidationError("عنصر الصورة لا يعرض حقول الفيديو. غيّر نوع العنصر أو امسح الفيديو.")
        if self.media_type == "video" and has_image:
            raise ValidationError("للفيديو استخدم Poster كصورة انتظار، واترك حقل الصورة فارغًا.")
        validate_home_media_repetition(self)

    def save(self, *args, **kwargs):
        if self.image:
            optimize_uploaded_image(self.image, max_size=(1800, 1800))
        if self.poster:
            optimize_uploaded_image(self.poster, max_size=(1800, 1800))
        super().save(*args, **kwargs)

    @property
    def image_resolved(self):
        return self.image.url if self.image else self.image_url

    @property
    def video_resolved(self):
        return self.video.url if self.video else self.video_url

    @property
    def mobile_video_resolved(self):
        return self.mobile_video.url if self.mobile_video else self.mobile_video_url

    @property
    def poster_resolved(self):
        return self.poster.url if self.poster else self.poster_url


class LibraryImage(TimeStampedModel):
    CATEGORY_CHOICES = [
        ("shades", "تصميم حدائق"),
        ("fencing", "لاندسكيب صلب"),
        ("palm", "أشجار ونخيل"),
        ("traditional", "أنظمة ري وصيانة"),
        ("general", "عام"),
    ]
    USAGE_GROUP_CHOICES = [
        ("home_hero", "هيرو الرئيسية"),
        ("home_gallery", "معرض الرئيسية"),
        ("home_banners", "بنرات الرئيسية"),
        ("about", "من نحن"),
        ("services", "الخدمات"),
        ("portfolio", "الأعمال"),
        ("cities", "المدن"),
        ("blog", "المدونة"),
        ("blog_post", "تفاصيل المقال"),
        ("contact", "اتصل بنا"),
        ("city", "صفحة المدينة"),
        ("city_service", "خدمة داخل مدينة"),
    ]

    source_name = models.CharField(max_length=255, unique=True, blank=True, help_text="اسم الملف الأصلي داخل مجلد imge")
    title = models.CharField(max_length=180)
    alt_text = models.CharField(max_length=220, blank=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default="general")
    usage_group = models.CharField(max_length=30, choices=USAGE_GROUP_CHOICES, default="home_gallery")
    image = models.ImageField(upload_to="library-images/", blank=True, null=True)
    image_data = models.BinaryField(blank=True, null=True, editable=False)
    image_stored = models.BooleanField(default=False, editable=False)
    image_content_type = models.CharField(max_length=80, blank=True, editable=False)
    image_filename = models.CharField(max_length=255, blank=True, editable=False)
    external_url = models.CharField(max_length=500, blank=True, validators=[validate_image_source])
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "صورة مكتبة الموقع"
        verbose_name_plural = "صور مكتبة الموقع"
        ordering = ["usage_group", "sort_order", "title"]
        indexes = [
            models.Index(fields=["usage_group", "is_active", "sort_order"], name="library_usage_active_idx"),
            models.Index(fields=["category", "is_active"], name="library_category_idx"),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if self.image and not getattr(self.image, "_committed", True):
            # FileField applies upload_to during storage save. Keep only the basename here
            # to avoid producing library-images/library-images/... paths.
            self.image.name = PurePath(str(self.image.name).replace("\\", "/")).name
            optimize_uploaded_image(self.image)
            # New uploads stay in object/file storage. Legacy database blobs remain readable
            # but are no longer duplicated on every save.
            self.image_stored = False
        super().save(*args, **kwargs)

    def store_image_in_database(self):
        if not self.image:
            return

        data = b""
        try:
            self.image.open("rb")
            data = self.image.read()
            self.image.close()
        except Exception:
            try:
                with default_storage.open(self.image.name, "rb") as image_file:
                    data = image_file.read()
            except Exception:
                data = b""

        if not data:
            return

        filename = PurePath(self.image.name).name or self.source_name or "library-image.jpg"
        content_type = mimetypes.guess_type(filename)[0] or "image/jpeg"
        self.image_data = data
        self.image_stored = True
        self.image_filename = filename
        self.image_content_type = content_type

    @property
    def image_url(self):
        if self.image:
            return self.image.url
        if self.image_stored and self.pk:
            filename = self.image_filename or PurePath(self.source_name or "image.jpg").name
            return f"/media-db/library-images/{self.pk}/{filename}"
        if self.external_url:
            return self.external_url
        if self.source_name:
            return static(self.source_name)
        return ""

    @property
    def display_alt(self):
        return self.alt_text or self.title


class MediaFolder(TimeStampedModel):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)
    parent = models.ForeignKey("self", on_delete=models.CASCADE, blank=True, null=True, related_name="children")

    class Meta:
        verbose_name = "مجلد وسائط"
        verbose_name_plural = "مجلدات الوسائط"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Page(TimeStampedModel, SeoFields):
    TEMPLATE_CHOICES = [
        ("home", "الرئيسية"),
        ("about", "من نحن"),
        ("services", "الخدمات"),
        ("portfolio", "الأعمال"),
        ("cities", "المدن"),
        ("blog", "المدونة"),
        ("contact", "اتصل بنا"),
        ("custom", "صفحة مخصصة"),
    ]

    title = models.CharField(max_length=180)
    slug = models.SlugField(max_length=180, unique=True)
    menu_title = models.CharField(max_length=120, blank=True)
    hero_title = models.CharField(max_length=255, blank=True)
    intro_text = models.TextField(blank=True)
    body = models.TextField(blank=True)
    template_key = models.CharField(max_length=30, choices=TEMPLATE_CHOICES, default="custom")
    custom_url = models.CharField(max_length=180, blank=True, help_text="مثال: offers أو about-us")
    is_visible = models.BooleanField(default=True)
    show_in_menu = models.BooleanField(default=True)
    menu_order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "صفحة"
        verbose_name_plural = "الصفحات"
        ordering = ["menu_order", "title"]
        constraints = [
            models.UniqueConstraint(
                fields=["custom_url"],
                condition=~models.Q(custom_url=""),
                name="unique_nonempty_page_custom_url",
            )
        ]

    def __str__(self):
        return self.title

    def clean(self):
        super().clean()
        custom_url = (self.custom_url or "").strip().strip("/")
        if custom_url and ("/" in custom_url or "://" in custom_url or "?" in custom_url or "#" in custom_url):
            raise ValidationError("الرابط المخصص يجب أن يكون مقطعًا واحدًا مثل offers أو about-us بدون / أو معاملات URL.")
        self.custom_url = custom_url

    @property
    def resolved_path(self):
        return self.custom_url or self.slug


class City(TimeStampedModel, SeoFields):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)
    region = models.CharField(max_length=120, blank=True)
    short_description = models.TextField(blank=True)
    content = models.TextField(blank=True)
    hero_title = models.CharField(max_length=255, blank=True)
    primary_color = models.CharField(max_length=7, blank=True)
    secondary_color = models.CharField(max_length=7, blank=True)
    accent_color = models.CharField(max_length=7, blank=True)
    background_color = models.CharField(max_length=7, blank=True)
    is_active = models.BooleanField(default=True)
    is_system = models.BooleanField(
        default=False,
        editable=False,
        help_text="مدينة أساسية ثابتة لا يمكن حذفها من لوحة التحكم.",
    )
    auto_generate_service_pages = models.BooleanField(default=True)

    class Meta:
        verbose_name = "مدينة"
        verbose_name_plural = "المدن"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def delete(self, *args, **kwargs):
        if self.is_system:
            raise ProtectedError("المدن الأساسية ثابتة ولا يمكن حذفها.", [self])
        return super().delete(*args, **kwargs)


class District(TimeStampedModel):
    city = models.ForeignKey(City, on_delete=models.PROTECT, related_name="districts")
    name = models.CharField(max_length=140)
    slug = models.SlugField(max_length=160, allow_unicode=True)
    is_active = models.BooleanField(default=True)
    is_system = models.BooleanField(default=False, editable=False)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "حي"
        verbose_name_plural = "الأحياء"
        ordering = ["city__name", "sort_order", "name"]
        constraints = [
            models.UniqueConstraint(fields=["city", "name"], name="unique_district_name_per_city"),
            models.UniqueConstraint(fields=["city", "slug"], name="unique_district_slug_per_city"),
        ]
        indexes = [models.Index(fields=["city", "is_active", "sort_order"], name="district_city_active_idx")]

    def __str__(self):
        return f"{self.name} - {self.city.name}"

    def delete(self, *args, **kwargs):
        if self.is_system:
            raise ProtectedError("الأحياء الأساسية ثابتة ولا يمكن حذفها.", [self])
        return super().delete(*args, **kwargs)


class ServiceCategory(TimeStampedModel, SeoFields):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True, allow_unicode=True)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name = "تصنيف خدمة"
        verbose_name_plural = "تصنيفات الخدمات"
        ordering = ["name"]

    def __str__(self):
        return self.name


class ServiceTag(TimeStampedModel, SeoFields):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True, allow_unicode=True)

    class Meta:
        verbose_name = "وسم خدمة"
        verbose_name_plural = "وسوم الخدمات"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Service(TimeStampedModel, SeoFields):
    title = models.CharField(max_length=180)
    slug = models.SlugField(max_length=140, unique=True)
    short_title = models.CharField(max_length=180, blank=True)
    description = models.TextField()
    benefits = models.TextField(blank=True, help_text="أدخل ميزة في كل سطر")
    image = models.ImageField(upload_to="services/", blank=True, null=True)
    image_url = models.CharField(max_length=500, blank=True, validators=[validate_image_source])
    category = models.ForeignKey(
        ServiceCategory,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="services",
    )
    tags = models.ManyToManyField(ServiceTag, blank=True, related_name="services")
    primary_city = models.ForeignKey(
        City,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="primary_services",
        verbose_name="المدينة الأساسية",
    )
    primary_district = models.ForeignKey(
        District,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="primary_services",
        verbose_name="الحي الأساسي",
    )
    cities = models.ManyToManyField(City, blank=True, related_name="services")
    auto_classify = models.BooleanField(default=True, help_text="إنشاء التصنيف والوسوم تلقائيًا عند تركها فارغة.")
    auto_distribute = models.BooleanField(default=True, help_text="اختيار مدينة وحي تلقائيًا عند تركهما فارغين.")
    is_visible = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "خدمة"
        verbose_name_plural = "الخدمات"
        ordering = ["display_order", "title"]

    def __str__(self):
        return self.title

    def clean(self):
        super().clean()
        if self.primary_district_id and self.primary_city_id and self.primary_district.city_id != self.primary_city_id:
            raise ValidationError("الحي المختار لا يتبع المدينة الأساسية.")

    def save(self, *args, **kwargs):
        from .content_automation import classify_service

        if self.primary_district_id and self.primary_city_id and self.primary_district.city_id != self.primary_city_id:
            self.primary_district = None
        classify_service(self)
        if self.image:
            optimize_uploaded_image(self.image)
        super().save(*args, **kwargs)
        if self.primary_city_id and not self.cities.filter(pk=self.primary_city_id).exists():
            self.cities.add(self.primary_city_id)

    @property
    def benefits_list(self):
        return [item.strip() for item in self.benefits.splitlines() if item.strip()]

    @property
    def resolved_image(self):
        if self.image:
            return self.image.url
        return self.image_url


class CityServicePage(TimeStampedModel, SeoFields):
    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name="city_services")
    district = models.ForeignKey(
        District,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="local_service_pages",
        verbose_name="الحي الموزع عليه",
    )
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="city_pages")
    hero_title = models.CharField(max_length=255, blank=True)
    content = models.TextField()
    benefits = models.TextField(blank=True, help_text="أدخل ميزة في كل سطر")
    is_active = models.BooleanField(default=True)
    custom_slug = models.SlugField(max_length=160, blank=True)

    class Meta:
        verbose_name = "خدمة داخل مدينة"
        verbose_name_plural = "الخدمات داخل المدن"
        unique_together = ("city", "service")
        ordering = ["city__name", "service__title"]
        indexes = [
            models.Index(fields=["city", "is_active"], name="city_service_active_idx"),
            models.Index(fields=["city", "district", "is_active"], name="citysvc_district_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["city", "custom_slug"],
                condition=~models.Q(custom_slug=""),
                name="unique_city_custom_service_slug",
            )
        ]

    def __str__(self):
        return f"{self.service.title} - {self.city.name}"

    def clean(self):
        super().clean()
        if self.district_id and self.city_id and self.district.city_id != self.city_id:
            raise ValidationError("الحي المختار لا يتبع مدينة صفحة الخدمة.")

    def save(self, *args, **kwargs):
        from .content_automation import choose_district

        if self.district_id and self.city_id and self.district.city_id != self.city_id:
            self.district = None
        if self.city_id and not self.district_id:
            self.district = choose_district(self.city, "local_service_pages")
        if not self.hero_title:
            self.hero_title = f"{self.service.title} في {self.city.name}"
        if not self.custom_slug:
            self.custom_slug = self.service.slug
        self.content = sanitize_html(self.content)
        super().save(*args, **kwargs)

    @property
    def benefits_list(self):
        return [item.strip() for item in self.benefits.splitlines() if item.strip()]


class BlogCategory(TimeStampedModel):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True, allow_unicode=True)
    description = models.TextField(blank=True)
    meta_title = models.CharField(max_length=255, blank=True)
    meta_description = models.TextField(blank=True)

    class Meta:
        verbose_name = "تصنيف مقال"
        verbose_name_plural = "تصنيفات المقالات"
        ordering = ["name"]

    def __str__(self):
        return self.name


class BlogTag(TimeStampedModel):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True, allow_unicode=True)
    meta_title = models.CharField(max_length=255, blank=True)
    meta_description = models.TextField(blank=True)

    class Meta:
        verbose_name = "وسم"
        verbose_name_plural = "الوسوم"
        ordering = ["name"]

    def __str__(self):
        return self.name


class BlogPost(TimeStampedModel, SeoFields):
    STATUS_CHOICES = [
        ("draft", "مسودة"),
        ("published", "منشور"),
    ]

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    excerpt = models.TextField(blank=True)
    content = models.TextField()
    featured_image = models.ImageField(upload_to="blog/", blank=True, null=True)
    featured_image_url = models.CharField(max_length=500, blank=True, validators=[validate_image_source])
    category = models.ForeignKey(BlogCategory, on_delete=models.SET_NULL, blank=True, null=True, related_name="posts")
    tags = models.ManyToManyField(BlogTag, blank=True, related_name="posts")
    city = models.ForeignKey(City, on_delete=models.SET_NULL, blank=True, null=True, related_name="blog_posts")
    district = models.ForeignKey(District, on_delete=models.SET_NULL, blank=True, null=True, related_name="blog_posts")
    auto_classify = models.BooleanField(default=True, help_text="إنشاء التصنيف والوسوم تلقائيًا عند تركها فارغة.")
    auto_distribute = models.BooleanField(default=True, help_text="توزيع المقال تلقائيًا على مدينة وحي عند تركهما فارغين.")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    is_featured = models.BooleanField(default=False)
    publish_at = models.DateTimeField(blank=True, null=True)
    view_count = models.PositiveIntegerField(default=0)
    total_read_seconds = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "مقال"
        verbose_name_plural = "المقالات"
        ordering = ["-publish_at", "-created_at"]
        indexes = [
            models.Index(fields=["status", "publish_at"], name="blog_status_publish_idx"),
            models.Index(fields=["is_featured", "publish_at"], name="blog_featured_publish_idx"),
            models.Index(fields=["city", "district", "status"], name="blog_location_status_idx"),
        ]

    def __str__(self):
        return self.title

    def clean(self):
        super().clean()
        if self.district_id and self.city_id and self.district.city_id != self.city_id:
            raise ValidationError("الحي المختار لا يتبع مدينة المقال.")

    def save(self, *args, **kwargs):
        from .content_automation import classify_blog_post

        if self.district_id and self.city_id and self.district.city_id != self.city_id:
            self.district = None
        classify_blog_post(self)
        self.content = sanitize_html(self.content)
        if self.featured_image:
            optimize_uploaded_image(self.featured_image)
        super().save(*args, **kwargs)

    @property
    def image_url(self):
        if self.featured_image:
            return self.featured_image.url
        return self.featured_image_url

    @property
    def is_published(self):
        return self.status == "published"

    @property
    def reading_time_minutes(self):
        words = len((self.content or "").split())
        return max(1, round(words / 200))

    @property
    def seo_score(self):
        score = 0
        if self.meta_title:
            score += 30
        if self.meta_description:
            score += 25
        if self.meta_keywords:
            score += 15
        if len((self.content or "").split()) > 300:
            score += 20
        if self.featured_image or self.featured_image_url:
            score += 10
        return min(score, 100)

    @property
    def avg_read_seconds(self):
        return self.total_read_seconds // self.view_count if self.view_count else 0


class BlogComment(TimeStampedModel):
    post = models.ForeignKey(BlogPost, on_delete=models.CASCADE, related_name="comments")
    author_name = models.CharField(max_length=120)
    author_email = models.EmailField(blank=True)
    content = models.TextField()
    is_approved = models.BooleanField(default=False)
    is_spam = models.BooleanField(default=False)

    class Meta:
        verbose_name = "تعليق"
        verbose_name_plural = "التعليقات"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.author_name} - {self.post.title}"

    def save(self, *args, **kwargs):
        text = (self.content or "").lower()
        if text.count("http") > 1 or text.count("www.") > 1:
            self.is_spam = True
            self.is_approved = False
        super().save(*args, **kwargs)


class Project(TimeStampedModel, SeoFields):
    CATEGORY_CHOICES = [
        ("shades", "تصميم حدائق"),
        ("fencing", "لاندسكيب صلب"),
        ("palm", "أشجار ونخيل"),
        ("traditional", "أنظمة ري وصيانة"),
    ]
    RECORD_TYPE_CHOICES = [
        ("portfolio", "عمل مصوّر / مشروع"),
        ("local_solution", "نموذج حل محلي"),
    ]

    title = models.CharField(max_length=180)
    slug = models.SlugField(max_length=180, unique=True)
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES)
    city = models.ForeignKey(City, on_delete=models.SET_NULL, blank=True, null=True, related_name="projects")
    district = models.ForeignKey(District, on_delete=models.SET_NULL, blank=True, null=True, related_name="projects")
    coverage_city = models.ForeignKey(
        City, on_delete=models.SET_NULL, blank=True, null=True, related_name="coverage_projects",
        verbose_name="مدينة نطاق الخدمة",
        help_text="مدينة يظهر المشروع ضمن تغطيتها دون الادعاء أن التنفيذ تم فيها.",
    )
    coverage_district = models.ForeignKey(
        District, on_delete=models.SET_NULL, blank=True, null=True, related_name="coverage_projects",
        verbose_name="حي نطاق الخدمة",
        help_text="حي يظهر المشروع ضمن نطاق خدمته. لا يعني أن المشروع نُفذ فعليًا في الحي.",
    )
    record_type = models.CharField(max_length=30, choices=RECORD_TYPE_CHOICES, default="portfolio", verbose_name="نوع السجل")
    is_indexable = models.BooleanField(
        default=True, verbose_name="السماح بالفهرسة",
        help_text="عطّل الفهرسة للنماذج المحلية المتكررة مع إبقائها قابلة للتصفح.",
    )
    description = models.TextField()
    featured_image = models.ImageField(upload_to="projects/", blank=True, null=True)
    featured_image_url = models.CharField(max_length=500, blank=True, validators=[validate_image_source])
    is_visible = models.BooleanField(default=True)

    class Meta:
        verbose_name = "مشروع"
        verbose_name_plural = "المشاريع"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["is_visible", "created_at"], name="project_visible_date_idx"),
            models.Index(fields=["city", "district", "is_visible"], name="project_location_idx"),
        ]

    def __str__(self):
        return self.title

    def clean(self):
        super().clean()
        if self.district_id and self.city_id and self.district.city_id != self.city_id:
            raise ValidationError("الحي المختار لا يتبع مدينة المشروع.")
        if self.coverage_district_id and self.coverage_city_id and self.coverage_district.city_id != self.coverage_city_id:
            raise ValidationError("حي نطاق الخدمة لا يتبع مدينة نطاق الخدمة.")

    def save(self, *args, **kwargs):
        from .content_automation import classify_project

        if self.district_id and self.city_id and self.district.city_id != self.city_id:
            self.district = None
        if self.coverage_district_id and self.coverage_city_id and self.coverage_district.city_id != self.coverage_city_id:
            self.coverage_district = None
        classify_project(self)
        if self.featured_image:
            optimize_uploaded_image(self.featured_image)
        super().save(*args, **kwargs)

    @property
    def image_url(self):
        if self.featured_image:
            return self.featured_image.url
        return self.featured_image_url


class ProjectImage(TimeStampedModel):
    TYPE_CHOICES = [
        ("before", "قبل"),
        ("after", "بعد"),
        ("gallery", "معرض"),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="gallery")
    title = models.CharField(max_length=150, blank=True)
    image_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default="gallery")
    image = models.ImageField(upload_to="projects/gallery/", blank=True, null=True)
    external_url = models.CharField(max_length=500, blank=True, validators=[validate_image_source])
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "صورة مشروع"
        verbose_name_plural = "صور المشاريع"
        ordering = ["sort_order", "-created_at"]

    def __str__(self):
        return self.title or f"صورة {self.project.title}"

    def clean(self):
        if not self.image and not self.external_url:
            raise ValidationError("يجب رفع صورة أو إضافة رابط خارجي.")

    def save(self, *args, **kwargs):
        if self.image:
            optimize_uploaded_image(self.image)
        super().save(*args, **kwargs)

    @property
    def image_url(self):
        if self.image:
            return self.image.url
        return self.external_url


class Lead(TimeStampedModel):
    STATUS_CHOICES = [
        ("new", "جديد"),
        ("contacted", "تم التواصل"),
        ("site_visit", "تم تحديد معاينة"),
        ("quote_sent", "تم إرسال عرض السعر"),
        ("negotiating", "تفاوض"),
        ("won", "تم التعاقد"),
        ("lost", "لم يتم التعاقد"),
        ("closed", "مغلق"),
    ]
    SOURCE_CHOICES = [
        ("website", "الموقع"),
        ("whatsapp", "واتساب"),
        ("call", "اتصال"),
        ("manual", "إدخال يدوي"),
    ]

    name = models.CharField(max_length=120)
    phone = models.CharField(max_length=20)
    city_name = models.CharField(max_length=120, blank=True)
    district_name = models.CharField(max_length=140, blank=True)
    message = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="new")
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default="website")
    page_url = models.URLField(blank=True)
    utm_source = models.CharField(max_length=120, blank=True)
    utm_medium = models.CharField(max_length=120, blank=True)
    utm_campaign = models.CharField(max_length=160, blank=True)
    follow_up_at = models.DateTimeField(blank=True, null=True)
    estimated_value = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "طلب عميل"
        verbose_name_plural = "طلبات العملاء"
        ordering = ["status", "-created_at"]
        indexes = [models.Index(fields=["status", "created_at"], name="lead_status_date_idx")]

    def __str__(self):
        return f"{self.name} - {self.phone}"


class ConversionEvent(TimeStampedModel):
    EVENT_CHOICES = [
        ("whatsapp", "واتساب"),
        ("call", "اتصال"),
        ("calculator", "حاسبة تكلفة"),
        ("exit_intent", "نافذة خروج"),
    ]

    event_type = models.CharField(max_length=30, choices=EVENT_CHOICES)
    page_url = models.URLField(blank=True)
    label = models.CharField(max_length=160, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "حدث تحويل"
        verbose_name_plural = "تتبع التحويلات"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["event_type", "created_at"], name="conversion_event_date_idx")]

    def __str__(self):
        return f"{self.get_event_type_display()} - {self.created_at:%Y-%m-%d %H:%M}"


class Testimonial(TimeStampedModel):
    name = models.CharField(max_length=120)
    city_name = models.CharField(max_length=120, blank=True)
    rating = models.PositiveSmallIntegerField(default=5, validators=[MinValueValidator(1), MaxValueValidator(5)])
    review = models.TextField()
    source = models.CharField(max_length=120, blank=True, help_text="مثال: Google Business Profile أو عميل مباشر")
    source_url = models.URLField(blank=True)
    is_verified = models.BooleanField(default=False)
    is_visible = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "تقييم عميل"
        verbose_name_plural = "تقييمات العملاء"
        ordering = ["display_order", "-created_at"]

    def __str__(self):
        return self.name


class NavigationItem(TimeStampedModel):
    label = models.CharField(max_length=120)
    route_name = models.CharField(max_length=80, blank=True, help_text="مثل home أو contact")
    external_url = models.URLField(blank=True)
    linked_page = models.ForeignKey(Page, on_delete=models.SET_NULL, blank=True, null=True, related_name="nav_items")
    sort_order = models.PositiveIntegerField(default=0)
    is_visible = models.BooleanField(default=True)
    open_in_new_tab = models.BooleanField(default=False)

    class Meta:
        verbose_name = "عنصر قائمة"
        verbose_name_plural = "عناصر القائمة"
        ordering = ["sort_order", "label"]

    def __str__(self):
        return self.label

    def clean(self):
        targets = [bool(self.route_name), bool(self.external_url), bool(self.linked_page)]
        if sum(targets) != 1:
            raise ValidationError("حدد وجهة واحدة فقط: رابط داخلي أو خارجي أو صفحة مرتبطة.")


class AIContentGenerationLog(TimeStampedModel):
    CONTENT_TYPE_CHOICES = [
        ("blog_post", "مقال"),
        ("service", "خدمة"),
        ("city", "مدينة"),
        ("page", "صفحة"),
        ("city_service", "خدمة داخل مدينة"),
    ]
    MODE_CHOICES = [
        ("create", "إنشاء"),
        ("update", "تحديث"),
    ]
    STATUS_CHOICES = [
        ("pending", "قيد التنفيذ"),
        ("completed", "مكتمل"),
        ("failed", "فشل"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name="ai_content_logs")
    content_type = models.CharField(max_length=30, choices=CONTENT_TYPE_CHOICES)
    mode = models.CharField(max_length=20, choices=MODE_CHOICES, default="create")
    prompt = models.TextField()
    title_hint = models.CharField(max_length=255, blank=True)
    image_count = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    input_payload = models.JSONField(default=dict, blank=True)
    generated_payload = models.JSONField(default=dict, blank=True)
    target_object_type = models.CharField(max_length=100, blank=True)
    target_object_id = models.PositiveIntegerField(blank=True, null=True)
    error_message = models.TextField(blank=True)

    class Meta:
        verbose_name = "سجل إنشاء محتوى بالذكاء الاصطناعي"
        verbose_name_plural = "سجلات إنشاء المحتوى بالذكاء الاصطناعي"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_content_type_display()} - {self.get_mode_display()} - {self.created_at:%Y-%m-%d %H:%M}"


class SiteVerification(TimeStampedModel):
    PROVIDER_CHOICES = [
        ("google", "Google Search Console"),
        ("bing", "Bing Webmaster Tools"),
        ("yandex", "Yandex"),
        ("custom", "كود مخصص"),
    ]
    METHOD_CHOICES = [
        ("html_tag", "وسم HTML داخل <head>"),
        ("html_file", "ملف HTML في جذر الموقع"),
        ("dns_txt", "سجل DNS TXT"),
        ("dns_cname", "سجل DNS CNAME"),
        ("google_analytics", "Google Analytics"),
        ("google_tag_manager", "Google Tag Manager"),
    ]
    provider = models.CharField(max_length=30, choices=PROVIDER_CHOICES, default="google")
    verification_method = models.CharField(
        max_length=30,
        choices=METHOD_CHOICES,
        default="html_tag",
        verbose_name="طريقة التحقق",
        help_text="اختر الطريقة نفسها التي يعرضها Google Search Console.",
    )
    name = models.CharField(
        max_length=255,
        default="google-site-verification",
        verbose_name="الاسم / المضيف / اسم الملف",
        help_text=(
            "HTML tag: اترك google-site-verification. HTML file: اسم الملف مثل google123.html. "
            "DNS: اسم/Host السجل. Analytics/Tag Manager: يمكن تركه كما هو."
        ),
    )
    content = models.TextField(
        blank=True,
        verbose_name="قيمة التحقق",
        help_text=(
            "الصق Token الوسم، أو محتوى ملف HTML كما هو، أو قيمة DNS، أو Measurement ID مثل G-XXXX، "
            "أو Container ID مثل GTM-XXXX."
        ),
    )
    raw_html = models.TextField(
        blank=True,
        help_text="اختياري للأكواد المخصصة فقط. لا تضع أسرار API هنا.",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "إثبات ملكية الموقع"
        verbose_name_plural = "إثبات ملكية الموقع"
        ordering = ["provider", "verification_method", "name"]

    def clean(self):
        super().clean()
        method = self.verification_method
        if method == "html_tag":
            self.name = "google-site-verification"
            if not self.content.strip():
                raise ValidationError("ألصق قيمة content الخاصة بوسم التحقق.")
        elif method == "html_file":
            self.name = (self.name or "").strip()
            if not re.fullmatch(r"google[A-Za-z0-9_-]{6,180}\.html", self.name, flags=re.IGNORECASE):
                raise ValidationError("أدخل اسم ملف Google كما هو، مثل google123456.html، بدون مسار أو تغيير الاسم.")
            if not self.content.strip():
                raise ValidationError("ألصق محتوى ملف التحقق كما نزّلته من Search Console دون تعديل.")
        elif method in {"dns_txt", "dns_cname"}:
            if not self.content.strip():
                raise ValidationError("ألصق قيمة سجل DNS التي أعطاها Search Console.")
        elif method == "google_analytics":
            value = self.content.strip().upper()
            if not value.startswith(("G-", "GT-")):
                raise ValidationError("أدخل Measurement ID صحيحًا مثل G-XXXXXXXXXX.")
            self.content = value
        elif method == "google_tag_manager":
            value = self.content.strip().upper()
            if not value.startswith("GTM-"):
                raise ValidationError("أدخل Container ID صحيحًا مثل GTM-XXXXXXX.")
            self.content = value

    def __str__(self):
        return f"{self.get_provider_display()} - {self.get_verification_method_display()}"


class SearchConsoleQuery(TimeStampedModel):
    query = models.CharField(max_length=500)
    page = models.URLField(blank=True)
    country = models.CharField(max_length=10, blank=True)
    device = models.CharField(max_length=30, blank=True)
    clicks = models.PositiveIntegerField(default=0)
    impressions = models.PositiveIntegerField(default=0)
    ctr = models.FloatField(default=0)
    position = models.FloatField(default=0)
    date_from = models.DateField(blank=True, null=True)
    date_to = models.DateField(blank=True, null=True)

    class Meta:
        verbose_name = "كلمة من Search Console"
        verbose_name_plural = "كلمات Search Console"
        ordering = ["-impressions", "position"]
        indexes = [models.Index(fields=["query", "page"])]

    def __str__(self):
        return f"{self.query} - {self.impressions}"


class SEOReportIssue(TimeStampedModel):
    SEVERITY_CHOICES = [("high", "مرتفع"), ("medium", "متوسط"), ("low", "منخفض")]
    STATUS_CHOICES = [("open", "مفتوح"), ("fixed", "تم الإصلاح"), ("ignored", "متجاهل")]
    page_url = models.CharField(max_length=500)
    title = models.CharField(max_length=255)
    issue_type = models.CharField(max_length=80)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default="medium")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="open")
    details = models.TextField(blank=True)
    suggested_fix = models.TextField(blank=True)
    detected_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "مشكلة SEO"
        verbose_name_plural = "تقرير SEO اليومي"
        ordering = ["status", "-severity", "-detected_at"]

    def __str__(self):
        return f"{self.title} - {self.page_url}"


class LegacyRedirect(TimeStampedModel):
    old_path = models.CharField(max_length=255, unique=True, help_text="مثال: /riyadh/shades/")
    target_path = models.CharField(max_length=255, help_text="مثال: /riyadh/landscaping/")
    is_permanent = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    hit_count = models.PositiveIntegerField(default=0)
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "تحويل رابط قديم"
        verbose_name_plural = "تحويلات الروابط القديمة"
        ordering = ["old_path"]

    def __str__(self):
        return f"{self.old_path} -> {self.target_path}"


class SEOAutomationRun(TimeStampedModel):
    STATUS_CHOICES = [
        ("running", "قيد التشغيل"),
        ("completed", "مكتمل"),
        ("failed", "فشل"),
        ("skipped", "متجاوز"),
    ]
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="running")
    search_console_result = models.JSONField(default=dict, blank=True)
    local_seo_result = models.JSONField(default=dict, blank=True)
    redirects_result = models.JSONField(default=dict, blank=True)
    issues_before = models.PositiveIntegerField(default=0)
    issues_after = models.PositiveIntegerField(default=0)
    ai_requested = models.BooleanField(default=False)
    ai_applied = models.BooleanField(default=False)
    ai_result = models.JSONField(default=dict, blank=True)
    summary = models.TextField(blank=True)
    error_message = models.TextField(blank=True)

    class Meta:
        verbose_name = "تشغيل أتمتة SEO"
        verbose_name_plural = "تشغيلات أتمتة SEO"
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.get_status_display()} - {self.started_at:%Y-%m-%d %H:%M}"
