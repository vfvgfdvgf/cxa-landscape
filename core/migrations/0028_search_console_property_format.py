from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0027_site_verification_methods_project_coverage")]

    operations = [
        migrations.AlterField(
            model_name="sitesettings",
            name="google_search_console_property",
            field=models.CharField(
                max_length=255,
                blank=True,
                help_text="مثال URL-prefix: https://getsiaq.online/ أو Domain: sc-domain:getsiaq.online",
            ),
        ),
    ]
