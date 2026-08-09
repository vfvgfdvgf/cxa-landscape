from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("core", "0026_site_identity_controls")]

    operations = [
        migrations.AddField(
            model_name="siteverification",
            name="verification_method",
            field=models.CharField(
                choices=[
                    ("html_tag", "وسم HTML داخل <head>"),
                    ("html_file", "ملف HTML في جذر الموقع"),
                    ("dns_txt", "سجل DNS TXT"),
                    ("dns_cname", "سجل DNS CNAME"),
                    ("google_analytics", "Google Analytics"),
                    ("google_tag_manager", "Google Tag Manager"),
                ],
                default="html_tag",
                help_text="اختر الطريقة نفسها التي يعرضها Google Search Console.",
                max_length=30,
                verbose_name="طريقة التحقق",
            ),
        ),
        migrations.AlterField(
            model_name="siteverification",
            name="name",
            field=models.CharField(
                default="google-site-verification",
                help_text="HTML tag: اترك google-site-verification. HTML file: اسم الملف مثل google123.html. DNS: اسم/Host السجل. Analytics/Tag Manager: يمكن تركه كما هو.",
                max_length=255,
                verbose_name="الاسم / المضيف / اسم الملف",
            ),
        ),
        migrations.AlterField(
            model_name="siteverification",
            name="content",
            field=models.TextField(
                blank=True,
                help_text="الصق Token الوسم، أو محتوى ملف HTML كما هو، أو قيمة DNS، أو Measurement ID مثل G-XXXX، أو Container ID مثل GTM-XXXX.",
                verbose_name="قيمة التحقق",
            ),
        ),
        migrations.AddField(
            model_name="project",
            name="coverage_city",
            field=models.ForeignKey(
                blank=True,
                help_text="مدينة يظهر المشروع ضمن تغطيتها دون الادعاء أن التنفيذ تم فيها.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="coverage_projects",
                to="core.city",
                verbose_name="مدينة نطاق الخدمة",
            ),
        ),
        migrations.AddField(
            model_name="project",
            name="coverage_district",
            field=models.ForeignKey(
                blank=True,
                help_text="حي يظهر المشروع ضمن نطاق خدمته. لا يعني أن المشروع نُفذ فعليًا في الحي.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="coverage_projects",
                to="core.district",
                verbose_name="حي نطاق الخدمة",
            ),
        ),
        migrations.AddField(
            model_name="project",
            name="record_type",
            field=models.CharField(
                choices=[
                    ("portfolio", "عمل مصوّر / مشروع"),
                    ("local_solution", "نموذج حل محلي"),
                ],
                default="portfolio",
                max_length=30,
                verbose_name="نوع السجل",
            ),
        ),
        migrations.AddField(
            model_name="project",
            name="is_indexable",
            field=models.BooleanField(
                default=True,
                help_text="عطّل الفهرسة للنماذج المحلية المتكررة مع إبقائها قابلة للتصفح.",
                verbose_name="السماح بالفهرسة",
            ),
        ),
    ]
