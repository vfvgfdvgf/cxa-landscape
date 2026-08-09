from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0002_admin_dashboard_models"),
    ]

    operations = [
        migrations.AddField(
            model_name="city",
            name="accent_color",
            field=models.CharField(blank=True, max_length=7),
        ),
        migrations.AddField(
            model_name="city",
            name="background_color",
            field=models.CharField(blank=True, max_length=7),
        ),
        migrations.AddField(
            model_name="city",
            name="primary_color",
            field=models.CharField(blank=True, max_length=7),
        ),
        migrations.AddField(
            model_name="city",
            name="secondary_color",
            field=models.CharField(blank=True, max_length=7),
        ),
        migrations.AddField(
            model_name="sitesettings",
            name="accent_color",
            field=models.CharField(default="#c6a56d", max_length=7),
        ),
        migrations.AddField(
            model_name="sitesettings",
            name="background_color",
            field=models.CharField(default="#f7f1e8", max_length=7),
        ),
        migrations.AddField(
            model_name="sitesettings",
            name="footer_text",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="sitesettings",
            name="primary_color",
            field=models.CharField(default="#83643b", max_length=7),
        ),
        migrations.AddField(
            model_name="sitesettings",
            name="secondary_color",
            field=models.CharField(default="#0f5b54", max_length=7),
        ),
        migrations.AddField(
            model_name="sitesettings",
            name="text_color",
            field=models.CharField(default="#1c1915", max_length=7),
        ),
    ]
