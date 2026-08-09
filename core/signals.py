from django.core.cache import cache
from django.db.models import Q
from django.db.models.deletion import ProtectedError
from django.db.models.signals import m2m_changed, post_delete, post_save, pre_delete
from django.dispatch import receiver

from .content_automation import apply_blog_tags, apply_service_tags
from .local_seo import build_city_service_seo
from .models import (
    BlogCategory,
    BlogPost,
    BlogTag,
    City,
    CityServicePage,
    ContactNumber,
    District,
    LegacyRedirect,
    LibraryImage,
    NavigationItem,
    Page,
    Service,
    ServiceCategory,
    ServiceTag,
    SiteSettings,
    SiteVerification,
    Testimonial,
)


def clear_site_cache():
    cache.delete_many(["site:defaults", "site:navigation_items", "library:records", "site:location_options"])


def _create_missing_pages_for(city=None, service=None):
    cities = City.objects.filter(is_active=True, is_system=True, auto_generate_service_pages=True)
    services = Service.objects.filter(is_visible=True)

    if city is not None:
        cities = cities.filter(pk=city.pk)
        services = services.filter(Q(cities=city) | Q(primary_city=city)).distinct()
    if service is not None:
        services = services.filter(pk=service.pk)
        selected_city_ids = list(service.cities.filter(is_active=True).values_list("pk", flat=True))
        if service.primary_city_id and service.primary_city_id not in selected_city_ids:
            selected_city_ids.append(service.primary_city_id)
        cities = cities.filter(pk__in=selected_city_ids)

    for city_obj in cities:
        for service_obj in services:
            payload = build_city_service_seo(city_obj, service_obj)
            CityServicePage.objects.get_or_create(
                city=city_obj,
                service=service_obj,
                defaults={
                    "hero_title": payload["hero_title"],
                    "content": payload["content"],
                    "benefits": payload["benefits"],
                    "custom_slug": payload["custom_slug"],
                    "meta_title": payload["meta_title"],
                    "meta_description": payload["meta_description"],
                    "meta_keywords": payload["meta_keywords"],
                    "is_active": True,
                },
            )


@receiver(pre_delete, sender=City)
def protect_fixed_city(sender, instance, **kwargs):
    if instance.is_system:
        raise ProtectedError("المدن الأساسية ثابتة ولا يمكن حذفها.", [instance])


@receiver(pre_delete, sender=District)
def protect_fixed_district(sender, instance, **kwargs):
    if instance.is_system:
        raise ProtectedError("الأحياء الأساسية ثابتة ولا يمكن حذفها.", [instance])


@receiver(post_save, sender=City)
def create_pages_after_city_save(sender, instance, **kwargs):
    clear_site_cache()
    if instance.is_active and instance.auto_generate_service_pages:
        _create_missing_pages_for(city=instance)


@receiver(post_save, sender=District)
@receiver(post_delete, sender=District)
def clear_location_cache(sender, instance, **kwargs):
    clear_site_cache()


@receiver(post_save, sender=Service)
def service_after_save(sender, instance, **kwargs):
    clear_site_cache()
    apply_service_tags(instance)


@receiver(m2m_changed, sender=Service.cities.through)
def service_cities_changed(sender, instance, action, **kwargs):
    if action in {"post_add", "post_remove", "post_clear"}:
        clear_site_cache()
        if instance.is_visible:
            _create_missing_pages_for(service=instance)


@receiver(post_save, sender=SiteSettings)
@receiver(post_delete, sender=SiteSettings)
@receiver(post_save, sender=SiteVerification)
@receiver(post_delete, sender=SiteVerification)
@receiver(post_save, sender=ContactNumber)
@receiver(post_delete, sender=ContactNumber)
@receiver(post_save, sender=NavigationItem)
@receiver(post_delete, sender=NavigationItem)
@receiver(post_save, sender=Page)
@receiver(post_delete, sender=Page)
@receiver(post_save, sender=Testimonial)
@receiver(post_delete, sender=Testimonial)
@receiver(post_save, sender=LibraryImage)
@receiver(post_delete, sender=LibraryImage)
def clear_cached_site_defaults(sender, instance, **kwargs):
    clear_site_cache()


@receiver(post_save, sender=BlogPost)
def blog_post_after_save(sender, instance, **kwargs):
    apply_blog_tags(instance)
    cache.delete("blog-sidebar-data")


@receiver(post_delete, sender=BlogPost)
@receiver(post_save, sender=BlogCategory)
@receiver(post_delete, sender=BlogCategory)
@receiver(post_save, sender=BlogTag)
@receiver(post_delete, sender=BlogTag)
@receiver(post_save, sender=ServiceCategory)
@receiver(post_delete, sender=ServiceCategory)
@receiver(post_save, sender=ServiceTag)
@receiver(post_delete, sender=ServiceTag)
def clear_content_taxonomy_cache(sender, instance, **kwargs):
    cache.delete("blog-sidebar-data")
    clear_site_cache()


@receiver(post_save, sender=LegacyRedirect)
def clear_cached_legacy_redirect(sender, instance, **kwargs):
    if not instance.old_path:
        return
    normalized = instance.old_path.rstrip("/") or "/"
    cache.delete_many([
        f"legacy_redirect:{instance.old_path}",
        f"legacy_redirect:{normalized}",
        f"legacy_redirect:{normalized}/",
    ])
