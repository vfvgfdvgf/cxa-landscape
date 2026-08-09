from django.core.management.base import BaseCommand

from core.search_console import fetch_search_console_queries


class Command(BaseCommand):
    help = "Fetch query/page performance from Google Search Console."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=28)
        parser.add_argument("--row-limit", type=int, default=250)

    def handle(self, *args, **options):
        result = fetch_search_console_queries(days=options["days"], row_limit=options["row_limit"])
        if result.get("skipped"):
            self.stdout.write(self.style.WARNING(f"Search Console skipped: {result['skipped']}"))
        else:
            self.stdout.write(self.style.SUCCESS(f"Search Console fetched={result['fetched']} saved={result['saved']}"))
