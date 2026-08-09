from django.db import migrations, models
import django.db.models.deletion


def distribute_existing_pages(apps, schema_editor):
    CityServicePage = apps.get_model("core", "CityServicePage")
    District = apps.get_model("core", "District")
    for city_id in CityServicePage.objects.values_list("city_id", flat=True).distinct():
        district_ids = list(
            District.objects.filter(city_id=city_id, is_active=True)
            .order_by("sort_order", "name")
            .values_list("id", flat=True)
        )
        if not district_ids:
            continue
        page_ids = list(
            CityServicePage.objects.filter(city_id=city_id, district_id__isnull=True)
            .order_by("id")
            .values_list("id", flat=True)
        )
        for index, page_id in enumerate(page_ids):
            CityServicePage.objects.filter(pk=page_id).update(district_id=district_ids[index % len(district_ids)])


class Migration(migrations.Migration):
    dependencies = [("core", "0024_nakheel_najd_brand")]

    operations = [
        migrations.AddField(
            model_name="cityservicepage",
            name="district",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="local_service_pages",
                to="core.district",
                verbose_name="الحي الموزع عليه",
            ),
        ),
        migrations.RunPython(distribute_existing_pages, migrations.RunPython.noop),
        migrations.AddIndex(
            model_name="cityservicepage",
            index=models.Index(fields=["city", "district", "is_active"], name="citysvc_district_idx"),
        ),
    ]
