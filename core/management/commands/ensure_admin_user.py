import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create a Django superuser once; existing passwords are only reset when explicitly requested."

    def handle(self, *args, **options):
        username = os.environ.get("DJANGO_SUPERUSER_USERNAME", "").strip()
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "").strip()
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "")

        if not username:
            self.stdout.write("DJANGO_SUPERUSER_USERNAME is not set; skipping admin user setup.")
            return

        User = get_user_model()
        existing_user = User.objects.filter(username=username).first()
        if existing_user is None and not password:
            self.stderr.write(
                "DJANGO_SUPERUSER_PASSWORD is not set; refusing to create an admin without a usable password."
            )
            return

        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                "email": email,
                "is_staff": True,
                "is_superuser": True,
            },
        )

        changed_fields = []
        if email and user.email != email:
            user.email = email
            changed_fields.append("email")
        if not user.is_staff:
            user.is_staff = True
            changed_fields.append("is_staff")
        if not user.is_superuser:
            user.is_superuser = True
            changed_fields.append("is_superuser")
        force_password_reset = os.environ.get("DJANGO_SUPERUSER_FORCE_PASSWORD_RESET", "").lower() in {"1", "true", "yes"}
        if password and (created or force_password_reset):
            user.set_password(password)
            changed_fields.append("password")

        if created or changed_fields:
            user.save()

        action = "created" if created else "updated" if changed_fields else "already exists"
        self.stdout.write(self.style.SUCCESS(f"Admin user {username!r} {action}."))
