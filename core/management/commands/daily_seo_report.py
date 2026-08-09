from django.core.management.base import BaseCommand

from core.seo_audit import run_seo_audit


class Command(BaseCommand):
    help = "Create/update the daily SEO report shown in the admin."

    def add_arguments(self, parser):
        parser.add_argument("--host", default="127.0.0.1:8000")

    def handle(self, *args, **options):
        issues = run_seo_audit(host=options["host"])
        self.stdout.write(self.style.SUCCESS(f"SEO report complete. Open issues found: {len(issues)}"))
