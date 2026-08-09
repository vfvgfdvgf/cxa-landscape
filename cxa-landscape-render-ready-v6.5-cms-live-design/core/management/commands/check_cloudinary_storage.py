from base64 import b64decode

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError

PNG_1X1 = b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")


class Command(BaseCommand):
    help = "Verify that production media storage can create and delete a tiny test image."

    def handle(self, *args, **options):
        if not getattr(settings, "USE_CLOUDINARY_MEDIA", False):
            raise CommandError("USE_CLOUDINARY_MEDIA is disabled; no Cloudinary upload test was performed.")
        name = "diagnostics/cxa-cloudinary-write-check.png"
        saved_name = ""
        try:
            saved_name = default_storage.save(name, ContentFile(PNG_1X1, name="cxa-cloudinary-write-check.png"))
            if not saved_name:
                raise RuntimeError("storage.save() returned an empty name")
            self.stdout.write(self.style.SUCCESS(f"Cloudinary create permission OK: {saved_name}"))
        except Exception as exc:
            raise CommandError(
                "Cloudinary write test failed. Check that the API key used by Render has asset create/upload "
                f"permission. Provider error: {exc.__class__.__name__}: {exc}"
            ) from exc
        finally:
            if saved_name:
                try:
                    default_storage.delete(saved_name)
                except Exception as exc:
                    self.stderr.write(self.style.WARNING(
                        f"Upload succeeded but diagnostic cleanup failed for {saved_name}: {exc.__class__.__name__}: {exc}"
                    ))
