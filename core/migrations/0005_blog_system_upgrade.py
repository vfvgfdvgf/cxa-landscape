from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0004_home_hero_background"),
    ]

    operations = [
        migrations.AddField(
            model_name="blogcategory",
            name="description",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="blogcategory",
            name="meta_description",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="blogcategory",
            name="meta_title",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="blogtag",
            name="meta_description",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="blogtag",
            name="meta_title",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="blogpost",
            name="is_featured",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="blogpost",
            name="status",
            field=models.CharField(choices=[("draft", "مسودة"), ("published", "منشور")], default="draft", max_length=20),
        ),
        migrations.AddField(
            model_name="blogpost",
            name="total_read_seconds",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="blogpost",
            name="view_count",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.CreateModel(
            name="BlogComment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("author_name", models.CharField(max_length=120)),
                ("author_email", models.EmailField(blank=True, max_length=254)),
                ("content", models.TextField()),
                ("is_approved", models.BooleanField(default=False)),
                ("is_spam", models.BooleanField(default=False)),
                ("post", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="comments", to="core.blogpost")),
            ],
            options={"verbose_name": "تعليق", "verbose_name_plural": "التعليقات", "ordering": ["-created_at"]},
        ),
    ]
