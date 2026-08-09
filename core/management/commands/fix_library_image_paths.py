from django.core.management.base import BaseCommand
from django.core.files.storage import default_storage
from django.core.cache import cache
from django.utils import timezone

from core.models import LibraryImage, normalize_image_field_name


class Command(BaseCommand):
    help = "Normalize duplicated LibraryImage media paths stored in the database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would change without saving updates.",
        )
        parser.add_argument(
            "--store-db-fallback",
            action="store_true",
            help="Legacy only: also copy image bytes into the database as a fallback.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        store_db_fallback = options["store_db_fallback"]
        fixed_count = 0
        stored_count = 0

        for item in LibraryImage.objects.exclude(image="").exclude(image__isnull=True).iterator():
            current_name = item.image.name
            normalized_name = normalize_image_field_name(current_name, "library-images")
            source_name = normalize_image_field_name(f"library-images/{item.source_name}", "library-images") if item.source_name else ""
            if source_name and not default_storage.exists(normalized_name) and default_storage.exists(source_name):
                normalized_name = source_name

            changed_path = current_name != normalized_name

            if changed_path:
                fixed_count += 1
                self.stdout.write(f"{current_name} -> {normalized_name}")

            item.image.name = normalized_name
            if store_db_fallback and not item.image_data:
                item.store_image_in_database()
                if item.image_data:
                    stored_count += 1

            if not changed_path and not (store_db_fallback and item.image_data):
                continue

            if not dry_run:
                updates = {"image": normalized_name, "updated_at": timezone.now()}
                if store_db_fallback:
                    updates.update(
                        image_data=item.image_data,
                        image_stored=bool(item.image_data),
                        image_content_type=item.image_content_type,
                        image_filename=item.image_filename,
                    )
                LibraryImage.objects.filter(pk=item.pk).update(**updates)

        if dry_run:
            self.stdout.write(self.style.WARNING(f"Dry run complete. Paths to fix: {fixed_count}. Legacy DB copies: {stored_count}"))
        else:
            cache.delete("library:records")
            self.stdout.write(self.style.SUCCESS(f"Library image paths fixed: {fixed_count}. Legacy DB copies: {stored_count}"))
