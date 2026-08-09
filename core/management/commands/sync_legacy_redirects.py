from django.core.management.base import BaseCommand

from core.redirects import sync_legacy_redirects


class Command(BaseCommand):
    help = "Create redirects from old local service slugs to the new SEO slugs."

    def handle(self, *args, **options):
        result = sync_legacy_redirects()
        self.stdout.write(self.style.SUCCESS(f"Legacy redirects synced. New={result['created']} updated={result['updated']}"))
