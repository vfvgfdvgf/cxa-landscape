from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0019_query_indexes")]

    operations = [
        migrations.AlterField(
            model_name="lead",
            name="status",
            field=models.CharField(
                choices=[
                    ("new", "جديد"),
                    ("contacted", "تم التواصل"),
                    ("site_visit", "تم تحديد معاينة"),
                    ("quote_sent", "تم إرسال عرض السعر"),
                    ("negotiating", "تفاوض"),
                    ("won", "تم التعاقد"),
                    ("lost", "لم يتم التعاقد"),
                    ("closed", "مغلق"),
                ],
                default="new",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="lead",
            name="source",
            field=models.CharField(
                choices=[
                    ("website", "الموقع"),
                    ("whatsapp", "واتساب"),
                    ("call", "اتصال"),
                    ("manual", "إدخال يدوي"),
                ],
                default="website",
                max_length=20,
            ),
        ),
        migrations.AddField(model_name="lead", name="page_url", field=models.URLField(blank=True)),
        migrations.AddField(model_name="lead", name="utm_source", field=models.CharField(blank=True, max_length=120)),
        migrations.AddField(model_name="lead", name="utm_medium", field=models.CharField(blank=True, max_length=120)),
        migrations.AddField(model_name="lead", name="utm_campaign", field=models.CharField(blank=True, max_length=160)),
        migrations.AddField(model_name="lead", name="follow_up_at", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(
            model_name="lead",
            name="estimated_value",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True),
        ),
    ]
