from django.contrib.admin import AdminSite
from django.core.exceptions import PermissionDenied
from django.db.utils import OperationalError, ProgrammingError
from django.shortcuts import redirect
from django.urls import NoReverseMatch, path, reverse


class ArabicAdminSite(AdminSite):
    site_header = "لوحة تحكم نخيل نجد"
    site_title = "إدارة نخيل نجد"
    index_title = "إدارة المحتوى والمدن والأحياء وSEO"
    site_url = "/"
    index_template = "admin/index.html"

    def get_urls(self):
        urls = super().get_urls()

        def redirect_bad_ai_content_link(request, *args, **kwargs):
            return redirect(reverse("admin:ai_content_generator"))

        custom_urls = [
            path("ai-content/", self.admin_view(self.ai_content_view), name="ai_content_generator"),
            path("core/<path:model_path>/ai-content/", self.admin_view(redirect_bad_ai_content_link)),
            path("core/<path:model_path>/ai-content/change/", self.admin_view(redirect_bad_ai_content_link)),
        ]
        return custom_urls + urls

    def ai_content_view(self, request):
        if not request.user.is_superuser:
            raise PermissionDenied("مولد المحتوى متاح لمدير النظام فقط.")
        from .admin_ai import ai_content_admin_view

        return ai_content_admin_view(request, self)

    def index(self, request, extra_context=None):
        extra_context = extra_context or {}
        try:
            from .models import BlogPost, City, Lead, Project, SEOAutomationRun, SEOReportIssue, SearchConsoleQuery, Service

            def admin_link(model_name):
                try:
                    return reverse(f"admin:core_{model_name}_changelist")
                except NoReverseMatch:
                    return "#"

            extra_context["dashboard_stats"] = [
                {"label": "الخدمات", "value": Service.objects.count()},
                {"label": "المدن", "value": City.objects.filter(is_system=True).count()},
                {"label": "المقالات", "value": BlogPost.objects.count()},
                {"label": "المشاريع", "value": Project.objects.count()},
                {"label": "الطلبات", "value": Lead.objects.count()},
                {"label": "مشاكل SEO مفتوحة", "value": SEOReportIssue.objects.filter(status="open").count()},
                {"label": "كلمات Search Console", "value": SearchConsoleQuery.objects.count()},
            ]
            extra_context["recent_leads"] = Lead.objects.order_by("-created_at")[:6]
            extra_context["seo_issues"] = SEOReportIssue.objects.filter(status="open").order_by("-detected_at")[:8]
            extra_context["latest_seo_run"] = SEOAutomationRun.objects.order_by("-started_at").first()
            extra_context["admin_groups"] = [
                {
                    "title": "الإعدادات الأساسية",
                    "description": "هوية الموقع، إثبات الملكية، والقائمة الرئيسية.",
                    "items": [
                        {"label": "إعدادات الموقع", "url": admin_link("sitesettings"), "note": "الأرقام، الهوية، LocalBusiness، وSearch Console"},
                        {"label": "إثبات ملكية الموقع", "url": admin_link("siteverification"), "note": "Search Console: HTML وDNS وAnalytics وTag Manager"},
                        {"label": "عناصر القائمة", "url": admin_link("navigationitem"), "note": "روابط الهيدر والتنقل"},
                    ],
                },
                {
                    "title": "SEO والأتمتة",
                    "description": "المتابعة اليومية والتحسين التلقائي والتحويلات.",
                    "items": [
                        {"label": "تقرير SEO اليومي", "url": admin_link("seoreportissue"), "note": "الأخطاء والتحذيرات المفتوحة"},
                        {"label": "تشغيلات أتمتة SEO", "url": admin_link("seoautomationrun"), "note": "سجل التشغيل اليومي ونتائج AI"},
                        {"label": "كلمات Search Console", "url": admin_link("searchconsolequery"), "note": "الكلمات والصفحات القادمة من Google"},
                        {"label": "تحويلات الروابط القديمة", "url": admin_link("legacyredirect"), "note": "منع التكرار وحماية الروابط القديمة"},
                    ],
                },
                {
                    "title": "الصفحات المحلية",
                    "description": "المدن والأحياء والخدمات وصفحات الخدمة المحلية.",
                    "items": [
                        {"label": "المدن", "url": admin_link("city"), "note": "مدن ثابتة للاختيار والربط"},
                        {"label": "الأحياء", "url": admin_link("district"), "note": "الأحياء الثابتة وصفحاتها المحلية"},
                        {"label": "الخدمات", "url": admin_link("service"), "note": "الخدمات الأساسية"},
                        {"label": "الخدمات داخل المدن", "url": admin_link("cityservicepage"), "note": "صفحات /city/service/"},
                    ],
                },
                {
                    "title": "المحتوى",
                    "description": "الصفحات والمقالات والمشاريع.",
                    "items": [
                        {"label": "الصفحات", "url": admin_link("page"), "note": "صفحات مخصصة وثابتة"},
                        {"label": "المقالات", "url": admin_link("blogpost"), "note": "محتوى المدونة"},
                        {"label": "تصنيفات المقالات", "url": admin_link("blogcategory"), "note": "تنظيم المقالات"},
                        {"label": "الوسوم", "url": admin_link("blogtag"), "note": "ربط مواضيع المدونة"},
                        {"label": "المشاريع", "url": admin_link("project"), "note": "نماذج الأعمال"},
                    ],
                },
                {
                    "title": "العملاء والثقة",
                    "description": "طلبات العملاء والتقييمات الحقيقية.",
                    "items": [
                        {"label": "طلبات العملاء", "url": admin_link("lead"), "note": "الاستفسارات والعملاء المحتملون"},
                        {"label": "تقييمات العملاء", "url": admin_link("testimonial"), "note": "مراجعات موثقة تظهر في Schema"},
                    ],
                },
                {
                    "title": "الصور والوسائط",
                    "description": "صور الصفحات والمكتبة المستخدمة في الموقع.",
                    "items": [
                        {"label": "صور الصفحات", "url": admin_link("pagemedia"), "note": "صور الهيرو والمعارض"},
                        {"label": "صور مكتبة الموقع", "url": admin_link("libraryimage"), "note": "تصنيف الصور وربطها بالاستخدام"},
                    ],
                },
            ]
        except (OperationalError, ProgrammingError):
            extra_context["dashboard_stats"] = []
            extra_context["recent_leads"] = []
            extra_context["seo_issues"] = []
            extra_context["latest_seo_run"] = None
            extra_context["admin_groups"] = []
        extra_context["ai_generator_url"] = "admin:ai_content_generator"
        return super().index(request, extra_context=extra_context)


admin_site = ArabicAdminSite(name="arabic_admin")
