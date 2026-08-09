from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0018_integrity_constraints")]

    operations = [
        migrations.AddIndex(
            model_name="pagemedia",
            index=models.Index(fields=["page", "section", "is_active"], name="page_media_lookup_idx"),
        ),
        migrations.AddIndex(
            model_name="libraryimage",
            index=models.Index(fields=["usage_group", "is_active", "sort_order"], name="library_usage_active_idx"),
        ),
        migrations.AddIndex(
            model_name="libraryimage",
            index=models.Index(fields=["category", "is_active"], name="library_category_idx"),
        ),
        migrations.AddIndex(
            model_name="cityservicepage",
            index=models.Index(fields=["city", "is_active"], name="city_service_active_idx"),
        ),
        migrations.AddIndex(
            model_name="blogpost",
            index=models.Index(fields=["status", "publish_at"], name="blog_status_publish_idx"),
        ),
        migrations.AddIndex(
            model_name="blogpost",
            index=models.Index(fields=["is_featured", "publish_at"], name="blog_featured_publish_idx"),
        ),
        migrations.AddIndex(
            model_name="project",
            index=models.Index(fields=["is_visible", "created_at"], name="project_visible_date_idx"),
        ),
        migrations.AddIndex(
            model_name="lead",
            index=models.Index(fields=["status", "created_at"], name="lead_status_date_idx"),
        ),
        migrations.AddIndex(
            model_name="conversionevent",
            index=models.Index(fields=["event_type", "created_at"], name="conversion_event_date_idx"),
        ),
    ]
