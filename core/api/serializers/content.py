from rest_framework import serializers

from core.api.serializers.common import HTMLField, TextField, related_payload, serializer_image
from core.api.utils import clean_meta_text, clean_text, seo_payload
from core.models import (
    BlogCategory,
    BlogPost,
    BlogTag,
    City,
    CityServicePage,
    District,
    Page,
    Project,
    Service,
    ServiceCategory,
    Testimonial,
)


class PageSerializer(serializers.ModelSerializer):
    title = TextField()
    menu_title = TextField()
    hero_title = TextField()
    intro_text = TextField()
    body = HTMLField()
    url = serializers.SerializerMethodField()
    seo = serializers.SerializerMethodField()

    class Meta:
        model = Page
        fields = (
            "id", "title", "slug", "menu_title", "hero_title", "intro_text", "body",
            "template_key", "url", "created_at", "updated_at", "seo",
        )

    def get_url(self, obj):
        route_map = {
            "home": "/", "about": "/about/", "services": "/services/",
            "portfolio": "/projects/", "cities": "/cities/", "blog": "/blog/",
            "contact": "/contact/",
        }
        return route_map.get(obj.template_key, f"/pages/{obj.resolved_path.strip('/')}/")

    def get_seo(self, obj):
        return seo_payload(
            obj,
            path=self.get_url(obj),
            title=obj.title,
            description=obj.intro_text,
            request=self.context.get("request"),
            schema={"@type": "WebPage", "name": clean_text(obj.title)},
        )


class ServiceSerializer(serializers.ModelSerializer):
    title = TextField()
    short_title = TextField()
    description = HTMLField()
    benefits = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    category = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()
    primary_city = serializers.SerializerMethodField()
    primary_district = serializers.SerializerMethodField()
    cities = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()
    seo = serializers.SerializerMethodField()

    class Meta:
        model = Service
        fields = (
            "id", "title", "short_title", "slug", "description", "benefits", "image",
            "category", "tags", "primary_city", "primary_district", "cities", "url",
            "display_order", "created_at", "updated_at", "seo",
        )

    def get_benefits(self, obj):
        return [clean_text(item) for item in obj.benefits_list]

    def get_image(self, obj):
        source = obj.image if obj.image else obj.image_url
        return serializer_image(self, source, obj.title)

    def get_category(self, obj):
        return related_payload(obj.category)

    def get_tags(self, obj):
        return [related_payload(tag) for tag in obj.tags.all()]

    def get_primary_city(self, obj):
        return related_payload(obj.primary_city)

    def get_primary_district(self, obj):
        district = obj.primary_district
        if not district:
            return None
        payload = related_payload(district)
        payload["city_slug"] = district.city.slug
        return payload

    def get_cities(self, obj):
        return [related_payload(city) for city in obj.cities.all()]

    def get_url(self, obj):
        return f"/services/{obj.slug}/"

    def get_seo(self, obj):
        return seo_payload(
            obj,
            path=self.get_url(obj),
            title=obj.title,
            description=obj.description,
            image=obj.resolved_image,
            request=self.context.get("request"),
            schema={"@type": "Service", "name": clean_text(obj.title)},
        )


class ServiceCategorySerializer(serializers.ModelSerializer):
    name = TextField()
    description = TextField()
    service_count = serializers.IntegerField(read_only=True)
    url = serializers.SerializerMethodField()
    seo = serializers.SerializerMethodField()

    class Meta:
        model = ServiceCategory
        fields = (
            "id", "name", "slug", "description", "service_count", "url",
            "created_at", "updated_at", "seo",
        )

    def get_url(self, obj):
        return f"/services/category/{obj.slug}/"

    def get_seo(self, obj):
        return seo_payload(
            obj,
            path=self.get_url(obj),
            title=f"خدمات {obj.name}",
            description=obj.description or f"استعرض خدمات {obj.name} المتاحة لدى نخيل نجد.",
            request=self.context.get("request"),
            schema={"@type": "CollectionPage", "name": clean_text(f"خدمات {obj.name}")},
        )


class ProjectGallerySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = TextField()
    image_type = serializers.CharField()
    image = serializers.SerializerMethodField()

    def get_image(self, obj):
        source = obj.image if obj.image else obj.external_url
        return serializer_image(self, source, obj.title or obj.project.title)


class ProjectSerializer(serializers.ModelSerializer):
    title = TextField()
    description = HTMLField()
    category_label = TextField(source="get_category_display")
    city = serializers.SerializerMethodField()
    district = serializers.SerializerMethodField()
    coverage_city = serializers.SerializerMethodField()
    coverage_district = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    gallery = ProjectGallerySerializer(many=True, read_only=True)
    url = serializers.SerializerMethodField()
    seo = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = (
            "id", "title", "slug", "category", "category_label", "description", "city",
            "district", "coverage_city", "coverage_district", "record_type", "is_indexable",
            "image", "gallery", "url", "created_at", "updated_at", "seo",
        )

    def get_city(self, obj):
        return related_payload(obj.city)

    def get_district(self, obj):
        return related_payload(obj.district)

    def get_coverage_city(self, obj):
        return related_payload(obj.coverage_city)

    def get_coverage_district(self, obj):
        return related_payload(obj.coverage_district)

    def get_image(self, obj):
        source = obj.featured_image if obj.featured_image else obj.featured_image_url
        return serializer_image(self, source, obj.title)

    def get_url(self, obj):
        return f"/projects/{obj.slug}/"

    def get_seo(self, obj):
        return seo_payload(
            obj,
            path=self.get_url(obj),
            title=obj.title,
            description=obj.description,
            image=obj.image_url,
            request=self.context.get("request"),
            schema={
                "@type": "CreativeWork",
                "name": clean_text(obj.title),
                "additionalType": "Local service showcase" if obj.record_type == "local_solution" else "Portfolio work",
            },
            robots=("index, follow, max-image-preview:large" if obj.is_indexable else "noindex, follow"),
        )


class ServiceCardSerializer(serializers.ModelSerializer):
    """Compact service payload for cards, listings and selectors."""
    title = TextField()
    short_title = TextField()
    description = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    category = serializers.SerializerMethodField()
    primary_city = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()

    class Meta:
        model = Service
        fields = (
            "id", "title", "short_title", "slug", "description", "image",
            "category", "primary_city", "url", "display_order",
        )

    def get_description(self, obj):
        return clean_meta_text(obj.description)[:260]

    def get_image(self, obj):
        source = obj.image if obj.image else obj.image_url
        return serializer_image(self, source, obj.title)

    def get_category(self, obj):
        return related_payload(obj.category)

    def get_primary_city(self, obj):
        return related_payload(obj.primary_city)

    def get_url(self, obj):
        return f"/services/{obj.slug}/"


class ProjectCardSerializer(serializers.ModelSerializer):
    """Compact project payload that keeps location transparency metadata."""
    title = TextField()
    description = serializers.SerializerMethodField()
    category_label = TextField(source="get_category_display")
    city = serializers.SerializerMethodField()
    district = serializers.SerializerMethodField()
    coverage_city = serializers.SerializerMethodField()
    coverage_district = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = (
            "id", "title", "slug", "category", "category_label", "description",
            "city", "district", "coverage_city", "coverage_district",
            "record_type", "is_indexable", "image", "url",
        )

    def get_description(self, obj):
        return clean_meta_text(obj.description)[:280]

    def get_city(self, obj):
        return related_payload(obj.city)

    def get_district(self, obj):
        return related_payload(obj.district)

    def get_coverage_city(self, obj):
        return related_payload(obj.coverage_city)

    def get_coverage_district(self, obj):
        return related_payload(obj.coverage_district)

    def get_image(self, obj):
        source = obj.featured_image if obj.featured_image else obj.featured_image_url
        return serializer_image(self, source, obj.title)

    def get_url(self, obj):
        return f"/projects/{obj.slug}/"


class ArticleCardSerializer(serializers.ModelSerializer):
    """Compact article payload; full HTML stays on the article detail endpoint."""
    title = TextField()
    excerpt = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    category = serializers.SerializerMethodField()
    city = serializers.SerializerMethodField()
    reading_time_minutes = serializers.IntegerField(read_only=True)
    url = serializers.SerializerMethodField()
    published_at = serializers.DateTimeField(source="publish_at", allow_null=True, read_only=True)

    class Meta:
        model = BlogPost
        fields = (
            "id", "title", "slug", "excerpt", "image", "category", "city",
            "reading_time_minutes", "url", "published_at", "created_at", "updated_at",
        )

    def get_excerpt(self, obj):
        return clean_meta_text(obj.excerpt or obj.content)[:280]

    def get_image(self, obj):
        source = obj.featured_image if obj.featured_image else obj.featured_image_url
        return serializer_image(self, source, obj.title)

    def get_category(self, obj):
        return related_payload(obj.category)

    def get_city(self, obj):
        return related_payload(obj.city)

    def get_url(self, obj):
        return f"/blog/{obj.slug}/"


class CityServiceCardSerializer(serializers.ModelSerializer):
    service = ServiceCardSerializer(read_only=True)
    city = serializers.SerializerMethodField()
    district = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()

    class Meta:
        model = CityServicePage
        fields = ("id", "city", "district", "service", "url")

    def get_city(self, obj):
        return related_payload(obj.city)

    def get_district(self, obj):
        return related_payload(obj.district)

    def get_url(self, obj):
        return f"/{obj.city.slug}/{obj.custom_slug or obj.service.slug}/"


class DistrictSummarySerializer(serializers.ModelSerializer):
    name = TextField()
    url = serializers.SerializerMethodField()

    class Meta:
        model = District
        fields = ("id", "name", "slug", "sort_order", "url")

    def get_url(self, obj):
        return f"/{obj.city.slug}/districts/{obj.slug}/"


class DistrictListSerializer(serializers.ModelSerializer):
    name = TextField()
    city = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()

    class Meta:
        model = District
        fields = ("id", "name", "slug", "sort_order", "city", "url", "created_at", "updated_at")

    def get_city(self, obj):
        return related_payload(obj.city)

    def get_url(self, obj):
        return f"/{obj.city.slug}/districts/{obj.slug}/"


class HomeCitySerializer(serializers.ModelSerializer):
    """Lean city payload for the homepage; only two district links are serialized."""
    name = TextField()
    short_description = TextField()
    districts = serializers.SerializerMethodField()
    district_count = serializers.IntegerField(read_only=True)
    url = serializers.SerializerMethodField()

    class Meta:
        model = City
        fields = (
            "id", "name", "slug", "short_description", "districts", "district_count", "url",
            "primary_color", "secondary_color", "accent_color", "background_color",
        )

    def get_districts(self, obj):
        districts = obj.active_districts if hasattr(obj, "active_districts") else obj.districts.filter(is_active=True)
        return DistrictSummarySerializer(list(districts)[:2], many=True, context=self.context).data

    def get_url(self, obj):
        return f"/{obj.slug}/"


class CitySerializer(serializers.ModelSerializer):
    name = TextField()
    region = TextField()
    short_description = TextField()
    content = HTMLField()
    hero_title = TextField()
    districts = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()
    seo = serializers.SerializerMethodField()

    class Meta:
        model = City
        fields = (
            "id", "name", "slug", "region", "short_description", "content", "hero_title",
            "districts", "url", "primary_color", "secondary_color", "accent_color",
            "background_color", "created_at", "updated_at", "seo",
        )

    def get_districts(self, obj):
        districts = obj.districts.all()
        if hasattr(obj, "active_districts"):
            districts = obj.active_districts
        return DistrictSummarySerializer(districts, many=True, context=self.context).data

    def get_url(self, obj):
        return f"/{obj.slug}/"

    def get_seo(self, obj):
        return seo_payload(
            obj,
            path=self.get_url(obj),
            title=obj.hero_title or obj.name,
            description=obj.short_description or obj.content,
            request=self.context.get("request"),
            schema={"@type": "Place", "name": clean_text(obj.name)},
        )


class DistrictSerializer(serializers.ModelSerializer):
    name = TextField()
    city = serializers.SerializerMethodField()
    projects = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()
    seo = serializers.SerializerMethodField()

    class Meta:
        model = District
        fields = ("id", "name", "slug", "city", "projects", "url", "created_at", "updated_at", "seo")

    def get_city(self, obj):
        return related_payload(obj.city)

    def get_projects(self, obj):
        projects = getattr(obj, "public_projects", obj.projects.filter(is_visible=True))
        return ProjectCardSerializer(projects, many=True, context=self.context).data

    def get_url(self, obj):
        return f"/{obj.city.slug}/districts/{obj.slug}/"

    def get_seo(self, obj):
        title = f"خدمات نخيل ولاندسكيب في حي {clean_text(obj.name)} {clean_text(obj.city.name)}"
        return seo_payload(
            path=self.get_url(obj), title=title,
            description=f"الخدمات والمشاريع المنشورة في حي {clean_text(obj.name)} بمدينة {clean_text(obj.city.name)}.",
            request=self.context.get("request"), schema={"@type": "Place", "name": clean_text(obj.name)},
            modified_time=obj.updated_at,
        )


class CityServiceSerializer(serializers.ModelSerializer):
    city = serializers.SerializerMethodField()
    district = serializers.SerializerMethodField()
    service = ServiceSerializer(read_only=True)
    hero_title = TextField()
    content = HTMLField()
    benefits = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()
    seo = serializers.SerializerMethodField()

    class Meta:
        model = CityServicePage
        fields = (
            "id", "city", "district", "service", "hero_title", "content", "benefits",
            "url", "created_at", "updated_at", "seo",
        )

    def get_city(self, obj):
        return related_payload(obj.city)

    def get_district(self, obj):
        return related_payload(obj.district)

    def get_benefits(self, obj):
        return [clean_text(item) for item in (obj.benefits_list or obj.service.benefits_list)]

    def get_url(self, obj):
        return f"/{obj.city.slug}/{obj.custom_slug or obj.service.slug}/"

    def get_seo(self, obj):
        return seo_payload(
            obj,
            path=self.get_url(obj),
            title=obj.hero_title or f"{obj.service.title} في {obj.city.name}",
            description=obj.content,
            image=obj.service.resolved_image,
            request=self.context.get("request"),
            schema={"@type": "Service", "name": clean_text(obj.hero_title or obj.service.title)},
        )


class CategorySerializer(serializers.ModelSerializer):
    name = TextField()
    description = TextField()
    url = serializers.SerializerMethodField()
    seo = serializers.SerializerMethodField()

    class Meta:
        model = BlogCategory
        fields = ("id", "name", "slug", "description", "url", "created_at", "updated_at", "seo")

    def get_url(self, obj):
        return f"/blog/category/{obj.slug}/"

    def get_seo(self, obj):
        return seo_payload(
            obj,
            path=self.get_url(obj),
            title=obj.name,
            description=obj.description or f"مقالات {obj.name}",
            request=self.context.get("request"),
            schema={"@type": "CollectionPage", "name": clean_text(obj.name)},
        )


class TagSerializer(serializers.ModelSerializer):
    name = TextField()
    url = serializers.SerializerMethodField()
    seo = serializers.SerializerMethodField()

    class Meta:
        model = BlogTag
        fields = ("id", "name", "slug", "url", "created_at", "updated_at", "seo")

    def get_url(self, obj):
        return f"/blog/tag/{obj.slug}/"

    def get_seo(self, obj):
        return seo_payload(
            obj,
            path=self.get_url(obj),
            title=f"وسم {obj.name}",
            description=f"المقالات المنشورة تحت وسم {obj.name}.",
            request=self.context.get("request"),
            schema={"@type": "CollectionPage", "name": clean_text(obj.name)},
        )


class ArticleSerializer(serializers.ModelSerializer):
    title = TextField()
    excerpt = TextField()
    content = HTMLField()
    image = serializers.SerializerMethodField()
    category = CategorySerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    city = serializers.SerializerMethodField()
    district = serializers.SerializerMethodField()
    reading_time_minutes = serializers.IntegerField(read_only=True)
    url = serializers.SerializerMethodField()
    published_at = serializers.DateTimeField(source="publish_at", allow_null=True, read_only=True)
    seo = serializers.SerializerMethodField()

    class Meta:
        model = BlogPost
        fields = (
            "id", "title", "slug", "excerpt", "content", "image", "category", "tags",
            "city", "district", "is_featured", "reading_time_minutes", "url", "published_at",
            "created_at", "updated_at", "seo",
        )

    def get_image(self, obj):
        source = obj.featured_image if obj.featured_image else obj.featured_image_url
        return serializer_image(self, source, obj.title)

    def get_city(self, obj):
        return related_payload(obj.city)

    def get_district(self, obj):
        return related_payload(obj.district)

    def get_url(self, obj):
        return f"/blog/{obj.slug}/"

    def get_seo(self, obj):
        return seo_payload(
            obj,
            path=self.get_url(obj),
            title=obj.title,
            description=obj.excerpt or obj.content,
            image=obj.image_url,
            og_type="article",
            request=self.context.get("request"),
            schema={"@type": "Article", "headline": clean_text(obj.title)},
        )


class TestimonialSerializer(serializers.ModelSerializer):
    name = TextField()
    city_name = TextField()
    review = TextField()
    source = TextField()

    class Meta:
        model = Testimonial
        fields = ("id", "name", "city_name", "rating", "review", "source", "source_url", "is_verified")
