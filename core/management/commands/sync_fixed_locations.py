from django.core.management.base import BaseCommand

from core.local_seo import sync_fixed_city_catalog


class Command(BaseCommand):
    help = "Create/update the fixed Saudi city and district catalog without deleting business content."

    def handle(self, *args, **options):
        counts = sync_fixed_city_catalog()
        self.stdout.write(
            self.style.SUCCESS(
                f"Synced {counts['cities']} cities and {counts['districts']} districts."
            )
        )
