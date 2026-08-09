from .models import City, LegacyRedirect


LEGACY_SERVICE_SLUGS = {
    "shades": "landscaping",
    "fencing": "hardscape",
    "traditional": "irrigation-maintenance",
}


def sync_legacy_redirects():
    created_count = 0
    updated_count = 0
    for city in City.objects.filter(is_active=True, is_system=True):
        for old_slug, new_slug in LEGACY_SERVICE_SLUGS.items():
            old_path = f"/{city.slug}/{old_slug}/"
            target_path = f"/{city.slug}/{new_slug}/"
            _, created = LegacyRedirect.objects.update_or_create(
                old_path=old_path,
                defaults={"target_path": target_path, "is_permanent": True, "is_active": True},
            )
            if created:
                created_count += 1
            else:
                updated_count += 1
    return {"created": created_count, "updated": updated_count}
