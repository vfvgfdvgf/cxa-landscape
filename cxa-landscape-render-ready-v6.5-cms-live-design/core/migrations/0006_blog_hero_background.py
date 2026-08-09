from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0005_blog_system_upgrade"),
    ]

    operations = [
        migrations.AddField(
            model_name="sitesettings",
            name="blog_hero_background",
            field=models.ImageField(blank=True, null=True, upload_to="site-settings/"),
        ),
        migrations.AddField(
            model_name="sitesettings",
            name="blog_hero_background_url",
            field=models.URLField(blank=True),
        ),
    ]
