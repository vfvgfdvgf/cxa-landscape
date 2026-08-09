from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0007_merge_20260323_0106"),
    ]

    operations = [
        migrations.CreateModel(
            name="LibraryImage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("source_name", models.CharField(blank=True, help_text="اسم الملف الأصلي داخل مجلد imge", max_length=255, unique=True)),
                ("title", models.CharField(max_length=180)),
                ("alt_text", models.CharField(blank=True, max_length=220)),
                ("category", models.CharField(choices=[("shades", "مظلات"), ("fencing", "شبوك"), ("palm", "نخيل"), ("traditional", "تراثي"), ("general", "عام")], default="general", max_length=20)),
                ("usage_group", models.CharField(choices=[("home_hero", "هيرو الرئيسية"), ("home_gallery", "معرض الرئيسية"), ("home_banners", "بنرات الرئيسية"), ("about", "من نحن"), ("services", "الخدمات"), ("portfolio", "الأعمال"), ("cities", "المدن"), ("blog", "المدونة"), ("blog_post", "تفاصيل المقال"), ("contact", "اتصل بنا"), ("city", "صفحة المدينة"), ("city_service", "خدمة داخل مدينة")], default="home_gallery", max_length=30)),
                ("image", models.ImageField(blank=True, null=True, upload_to="library-images/")),
                ("external_url", models.URLField(blank=True)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={
                "verbose_name": "صورة مكتبة الموقع",
                "verbose_name_plural": "صور مكتبة الموقع",
                "ordering": ["usage_group", "sort_order", "title"],
            },
        ),
    ]
