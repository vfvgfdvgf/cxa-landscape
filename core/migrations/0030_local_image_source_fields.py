from django.db import migrations, models
import core.models


class Migration(migrations.Migration):
    dependencies = [("core", "0029_site_verification_model_state")]

    operations = [
        migrations.AlterField(
            model_name="pagemedia",
            name="external_url",
            field=models.CharField(blank=True, max_length=500, validators=[core.models.validate_image_source]),
        ),
        migrations.AlterField(
            model_name="libraryimage",
            name="external_url",
            field=models.CharField(blank=True, max_length=500, validators=[core.models.validate_image_source]),
        ),
        migrations.AlterField(
            model_name="service",
            name="image_url",
            field=models.CharField(blank=True, max_length=500, validators=[core.models.validate_image_source]),
        ),
        migrations.AlterField(
            model_name="blogpost",
            name="featured_image_url",
            field=models.CharField(blank=True, max_length=500, validators=[core.models.validate_image_source]),
        ),
        migrations.AlterField(
            model_name="project",
            name="featured_image_url",
            field=models.CharField(blank=True, max_length=500, validators=[core.models.validate_image_source]),
        ),
        migrations.AlterField(
            model_name="projectimage",
            name="external_url",
            field=models.CharField(blank=True, max_length=500, validators=[core.models.validate_image_source]),
        ),
    ]
