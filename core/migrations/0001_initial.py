from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="PageMedia",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "page",
                    models.CharField(
                        choices=[
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
                        ],
                        max_length=30,
                    ),
                ),
                ("section", models.CharField(default="hero", help_text="مثال: hero, gallery, secondary", max_length=50)),
                ("title", models.CharField(max_length=150)),
                ("alt_text", models.CharField(blank=True, max_length=180)),
                ("image", models.ImageField(blank=True, null=True, upload_to="site-media/")),
                ("external_url", models.URLField(blank=True)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "صورة صفحة",
                "verbose_name_plural": "صور الصفحات",
                "ordering": ["page", "section", "sort_order", "-created_at"],
            },
        ),
        migrations.CreateModel(
            name="SiteSettings",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("site_name", models.CharField(default="مظلات وسواتر المملكة", max_length=200)),
                ("contact_phone", models.CharField(default="0554882724", max_length=20)),
                ("whatsapp_number", models.CharField(default="0554882724", max_length=20)),
                ("tagline", models.CharField(default="خدمات متكاملة في جميع مدن السعودية", max_length=255)),
                ("homepage_meta_title", models.CharField(default="مظلات وسواتر ونخيل ومجالس تراثية في السعودية", max_length=255)),
                (
                    "homepage_meta_description",
                    models.TextField(
                        default="شركة سعودية متخصصة في تركيب المظلات والسواتر والشبوك وتوريد النخيل وبناء المجالس التراثية في جميع مدن المملكة."
                    ),
                ),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"verbose_name": "إعدادات الموقع", "verbose_name_plural": "إعدادات الموقع"},
        ),
    ]
