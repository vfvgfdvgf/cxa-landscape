from django.core.management.base import BaseCommand

from core.local_seo import ensure_local_service_pages, seed_default_cities_and_services


class Command(BaseCommand):
    help = "Seed default cities/services and generate SEO city-service pages."

    def add_arguments(self, parser):
        parser.add_argument("--overwrite", action="store_true", help="Rewrite existing generated city-service SEO fields.")

    def handle(self, *args, **options):
        seeded = seed_default_cities_and_services()
        pages = ensure_local_service_pages(overwrite=options["overwrite"])
        self.stdout.write(
            self.style.SUCCESS(
                "Local SEO complete: "
                f"cities created={seeded['cities']}, services created={seeded['services']}, "
                f"pages created={pages['created']}, pages updated={pages['updated']}"
            )
        )
