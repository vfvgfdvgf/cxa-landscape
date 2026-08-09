from rest_framework import serializers

from core.api.serializers.common import TextField, serializer_image
from core.api.utils import clean_text
from core.models import SiteSettings, SiteVerification


class NavigationSerializer(serializers.Serializer):
    label = TextField()
    url = serializers.CharField()
    new_tab = serializers.BooleanField(default=False)


class SiteSettingsSerializer(serializers.ModelSerializer):
    site_name = TextField()
    tagline = TextField()
    address = TextField()
    footer_text = TextField()
    service_highlights = serializers.SerializerMethodField()
    contact_numbers = serializers.SerializerMethodField()
    social_links = serializers.SerializerMethodField()
    default_image = serializers.SerializerMethodField()
    logo = serializers.SerializerMethodField()
    hero_image = serializers.SerializerMethodField()
    hero_mobile_image = serializers.SerializerMethodField()
    hero_settings = serializers.SerializerMethodField()
    colors = serializers.SerializerMethodField()
    seo_defaults = serializers.SerializerMethodField()
    business = serializers.SerializerMethodField()
    verification = serializers.SerializerMethodField()

    class Meta:
        model = SiteSettings
        fields = (
            "site_name", "tagline", "contact_phone", "whatsapp_number", "email", "address",
            "footer_text", "service_highlights", "contact_numbers", "social_links", "default_image", "logo",
            "hero_image", "hero_mobile_image", "hero_settings", "colors", "seo_defaults", "business", "verification", "updated_at",
        )

    def get_service_highlights(self, obj):
        return [clean_text(item) for item in obj.service_highlights_list]

    def get_contact_numbers(self, obj):
        return [
            {
                "label": clean_text(item.label), "phone": item.phone,
                "is_primary": item.is_primary, "whatsapp": item.enable_whatsapp,
            }
            for item in obj.contact_numbers.filter(is_active=True)
        ]

    def get_social_links(self, obj):
        return {
            "facebook": obj.facebook_url, "instagram": obj.instagram_url,
            "x": obj.x_url, "linkedin": obj.linkedin_url,
        }

    def get_default_image(self, obj):
        source = obj.default_og_image if obj.default_og_image else obj.default_og_image_url
        return serializer_image(self, source, obj.site_name)

    def get_logo(self, obj):
        source = obj.site_logo if obj.site_logo else obj.site_logo_url
        return serializer_image(self, source, obj.site_logo_alt or obj.site_name)

    def get_hero_image(self, obj):
        source = obj.homepage_hero_background if obj.homepage_hero_background else obj.homepage_hero_background_url
        return serializer_image(self, source, obj.homepage_hero_alt or obj.homepage_meta_title)

    def get_hero_mobile_image(self, obj):
        source = (
            obj.homepage_hero_mobile_background
            if obj.homepage_hero_mobile_background
            else obj.homepage_hero_mobile_background_url
        )
        return serializer_image(self, source, obj.homepage_hero_alt or obj.homepage_meta_title)

    def get_hero_settings(self, obj):
        return {
            "focus_x": obj.homepage_hero_focus_x,
            "focus_y": obj.homepage_hero_focus_y,
            "overlay_opacity": obj.homepage_hero_overlay_opacity,
        }

    def get_colors(self, obj):
        return {
            "primary": obj.primary_color, "secondary": obj.secondary_color,
            "accent": obj.accent_color, "background": obj.background_color, "text": obj.text_color,
        }

    def get_seo_defaults(self, obj):
        return {
            "title": clean_text(obj.homepage_meta_title),
            "description": clean_text(obj.seo_default_description or obj.homepage_meta_description),
            "keywords": clean_text(obj.seo_default_keywords),
            "twitter_handle": obj.seo_twitter_handle,
        }


    def get_verification(self, obj):
        records = SiteVerification.objects.filter(provider="google", is_active=True).order_by("created_at", "pk")
        meta_tags = []
        html_files = []
        dns_records = []
        analytics_id = ""
        tag_manager_id = ""
        for item in records:
            method = item.verification_method
            if method == "html_tag" and item.name and item.content:
                meta_tags.append({"name": item.name.strip(), "content": item.content.strip()})
            elif method == "html_file" and item.name and item.content:
                html_files.append({"name": item.name.strip(), "content": item.content})
            elif method in {"dns_txt", "dns_cname"} and item.content:
                dns_records.append({"type": method.removeprefix("dns_").upper(), "name": item.name.strip(), "value": item.content.strip()})
            elif method == "google_analytics" and item.content and not analytics_id:
                analytics_id = item.content.strip()
            elif method == "google_tag_manager" and item.content and not tag_manager_id:
                tag_manager_id = item.content.strip()
        return {
            "meta_tags": meta_tags,
            "html_files": html_files,
            "dns_records": dns_records,
            "google_analytics_id": analytics_id,
            "google_tag_manager_id": tag_manager_id,
        }

    def get_business(self, obj):
        return {
            "type": obj.business_type or "LocalBusiness",
            "legal_name": clean_text(obj.legal_name or obj.site_name),
            "opening_hours": [clean_text(item) for item in obj.opening_hours_list],
            "area_served": [clean_text(item) for item in obj.area_served_list],
            "latitude": str(obj.latitude) if obj.latitude is not None else "",
            "longitude": str(obj.longitude) if obj.longitude is not None else "",
            "address": {
                "street_address": clean_text(obj.street_address or obj.address),
                "locality": clean_text(obj.address_locality),
                "region": clean_text(obj.address_region),
                "postal_code": obj.postal_code,
                "country": obj.address_country or "SA",
            },
        }
