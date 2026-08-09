from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0003_theme_colors"),
    ]

    operations = [
        migrations.AddField(
            model_name="sitesettings",
            name="homepage_hero_background",
            field=models.ImageField(blank=True, null=True, upload_to="site-settings/"),
        ),
        migrations.AddField(
            model_name="sitesettings",
            name="homepage_hero_background_url",
            field=models.URLField(blank=True),
        ),
    ]
