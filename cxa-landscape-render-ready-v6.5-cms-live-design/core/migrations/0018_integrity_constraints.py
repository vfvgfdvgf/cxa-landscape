from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import migrations, models
from django.db.models import Count


def resolve_duplicate_paths(apps, schema_editor):
    Page = apps.get_model("core", "Page")
    CityServicePage = apps.get_model("core", "CityServicePage")

    duplicate_page_paths = (
        Page.objects.exclude(custom_url="")
        .values("custom_url")
        .annotate(total=Count("id"))
        .filter(total__gt=1)
    )
    for row in duplicate_page_paths.iterator():
        duplicates = Page.objects.filter(custom_url=row["custom_url"]).order_by("id")
        for item in list(duplicates)[1:]:
            suffix = f"-{item.pk}"
            item.custom_url = f"{row['custom_url'][: 180 - len(suffix)]}{suffix}"
            item.save(update_fields=["custom_url"])

    duplicate_city_slugs = (
        CityServicePage.objects.exclude(custom_slug="")
        .values("city_id", "custom_slug")
        .annotate(total=Count("id"))
        .filter(total__gt=1)
    )
    for row in duplicate_city_slugs.iterator():
        duplicates = CityServicePage.objects.filter(
            city_id=row["city_id"], custom_slug=row["custom_slug"]
        ).order_by("id")
        for item in list(duplicates)[1:]:
            suffix = f"-{item.pk}"
            item.custom_slug = f"{row['custom_slug'][: 160 - len(suffix)]}{suffix}"
            item.save(update_fields=["custom_slug"])


class Migration(migrations.Migration):
    dependencies = [("core", "0017_libraryimage_image_stored")]

    operations = [
        migrations.RunPython(resolve_duplicate_paths, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="page",
            constraint=models.UniqueConstraint(
                condition=~models.Q(custom_url=""),
                fields=("custom_url",),
                name="unique_nonempty_page_custom_url",
            ),
        ),
        migrations.AddConstraint(
            model_name="cityservicepage",
            constraint=models.UniqueConstraint(
                condition=~models.Q(custom_slug=""),
                fields=("city", "custom_slug"),
                name="unique_city_custom_service_slug",
            ),
        ),
        migrations.AlterField(
            model_name="testimonial",
            name="rating",
            field=models.PositiveSmallIntegerField(
                default=5,
                validators=[MinValueValidator(1), MaxValueValidator(5)],
            ),
        ),
    ]
