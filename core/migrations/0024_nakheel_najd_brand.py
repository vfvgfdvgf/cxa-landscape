from django.db import migrations, models


def apply_brand(apps, schema_editor):
    SiteSettings = apps.get_model("core", "SiteSettings")
    ContactNumber = apps.get_model("core", "ContactNumber")
    Page = apps.get_model("core", "Page")

    settings_obj, _ = SiteSettings.objects.get_or_create(pk=1)
    settings_obj.site_name = "نخيل نجد"
    settings_obj.contact_phone = "0554882724"
    settings_obj.whatsapp_number = "0554882724"
    settings_obj.legal_name = "نخيل نجد"
    settings_obj.tagline = "توريد وزراعة النخيل وتنسيق الحدائق والشبوك في مدن المملكة"
    settings_obj.homepage_meta_title = "نخيل نجد | توريد وزراعة النخيل واللاندسكيب والشبوك"
    settings_obj.homepage_meta_description = (
        "نخيل نجد لتوريد وزراعة النخيل العربي والواشنطني والملوكي، وصيانة الحدائق، "
        "وتنفيذ اللاندسكيب والشبوك في مدن المملكة وأحيائها."
    )
    settings_obj.service_highlights = (
        "توريد النخيل العربي\nتوريد النخيل الواشنطني والملوكي\nصيانة الحدائق واللاندسكيب\n"
        "شبكات الري\nالشبوك والسياجات"
    )
    settings_obj.seo_default_keywords = (
        "نخيل نجد, توريد نخيل, نخيل عربي, نخيل واشنطني, نخيل ملوكي, صيانة حدائق, "
        "لاندسكيب, شبوك, شبكات ري, السعودية"
    )
    settings_obj.seo_default_description = settings_obj.homepage_meta_description
    settings_obj.footer_text = (
        "توريد وزراعة النخيل العربي والواشنطني والملوكي، وتنفيذ وصيانة الحدائق "
        "واللاندسكيب وشبكات الري والشبوك."
    )
    settings_obj.primary_color = "#205B47"
    settings_obj.secondary_color = "#173D31"
    settings_obj.accent_color = "#B89157"
    settings_obj.background_color = "#F5F4EF"
    settings_obj.text_color = "#17201C"
    settings_obj.save()

    ContactNumber.objects.filter(site_settings_id=settings_obj.pk).exclude(phone="0554882724").update(
        is_active=False,
        is_primary=False,
    )
    contact, _ = ContactNumber.objects.update_or_create(
        site_settings_id=settings_obj.pk,
        phone="0554882724",
        defaults={
            "label": "واتساب نخيل نجد",
            "is_primary": True,
            "enable_whatsapp": True,
            "is_active": True,
            "sort_order": 0,
        },
    )
    ContactNumber.objects.filter(site_settings_id=settings_obj.pk).exclude(pk=contact.pk).update(is_primary=False)

    Page.objects.filter(template_key="home").update(
        title="نخيل نجد",
        menu_title="الرئيسية",
        hero_title="توريد وزراعة النخيل وتنفيذ الحدائق والري والشبوك",
        intro_text=(
            "نورّد ونزرع النخيل العربي والواشنطني والملوكي، وننفذ اللاندسكيب "
            "وشبكات الري والشبوك مع تغطية المدن والأحياء."
        ),
    )


class Migration(migrations.Migration):
    dependencies = [("core", "0023_classify_existing_content")]

    operations = [
        migrations.AlterField(
            model_name="sitesettings",
            name="site_name",
            field=models.CharField(default="نخيل نجد", max_length=200),
        ),
        migrations.AlterField(
            model_name="sitesettings",
            name="contact_phone",
            field=models.CharField(default="0554882724", max_length=20),
        ),
        migrations.AlterField(
            model_name="sitesettings",
            name="whatsapp_number",
            field=models.CharField(default="0554882724", max_length=20),
        ),
        migrations.RunPython(apply_brand, migrations.RunPython.noop),
    ]
