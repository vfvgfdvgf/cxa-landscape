from django.db import migrations
from django.utils.text import slugify


def seed_locations(apps, schema_editor):
    City = apps.get_model("core", "City")
    District = apps.get_model("core", "District")
    ServiceCategory = apps.get_model("core", "ServiceCategory")
    BlogCategory = apps.get_model("core", "BlogCategory")

    from core.data import CITIES
    from core.location_data import FIXED_DISTRICTS

    for city_data in CITIES:
        city, _ = City.objects.get_or_create(
            slug=city_data["slug"],
            defaults={
                "name": city_data["name"],
                "region": city_data.get("region", ""),
                "short_description": city_data.get("description", ""),
            },
        )
        city.name = city_data["name"]
        city.region = city_data.get("region", city.region)
        if not city.short_description:
            city.short_description = city_data.get("description", "")
        city.is_active = True
        city.is_system = True
        city.auto_generate_service_pages = True
        city.save(update_fields=["name", "region", "short_description", "is_active", "is_system", "auto_generate_service_pages", "updated_at"])

        seen = set()
        for order, district_name in enumerate(FIXED_DISTRICTS.get(city.slug, []), start=1):
            if district_name in seen:
                continue
            seen.add(district_name)
            district, _ = District.objects.get_or_create(
                city=city,
                name=district_name,
                defaults={"slug": slugify(district_name, allow_unicode=True), "sort_order": order},
            )
            district.slug = slugify(district_name, allow_unicode=True)
            district.sort_order = order
            district.is_active = True
            district.is_system = True
            district.save(update_fields=["slug", "sort_order", "is_active", "is_system", "updated_at"])

    for name, slug in [
        ("تصميم وتنفيذ الحدائق", "garden-design-build"),
        ("النخيل والتشجير", "palms-planting"),
        ("الري والصيانة", "irrigation-care"),
        ("اللاندسكيب الصلب", "hardscape"),
        ("المظلات والشبوك", "shades-fencing"),
        ("خدمات اللاندسكيب", "landscape-services"),
    ]:
        ServiceCategory.objects.get_or_create(slug=slug, defaults={"name": name, "description": f"خدمات متخصصة ضمن {name}."})

    for name, slug in [
        ("النخيل والأشجار", "palms-trees"),
        ("تصميم الحدائق", "garden-design"),
        ("الري والصيانة", "irrigation-maintenance"),
        ("اللاندسكيب", "landscape"),
        ("المظلات والشبوك", "shades-fencing"),
        ("دليل وتكاليف", "guides-costs"),
        ("نصائح اللاندسكيب", "landscape-tips"),
    ]:
        BlogCategory.objects.get_or_create(slug=slug, defaults={"name": name, "description": f"مقالات وأدلة حول {name}."})


def reverse_noop(apps, schema_editor):
    # The fixed catalog is content, not disposable migration data.
    pass


class Migration(migrations.Migration):
    dependencies = [("core", "0021_location_taxonomy_automation")]
    operations = [migrations.RunPython(seed_locations, reverse_noop)]
