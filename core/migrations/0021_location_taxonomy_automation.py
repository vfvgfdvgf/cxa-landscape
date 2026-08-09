from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("core", "0020_lead_crm_fields")]

    operations = [
        migrations.AddField(
            model_name="city",
            name="is_system",
            field=models.BooleanField(default=False, editable=False, help_text="مدينة أساسية ثابتة لا يمكن حذفها من لوحة التحكم."),
        ),
        migrations.CreateModel(
            name="District",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=140)),
                ("slug", models.SlugField(allow_unicode=True, max_length=160)),
                ("is_active", models.BooleanField(default=True)),
                ("is_system", models.BooleanField(default=False, editable=False)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("city", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="districts", to="core.city")),
            ],
            options={
                "verbose_name": "حي",
                "verbose_name_plural": "الأحياء",
                "ordering": ["city__name", "sort_order", "name"],
            },
        ),
        migrations.CreateModel(
            name="ServiceCategory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("meta_title", models.CharField(blank=True, max_length=255)),
                ("meta_description", models.TextField(blank=True)),
                ("meta_keywords", models.CharField(blank=True, max_length=500)),
                ("name", models.CharField(max_length=120)),
                ("slug", models.SlugField(allow_unicode=True, max_length=140, unique=True)),
                ("description", models.TextField(blank=True)),
            ],
            options={"verbose_name": "تصنيف خدمة", "verbose_name_plural": "تصنيفات الخدمات", "ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="ServiceTag",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("meta_title", models.CharField(blank=True, max_length=255)),
                ("meta_description", models.TextField(blank=True)),
                ("meta_keywords", models.CharField(blank=True, max_length=500)),
                ("name", models.CharField(max_length=120)),
                ("slug", models.SlugField(allow_unicode=True, max_length=140, unique=True)),
            ],
            options={"verbose_name": "وسم خدمة", "verbose_name_plural": "وسوم الخدمات", "ordering": ["name"]},
        ),
        migrations.AddField(model_name="service", name="auto_classify", field=models.BooleanField(default=True, help_text="إنشاء التصنيف والوسوم تلقائيًا عند تركها فارغة.")),
        migrations.AddField(model_name="service", name="auto_distribute", field=models.BooleanField(default=True, help_text="اختيار مدينة وحي تلقائيًا عند تركهما فارغين.")),
        migrations.AddField(model_name="service", name="category", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="services", to="core.servicecategory")),
        migrations.AddField(model_name="service", name="primary_city", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="primary_services", to="core.city", verbose_name="المدينة الأساسية")),
        migrations.AddField(model_name="service", name="primary_district", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="primary_services", to="core.district", verbose_name="الحي الأساسي")),
        migrations.AddField(model_name="service", name="tags", field=models.ManyToManyField(blank=True, related_name="services", to="core.servicetag")),
        migrations.AlterField(model_name="blogcategory", name="slug", field=models.SlugField(allow_unicode=True, max_length=140, unique=True)),
        migrations.AlterField(model_name="blogtag", name="slug", field=models.SlugField(allow_unicode=True, max_length=140, unique=True)),
        migrations.AddField(model_name="blogpost", name="auto_classify", field=models.BooleanField(default=True, help_text="إنشاء التصنيف والوسوم تلقائيًا عند تركها فارغة.")),
        migrations.AddField(model_name="blogpost", name="auto_distribute", field=models.BooleanField(default=True, help_text="توزيع المقال تلقائيًا على مدينة وحي عند تركهما فارغين.")),
        migrations.AddField(model_name="blogpost", name="city", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="blog_posts", to="core.city")),
        migrations.AddField(model_name="blogpost", name="district", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="blog_posts", to="core.district")),
        migrations.AddField(model_name="project", name="district", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="projects", to="core.district")),
        migrations.AddField(model_name="lead", name="district_name", field=models.CharField(blank=True, max_length=140)),
        migrations.AddConstraint(model_name="district", constraint=models.UniqueConstraint(fields=("city", "name"), name="unique_district_name_per_city")),
        migrations.AddConstraint(model_name="district", constraint=models.UniqueConstraint(fields=("city", "slug"), name="unique_district_slug_per_city")),
        migrations.AddIndex(model_name="district", index=models.Index(fields=["city", "is_active", "sort_order"], name="district_city_active_idx")),
        migrations.AddIndex(model_name="blogpost", index=models.Index(fields=["city", "district", "status"], name="blog_location_status_idx")),
        migrations.AddIndex(model_name="project", index=models.Index(fields=["city", "district", "is_visible"], name="project_location_idx")),
    ]
