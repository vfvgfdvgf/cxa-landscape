from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0028_search_console_property_format")]

    operations = [
        migrations.AlterModelOptions(
            name="siteverification",
            options={
                "ordering": ["provider", "verification_method", "name"],
                "verbose_name": "إثبات ملكية الموقع",
                "verbose_name_plural": "إثبات ملكية الموقع",
            },
        ),
        migrations.AlterField(
            model_name="siteverification",
            name="raw_html",
            field=models.TextField(
                blank=True,
                help_text="اختياري للأكواد المخصصة فقط. لا تضع أسرار API هنا.",
            ),
        ),
    ]
