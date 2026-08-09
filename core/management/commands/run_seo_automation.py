import json
import os

from django.core.management.base import BaseCommand
from django.utils import timezone

from core.local_seo import ensure_local_service_pages, seed_default_cities_and_services
from core.management.commands.daily_ai_seo import request_ai_seo_update, search_web
from core.models import SEOAutomationRun, SEOReportIssue, SearchConsoleQuery, SiteSettings
from core.redirects import sync_legacy_redirects
from core.search_console import fetch_search_console_queries
from core.seo_audit import run_seo_audit


def _research_queries(settings_obj):
    configured = [item.strip() for item in (settings_obj.ai_seo_research_queries or "").splitlines() if item.strip()]
    if configured:
        return configured[:8]
    gsc_queries = list(
        SearchConsoleQuery.objects.order_by("-impressions", "position").values_list("query", flat=True)[:5]
    )
    fallback = [
        "تنسيق حدائق السعودية لاندسكيب",
        "تصميم حدائق فلل السعودية",
        "زراعة نخيل وأشجار حدائق السعودية",
        "أنظمة ري حدائق السعودية",
    ]
    return list(dict.fromkeys([*gsc_queries, *fallback]))[:8]


class Command(BaseCommand):
    help = "Run the full daily SEO automation: GSC, local pages, redirects, audit, and optional AI improvements."

    def add_arguments(self, parser):
        parser.add_argument("--host", default="127.0.0.1:8000")
        parser.add_argument("--apply-ai", action="store_true", help="Apply AI SEO changes if OpenAI is configured.")
        parser.add_argument("--dry-run-ai", action="store_true", help="Ask AI but do not save its suggested changes.")
        parser.add_argument("--skip-ai", action="store_true", help="Run all SEO automation except AI.")
        parser.add_argument("--force", action="store_true", help="Run even if SiteSettings.ai_seo_enabled is off.")

    def handle(self, *args, **options):
        settings_obj = SiteSettings.load()
        run = SEOAutomationRun.objects.create(status="running", summary="بدأ تشغيل أتمتة SEO اليومية.")

        try:
            if not settings_obj.ai_seo_enabled and not options["force"]:
                run.status = "skipped"
                run.summary = "تم تجاوز التشغيل لأن أتمتة SEO غير مفعلة من إعدادات الموقع."
                run.finished_at = timezone.now()
                run.save()
                self.stdout.write(self.style.WARNING(run.summary))
                return

            search_result = fetch_search_console_queries()
            run.search_console_result = search_result

            issues_before = run_seo_audit(host=options["host"])
            run.issues_before = len(issues_before)

            seed_default_cities_and_services()
            local_result = ensure_local_service_pages(overwrite=False)
            run.local_seo_result = local_result

            redirects_result = sync_legacy_redirects()
            run.redirects_result = redirects_result

            # AI changes are never applied only because a database flag is enabled.
            # A human/operator must pass --apply-ai explicitly for every applying run.
            should_apply_ai = bool(options["apply_ai"])
            ai_allowed = not options["skip_ai"] and (should_apply_ai or options["dry_run_ai"])
            if settings_obj.ai_seo_auto_apply and not should_apply_ai:
                self.stdout.write(
                    self.style.WARNING(
                        "تم تجاهل خيار التطبيق التلقائي القديم. استخدم --apply-ai صراحةً بعد مراجعة النسخة الاحتياطية."
                    )
                )
            if ai_allowed:
                run.ai_requested = True
                research = []
                for query in _research_queries(settings_obj):
                    try:
                        research.append({"query": query, "results": search_web(query)})
                    except Exception as exc:
                        research.append({"query": query, "error": str(exc), "results": []})
                prompt = (
                    "حسّن SEO الموقع تلقائيًا بناءً على Search Console وتقرير SEO الحالي. "
                    "ركّز على العناوين والوصف وصفحات المدن والخدمات والمقالات، وأضف محتوى فقط عندما توجد فجوة واضحة. "
                    "لا تضف أسعارًا أو وعودًا غير مثبتة، ولا تغيّر هوية الموقع."
                )
                previous_flag = os.environ.get("AI_DAILY_SEO_ENABLED")
                if should_apply_ai:
                    os.environ["AI_DAILY_SEO_ENABLED"] = "True"
                try:
                    ai_result = request_ai_seo_update(
                        prompt,
                        research,
                        dry_run=options["dry_run_ai"] or not should_apply_ai,
                        publish_now=False,
                    )
                    run.ai_result = ai_result if isinstance(ai_result, dict) else {"result": ai_result}
                    run.ai_applied = bool(should_apply_ai and not options["dry_run_ai"])
                finally:
                    if previous_flag is None:
                        os.environ.pop("AI_DAILY_SEO_ENABLED", None)
                    else:
                        os.environ["AI_DAILY_SEO_ENABLED"] = previous_flag

            issues_after = run_seo_audit(host=options["host"])
            run.issues_after = len(issues_after)
            run.status = "completed"
            run.finished_at = timezone.now()
            run.summary = (
                f"اكتمل التشغيل. مشاكل قبل={run.issues_before}, بعد={run.issues_after}, "
                f"Search Console={search_result.get('saved', 0)}, AI={'طبق' if run.ai_applied else 'لم يطبق'}."
            )
            run.save()
            self.stdout.write(self.style.SUCCESS(run.summary))
            self.stdout.write(json.dumps({
                "search_console": run.search_console_result,
                "local_seo": run.local_seo_result,
                "redirects": run.redirects_result,
                "issues_open": SEOReportIssue.objects.filter(status="open").count(),
                "ai_applied": run.ai_applied,
            }, ensure_ascii=False, indent=2))
        except Exception as exc:
            run.status = "failed"
            run.error_message = str(exc)
            run.finished_at = timezone.now()
            run.save()
            raise
