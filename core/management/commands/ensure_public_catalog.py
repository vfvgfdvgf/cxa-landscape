from django.core.management import BaseCommand, call_command

from core.location_data import FIXED_DISTRICTS
from core.management.commands.bootstrap_nakheel_najd import LOCAL_SOLUTION_CATEGORIES
from core.models import City, CityServicePage, Project, Service
from core.nakheel_content import ALL_SERVICE_SPECS, SERVICE_SPECS
from core.project_media import PROJECT_MEDIA


class Command(BaseCommand):
    help = "Ensure the production service catalogue and local project showcase exist without rebuilding them on every restart."

    def _status(self):
        expected_city_slugs = set(FIXED_DISTRICTS)
        service_slugs = [spec.slug for spec in ALL_SERVICE_SPECS]
        local_service_slugs = [spec.slug for spec in SERVICE_SPECS]
        expected_portfolio = len(PROJECT_MEDIA)
        seeded_project_slugs = [f"nakheel-najd-project-{index:02d}" for index in range(1, expected_portfolio + 1)]

        system_cities = list(
            City.objects.filter(is_active=True, is_system=True, slug__in=expected_city_slugs)
            .only("pk", "slug")
            .order_by("pk")
        )
        city_ids = [city.pk for city in system_cities]
        city_slugs = {city.slug for city in system_cities}
        expected_local = len(expected_city_slugs) * len(LOCAL_SOLUTION_CATEGORIES)
        expected_local_pages = len(expected_city_slugs) * len(local_service_slugs)
        expected_local_solution_slugs = {
            f"local-solution-{city_slug}-{slot + 1:02d}"
            for city_slug in expected_city_slugs
            for slot in range(len(LOCAL_SOLUTION_CATEGORIES))
        }

        services = Service.objects.filter(is_visible=True, slug__in=service_slugs).count()
        portfolio = Project.objects.filter(
            is_visible=True, record_type="portfolio", slug__in=seeded_project_slugs,
        ).count()
        local = Project.objects.filter(
            is_visible=True, record_type="local_solution", slug__in=expected_local_solution_slugs,
        ).count()
        local_pages = 0
        if city_ids:
            local_pages = CityServicePage.objects.filter(
                is_active=True, city_id__in=city_ids, service__slug__in=local_service_slugs,
            ).count()

        expected = {
            "cities": len(expected_city_slugs),
            "services": len(service_slugs),
            "portfolio": expected_portfolio,
            "local": expected_local,
            "local_pages": expected_local_pages,
        }
        actual = {
            "cities": len(city_slugs),
            "services": services,
            "portfolio": portfolio,
            "local": local,
            "local_pages": local_pages,
        }
        ok = all(actual[key] == value for key, value in expected.items())
        return ok, actual, expected

    def handle(self, *args, **options):
        ready, actual, expected = self._status()
        if ready:
            self.stdout.write(self.style.SUCCESS(
                "Public catalogue ready: " + ", ".join(f"{key}={actual[key]}/{expected[key]}" for key in expected)
            ))
            return

        self.stdout.write(
            "Public catalogue incomplete; syncing safely: "
            + ", ".join(f"{key}={actual[key]}/{expected[key]}" for key in expected)
        )
        call_command("bootstrap_nakheel_najd", "--catalog-only")

        ready, actual, expected = self._status()
        if not ready:
            raise RuntimeError(
                "Catalogue verification failed after sync: "
                + ", ".join(f"{key}={actual[key]}/{expected[key]}" for key in expected)
            )
        self.stdout.write(self.style.SUCCESS(
            "Public catalogue synced: " + ", ".join(f"{key}={actual[key]}/{expected[key]}" for key in expected)
        ))
