from django.db import migrations
from django.utils.text import slugify


BLOG_RULES = [
    ("النخيل والأشجار", "palms-trees", ("نخيل", "أشجار", "شجرة", "زراعة")),
    ("تصميم الحدائق", "garden-design", ("تصميم", "حدائق", "حديقة", "جلسات")),
    ("الري والصيانة", "irrigation-maintenance", ("ري", "صيانة", "تقليم", "تسميد")),
    ("اللاندسكيب", "landscape", ("لاندسكيب", "ثيل", "عشب")),
    ("المظلات والشبوك", "shades-fencing", ("مظلات", "شبوك", "سياج")),
    ("دليل وتكاليف", "guides-costs", ("تكلفة", "سعر", "دليل", "أفضل")),
]
SERVICE_RULES = [
    ("تصميم وتنفيذ الحدائق", "garden-design-build", ("تصميم", "حدائق", "حديقة")),
    ("النخيل والتشجير", "palms-planting", ("نخيل", "أشجار", "تشجير", "زراعة")),
    ("الري والصيانة", "irrigation-care", ("ري", "صيانة", "تقليم", "تسميد")),
    ("اللاندسكيب الصلب", "hardscape", ("لاندسكيب", "حجر", "بلاط")),
    ("المظلات والشبوك", "shades-fencing", ("مظلات", "شبوك", "سياج")),
]


def match_rule(text, rules, default):
    text = (text or "").lower()
    best = default
    score = 0
    for name, slug, words in rules:
        current = sum(text.count(word) for word in words)
        if current > score:
            best = (name, slug, words)
            score = current
    return best


def migrate_content(apps, schema_editor):
    City = apps.get_model("core", "City")
    District = apps.get_model("core", "District")
    Service = apps.get_model("core", "Service")
    ServiceCategory = apps.get_model("core", "ServiceCategory")
    ServiceTag = apps.get_model("core", "ServiceTag")
    BlogPost = apps.get_model("core", "BlogPost")
    BlogCategory = apps.get_model("core", "BlogCategory")
    BlogTag = apps.get_model("core", "BlogTag")
    Project = apps.get_model("core", "Project")

    cities = list(City.objects.filter(is_active=True, is_system=True).order_by("name"))
    districts = {
        city.pk: list(District.objects.filter(city_id=city.pk, is_active=True).order_by("sort_order", "name"))
        for city in cities
    }
    if not cities:
        return

    for index, service in enumerate(Service.objects.order_by("pk")):
        city = cities[index % len(cities)]
        district_list = districts.get(city.pk) or []
        district = district_list[index % len(district_list)] if district_list else None
        text = " ".join([service.title or "", service.short_title or "", service.description or "", service.meta_keywords or ""])
        category_name, category_slug, words = match_rule(text, SERVICE_RULES, ("خدمات اللاندسكيب", "landscape-services", ("لاندسكيب",)))
        category, _ = ServiceCategory.objects.get_or_create(slug=category_slug, defaults={"name": category_name})
        updates = []
        if not service.category_id:
            service.category_id = category.pk
            updates.append("category")
        if not service.primary_city_id:
            service.primary_city_id = city.pk
            updates.append("primary_city")
        if not service.primary_district_id and district:
            service.primary_district_id = district.pk
            updates.append("primary_district")
        if updates:
            service.save(update_fields=updates)
        service.cities.add(service.primary_city_id or city.pk)
        for word in words[:4]:
            tag, _ = ServiceTag.objects.get_or_create(
                slug=slugify(word, allow_unicode=True),
                defaults={"name": word},
            )
            service.tags.add(tag)

    for index, post in enumerate(BlogPost.objects.order_by("pk")):
        city = cities[index % len(cities)]
        district_list = districts.get(city.pk) or []
        district = district_list[index % len(district_list)] if district_list else None
        text = " ".join([post.title or "", post.excerpt or "", post.content or "", post.meta_keywords or ""])
        category_name, category_slug, words = match_rule(text, BLOG_RULES, ("نصائح اللاندسكيب", "landscape-tips", ("لاندسكيب",)))
        category, _ = BlogCategory.objects.get_or_create(slug=category_slug, defaults={"name": category_name})
        updates = []
        if not post.category_id:
            post.category_id = category.pk
            updates.append("category")
        if not post.city_id:
            post.city_id = city.pk
            updates.append("city")
        if not post.district_id and district:
            post.district_id = district.pk
            updates.append("district")
        if updates:
            post.save(update_fields=updates)
        for word in words[:4]:
            tag, _ = BlogTag.objects.get_or_create(
                slug=slugify(word, allow_unicode=True),
                defaults={"name": word},
            )
            post.tags.add(tag)

    for index, project in enumerate(Project.objects.exclude(city_id=None).order_by("pk")):
        if project.district_id:
            continue
        district_list = districts.get(project.city_id) or []
        if district_list:
            project.district_id = district_list[index % len(district_list)].pk
            project.save(update_fields=["district"])


def reverse_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [("core", "0022_seed_fixed_locations")]
    operations = [migrations.RunPython(migrate_content, reverse_noop)]
