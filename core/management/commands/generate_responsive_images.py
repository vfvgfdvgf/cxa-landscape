from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from PIL import Image, ImageOps, UnidentifiedImageError

WIDTHS = (320, 480, 768, 1200)
SUPPORTED = {".jpg", ".jpeg", ".png", ".webp"}


class Command(BaseCommand):
    help = "Generate lightweight responsive WebP + AVIF variants for local static images."

    def handle(self, *args, **options):
        source_dir = settings.BASE_DIR / "imge"
        created = 0
        skipped = 0
        for source in source_dir.iterdir() if source_dir.exists() else []:
            if not source.is_file() or source.suffix.lower() not in SUPPORTED or "-w" in source.stem:
                continue
            try:
                with Image.open(source) as opened:
                    image = ImageOps.exif_transpose(opened)
                    if getattr(image, "is_animated", False):
                        skipped += 1
                        continue
                    if image.mode != "RGB":
                        image = image.convert("RGB")
                    for width in WIDTHS:
                        if image.width < width:
                            continue
                        height = max(1, round(image.height * width / image.width))
                        resized = image.resize((width, height), Image.Resampling.LANCZOS)
                        webp = source.with_name(f"{source.stem}-w{width}.webp")
                        avif = source.with_name(f"{source.stem}-w{width}.avif")
                        resized.save(webp, "WEBP", quality=72, method=6)
                        resized.save(avif, "AVIF", quality=48)
                        created += 2
            except (UnidentifiedImageError, OSError, ValueError):
                skipped += 1
        self.stdout.write(self.style.SUCCESS(f"Generated {created} responsive image files; skipped {skipped}."))
