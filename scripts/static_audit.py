#!/usr/bin/env python3
"""Offline release audit for Nakheel Najd.

Runs without importing Django or connecting to PostgreSQL, Cloudinary, or
TokenMix. Django's runtime checks and tests remain part of scripts/verify.sh.
"""

from __future__ import annotations

import ast
import re
import runpy
import subprocess
import sys
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_PARTS = {
    ".git", ".next", ".venv", ".venv-test", "__pycache__",
    "media", "node_modules", "staticfiles_build",
}
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif"}
RESPONSIVE_WIDTHS = (320, 480, 768, 1200)
VARIANT_RE = re.compile(r"-w(320|480|768|1200)\.(webp|avif)$", re.IGNORECASE)
STATIC_REF_RE = re.compile(r"{%\s*static\s+['\"]([^'\"]+)['\"]\s*%}")

errors: list[str] = []
warnings: list[str] = []
stats: Counter[str] = Counter()


def fail(message: str) -> None:
    errors.append(message)


def warn(message: str) -> None:
    warnings.append(message)


def project_files(pattern: str):
    for path in ROOT.rglob(pattern):
        if any(part in EXCLUDED_PARTS for part in path.parts):
            continue
        yield path


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8-sig")


def is_git_tracked(path: Path) -> bool:
    try:
        result = subprocess.run(
            ["git", "ls-files", "--error-unmatch", "--", path.relative_to(ROOT).as_posix()],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except (OSError, ValueError):
        return True
    return result.returncode == 0


def check_python() -> None:
    for path in project_files("*.py"):
        stats["python_files"] += 1
        try:
            source = path.read_text(encoding="utf-8-sig")
            tree = ast.parse(source, filename=str(path))
        except (OSError, UnicodeError, SyntaxError) as exc:
            fail(f"Python parse failed: {path.relative_to(ROOT)}: {exc}")
            continue

        names = [
            node.name
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        ]
        duplicates = sorted(name for name, count in Counter(names).items() if count > 1)
        if duplicates:
            fail(f"Duplicate top-level definitions in {path.relative_to(ROOT)}: {', '.join(duplicates)}")


def check_templates() -> None:
    static_refs: set[str] = set()
    for path in project_files("*.html"):
        if "templates" not in path.parts:
            continue
        stats["template_files"] += 1
        text = path.read_text(encoding="utf-8-sig")
        for left, right, label in (("{{", "}}", "variable"), ("{%", "%}", "tag"), ("{#", "#}", "comment")):
            if text.count(left) != text.count(right):
                fail(f"Unbalanced Django {label} delimiters in {path.relative_to(ROOT)}")
        for match in re.finditer(r"<img\b[^>]*>", text, flags=re.IGNORECASE | re.DOTALL):
            stats["image_tags"] += 1
            tag = match.group(0)
            if not re.search(r"\balt\s*=", tag, flags=re.IGNORECASE):
                fail(f"Image without alt in {path.relative_to(ROOT)} near offset {match.start()}")
            if "decoding=" not in tag:
                warn(f"Image without decoding hint in {path.relative_to(ROOT)} near offset {match.start()}")
        static_refs.update(STATIC_REF_RE.findall(text))

        if re.search(r"(?:content|description|body)\s*\|\s*safe(?!_html)", text):
            fail(f"Raw rich-text HTML marked safe in {path.relative_to(ROOT)}")

    for relative in sorted(static_refs):
        if not (ROOT / "static" / relative).exists():
            fail(f"Missing static asset referenced by template: static/{relative}")
    stats["static_references"] = len(static_refs)

    required_templates = (
        "templates/cities/detail.html",
        "templates/cities/district_detail.html",
        "templates/cities/service_detail.html",
        "templates/pages/home.html",
        "templates/partials/header.html",
        "templates/partials/conversion_bar.html",
    )
    for filename in required_templates:
        if not (ROOT / filename).exists():
            fail(f"Required template missing: {filename}")


def check_css() -> None:
    for path in project_files("*.css"):
        stats["css_files"] += 1
        text = path.read_text(encoding="utf-8-sig")
        scrubbed = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
        if scrubbed.count("{") != scrubbed.count("}"):
            fail(f"Unbalanced CSS braces in {path.relative_to(ROOT)}")


def check_frontend_contract() -> None:
    base = read("templates/base.html")
    js = read("static/js/site-v4-4.js")
    conversion = read("templates/partials/conversion_bar.html")
    required_base = (
        'id="swup"',
        "css/site-v4-4.css",
        "js/site-v4-4.js",
    )
    for marker in required_base:
        if marker not in base:
            fail(f"Missing frontend navigation/design marker: {marker}")
    forbidden_external = ("unpkg.com/swup", "@swup/head-plugin", "@swup/preload-plugin")
    for marker in forbidden_external:
        if marker in base:
            fail(f"External navigation dependency must not remain: {marker}")
    for marker in ("initFastNavigation", "DOMParser", "history.pushState", "popstate", "X-Requested-With", "startViewTransition"):
        if marker not in js:
            fail(f"Missing local fast-navigation marker: {marker}")
    home = read("templates/pages/home.html")
    for marker in ("hero_desktop.image_url", "hero_mobile.image_url", 'class="nn-brand-marquee"', 'fetchpriority="high"', "data-project-stack", "data-services-track", "nn-saudi-map"):
        if marker not in home:
            fail(f"Missing V4.4 home experience marker: {marker}")
    header = read("templates/partials/header.html")
    for marker in ("initMotionSections", "ScrollTrigger"):
        if marker not in js:
            fail(f"Missing V4.4 motion marker: {marker}")
    for marker in ("data-open-search", "data-menu-overlay"):
        if marker not in header:
            fail(f"Missing V4.4 shell marker: {marker}")
    if 'nn-language-chip' in header or '>AR<' in header or '>EN<' in header:
        fail("Public header must remain Arabic-only without language chips")
    if '<html lang="ar" dir="rtl">' not in base:
        fail("Base template must force Arabic RTL document direction")
    if "saudi-arabia-outline.svg" not in home:
        fail("Accurate Saudi outline asset is not used on the homepage")
    font_css = read("static/css/thmanyah.css")
    bundle = read("static/css/site-v4-4.css")
    for marker in ("Thmanyah Sans", "Thmanyah Serif Display", "Thmanyah Serif Text"):
        if marker not in font_css or marker not in bundle:
            fail(f"Missing Thmanyah type-system marker: {marker}")
    for marker in ("static/css/style.css", "static/css/nakheel-najd-v4-1.css", "static/css/nakheel-najd-v4-2.css", "static/css/nakheel-najd-v4-3.css", "static/css/nakheel-najd-v4-4.css", "nn-brand-marquee"):
        if marker not in bundle:
            fail(f"Public CSS bundle is stale or incomplete: {marker}")
    if not (ROOT / "scripts/install_thmanyah_fonts.py").exists():
        fail("Missing owner-font installer script")
    if not (ROOT / "scripts/build_public_assets.py").exists():
        fail("Missing deterministic public CSS build script")
    if "data-swup-form" not in "".join(path.read_text(encoding="utf-8") for path in project_files("*.html")):
        fail("No progressively enhanced GET form found")
    if "whatsapp.svg" not in conversion:
        fail("Compact conversion bar must use the WhatsApp SVG icon")
    if "tel:" in conversion:
        fail("The compact conversion bar must not contain a phone-call button")

    package_json = read("frontend/package.json")
    if '"node": "22.x"' not in package_json:
        fail("Frontend Node.js runtime must stay pinned to the Node 22 LTS line")

    next_config = read("frontend/next.config.ts")
    if "Strict-Transport-Security" not in next_config:
        fail("The public Next.js domain must send HSTS, not only the Django backend")
    for marker in ("apiHostname", "hostname: apiHostname", "${apiOrigin}"):
        if marker not in next_config:
            fail(f"Next image configuration is not tied to the Django API host: {marker}")
    if "cxa-landscape.onrender.com" in next_config:
        fail("Retired Django hostname remains in the Next image configuration")

    responsive_image = read("frontend/components/content/ResponsiveImage.tsx")
    for marker in ('type="image/avif"', "preferredImageUrl", "srcSet", "fetchPriority", 'loading={priority ? "eager" : "lazy"}'):
        if marker not in responsive_image:
            fail(f"Fast responsive image pipeline is incomplete: {marker}")
    image_helpers = read("frontend/lib/images.ts")
    for marker in ("/media/", "avif_url", "imageSourceSet", "preferredImageUrl"):
        if marker not in image_helpers:
            fail(f"Frontend image helper is incomplete: {marker}")
    media_copy = read("frontend/scripts/copy-public-media.mjs")
    for marker in ("public", "media", "imge", "cp"):
        if marker not in media_copy:
            fail(f"Frontend media copy step is incomplete: {marker}")
    if '"prebuild": "node scripts/copy-public-media.mjs"' not in package_json:
        fail("Frontend build must mirror optimized portfolio media into Next public/media")
    media_budget = read("frontend/lib/media-budget.ts")
    page_hero = read("frontend/components/ui/PageHero.tsx")
    api_utils = read("core/api/utils.py")
    if "enforceHomeMediaBudget" not in media_budget or "maxUses = 3" not in media_budget:
        fail("Frontend homepage media repetition protection is missing")
    if "cap_repeated_media" not in api_utils or "max_uses=3" not in api_utils:
        fail("Public API media repetition protection is missing")
    if 'videoSrc = "/videos/story-finished.mp4"' in page_hero or "INTERIOR_HERO_MEDIA" not in page_hero:
        fail("Interior pages still depend on one repeated default hero video")
    if '/media/:path*' not in next_config or 'max-age=86400, s-maxage=31536000, stale-while-revalidate=604800' not in next_config:
        fail("Frontend media must use short browser cache plus long shared-CDN cache headers")

    frontend_css = read("frontend/app/globals.css")
    if ".content-card__media > .image-frame" not in frontend_css:
        fail("Fill images inside content cards do not have a stable containing block")

    middleware = read("core/middleware.py")
    for marker in ('"/static/"', '"cross-origin"'):
        if marker not in middleware:
            fail(f"Cross-origin static image support is missing: {marker}")

    settings_py = read("project/settings.py")
    if "django.middleware.gzip.GZipMiddleware" not in settings_py:
        fail("GZipMiddleware is required to compress JSON/API responses")
    api_content = read("core/api/views/content.py")
    for marker in ("ServiceCardSerializer", "ProjectCardSerializer", "ArticleCardSerializer", "CityServiceCardSerializer"):
        if marker not in api_content:
            fail(f"Compact API card payload is missing: {marker}")
    api_utils = read("core/api/utils.py")
    if "_cloudinary_variants" not in api_utils or "q_auto:eco" not in api_utils:
        fail("Cloudinary responsive delivery transformations are missing")
    for marker in ("Existence checks are enough here", "webp.is_file()", "avif.is_file()"):
        if marker not in api_utils:
            fail(f"Fast static-image variant serialization is missing: {marker}")

    home_site = read("core/api/views/site.py")
    home_serializer = read("core/api/serializers/content.py")
    for marker in ("HomeCitySerializer", 'record_type="portfolio"', 'district_count=Count(', "project_counts ="):
        if marker not in home_site:
            fail(f"Optimized/trustworthy homepage API marker is missing: {marker}")
    if "class HomeCitySerializer" not in home_serializer or "district_count" not in home_serializer:
        fail("Compact homepage city serializer is missing")

    google_route = read("frontend/app/api/site-verification/google/[token]/route.ts")
    if "site?.verification?.html_files" not in google_route:
        fail("Google verification route must safely optional-chain the verification payload")

    gitignore = read(".gitignore")
    if "frontend/public/media/" not in gitignore:
        fail("Generated Next public/media mirror must stay ignored by Git")
    if "\nmedia/\n" in f"\n{gitignore}\n":
        fail("Generic media/ ignore rule would hide frontend/components/media source files; use /media/ for Django root media only")
    if not (ROOT / "frontend/components/media/CinematicVideo.tsx").exists():
        fail("CinematicVideo source component is missing")

    route_data = read("frontend/lib/page-data.ts")
    if "normalizeRouteParam" not in route_data:
        fail("Unicode route parameter normalization is missing")

    public_copy = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / "frontend" / "app").rglob("*.tsx"))
    for internal_phrase in (
        "الخدمات المنشورة والمدارة من لوحة Django",
        "مشاريع وصور مرتبطة بسجلات Django",
        "مقالات حقيقية يديرها فريق المحتوى من Django",
        "خادم Next.js إلى Django",
    ):
        if internal_phrase in public_copy:
            fail(f"Internal implementation copy leaked into the public frontend: {internal_phrase}")

    districts_page = read("frontend/app/districts/page.tsx")
    for marker in ('withQuery("districts/"', "DistrictCard", 'href="/districts/"'):
        if marker not in districts_page:
            fail(f"District directory contract is incomplete: {marker}")


def check_images() -> None:
    image_dir = ROOT / "imge"
    if not image_dir.exists():
        warn("imge directory is missing")
        return
    try:
        from PIL import Image
    except Exception as exc:  # pragma: no cover
        warn(f"Pillow unavailable; image integrity checks skipped: {exc}")
        return

    originals = []
    variants = {}
    for path in sorted(image_dir.iterdir()):
        if not path.is_file() or path.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        stats["image_files"] += 1
        variant_match = VARIANT_RE.search(path.name)
        try:
            with Image.open(path) as image:
                image.verify()
            with Image.open(path) as image:
                width, height = image.size
        except Exception as exc:
            fail(f"Invalid image {path.name}: {exc}")
            continue
        if width < 1 or height < 1:
            fail(f"Invalid image dimensions for {path.name}: {width}x{height}")
        if variant_match:
            expected_width = int(variant_match.group(1))
            if width != expected_width:
                fail(f"Responsive image width mismatch: {path.name} is {width}px, expected {expected_width}px")
            variants[path.name] = width
        else:
            originals.append((path, width))

    original_names = {path.name for path, _width in originals}
    expected_originals = ({f"project-{index:02d}.webp" for index in range(1, 54)} | {f"archive-project-{index:02d}.webp" for index in range(1, 41)} | {"hero-desktop.webp", "hero-mobile.webp"})
    for filename in sorted(expected_originals - original_names):
        fail(f"Missing owner-supplied/hero image: {filename}")
    for filename in sorted(original_names - expected_originals):
        fail(f"Legacy or uncurated image remains in imge/: {filename}")

    for source, source_width in originals:
        for width in RESPONSIVE_WIDTHS:
            if source_width < width:
                continue
            for suffix in ("webp", "avif"):
                expected = source.with_name(f"{source.stem}-w{width}.{suffix}")
                if not expected.exists():
                    fail(f"Missing responsive variant: {expected.name}")

    stats["original_images"] = len(originals)
    stats["responsive_images"] = len(variants)


def check_content_catalog() -> None:
    try:
        locations = runpy.run_path(str(ROOT / "core/location_data.py"))
        content = runpy.run_path(str(ROOT / "core/nakheel_content.py"))
        fixed_districts = locations["FIXED_DISTRICTS"]
        service_specs = content["SERVICE_SPECS"]
        all_service_specs = content["ALL_SERVICE_SPECS"]
        article_topics = content["ARTICLE_TOPICS"]
        project_media = runpy.run_path(str(ROOT / "core/project_media.py"))["PROJECT_MEDIA"]
    except Exception as exc:
        fail(f"Unable to load fixed content catalogs: {exc}")
        return

    city_count = len(fixed_districts)
    district_count = sum(len(items) for items in fixed_districts.values())
    stats["fixed_cities"] = city_count
    stats["fixed_districts"] = district_count
    stats["service_specs"] = len(service_specs)
    stats["all_service_specs"] = len(all_service_specs)
    stats["article_topics"] = len(article_topics)
    stats["project_media"] = len(project_media)
    if city_count != 12:
        fail(f"Expected 12 fixed cities, found {city_count}")
    if district_count != 330:
        fail(f"Expected 330 fixed operational districts, found {district_count}")
    if len(service_specs) != 50:
        fail(f"Expected exactly 50 local service specifications, found {len(service_specs)}")
    if len(all_service_specs) != 250:
        fail(f"Expected exactly 250 nationwide catalogue services, found {len(all_service_specs)}")
    if len(article_topics) != 50:
        fail(f"Expected exactly 50 article topics, found {len(article_topics)}")
    if len(project_media) != 93:
        fail(f"Expected exactly 93 curated project images, found {len(project_media)}")
    for item in project_media:
        if not (ROOT / "imge" / item["filename"]).exists():
            fail(f"Missing curated project image: {item['filename']}")
    if len({spec.slug for spec in all_service_specs}) != len(all_service_specs):
        fail("Duplicate service slugs in ALL_SERVICE_SPECS")
    if any(len(spec.slug) > 140 for spec in all_service_specs):
        fail("A service specification slug exceeds Service.slug max_length=140")
    if any(len(spec.title) > 180 for spec in all_service_specs):
        fail("A service specification title exceeds Service.title max_length=180")

    sample_city = SimpleNamespace(slug="riyadh", name="الرياض")
    sample_district = SimpleNamespace(name="الياسمين")
    generated_html = [
        content["service_page_html"](spec, sample_city, sample_district)
        for spec in service_specs
    ] + [
        content["service_catalog_html"](spec)
        for spec in all_service_specs
    ] + [
        content["article_html"](topic, sample_city, sample_district, "توريد وزراعة النخيل")
        for topic in article_topics
    ]
    allowed_generated_tags = {"a", "div", "h2", "h3", "li", "ol", "p", "strong", "ul"}
    for index, html in enumerate(generated_html, start=1):
        if "javascript:" in html.lower() or "<script" in html.lower():
            fail(f"Unsafe generated HTML in catalog item {index}")
        tags = {match.group(1).lower() for match in re.finditer(r"</?([a-zA-Z0-9]+)\b", html)}
        unexpected = tags - allowed_generated_tags
        if unexpected:
            fail(f"Unexpected generated HTML tags in catalog item {index}: {', '.join(sorted(unexpected))}")

    bootstrap = read("core/management/commands/bootstrap_nakheel_najd.py")
    ensure_catalog = read("core/management/commands/ensure_public_catalog.py")
    for marker in ("FIXED_DISTRICTS", "CityServicePage", "expected_local_solution_slugs", '"local_pages"', "ALL_SERVICE_SPECS", "PROJECT_MEDIA"):
        if marker not in ensure_catalog:
            fail(f"Production catalogue integrity check is incomplete: {marker}")
    if "actual[key] == value" not in ensure_catalog:
        fail("Production catalogue verification must require exact seeded counts")
    for forbidden in (
        "PageMedia.objects.all().delete()",
        "ProjectImage.objects.all().delete()",
        "LibraryImage.objects.exclude(source_name__in=filenames).update(is_active=False)",
        "Project.objects.update_or_create",
        "LibraryImage.objects.update_or_create",
    ):
        if forbidden in bootstrap:
            fail(f"Destructive/overwrite-prone automatic catalogue operation remains: {forbidden}")
    for marker in ("ProjectImage rows belong to editors", "Treat library metadata and uploaded replacements as editor-owned"):
        if marker not in bootstrap:
            fail(f"Editor-owned media preservation marker is missing: {marker}")
    for marker in (
        'service__slug__in=local_service_slugs',
        "ALL_SERVICE_SPECS",
        'slug__startswith="nakheel-najd-"',
        'BRAND_NAME = "نخيل نجد"',
        'PHONE = "0554882724"',
        "_release_city_service_slug_collision",
        "_sync_media_and_projects",
        "PROJECT_MEDIA",
        "@transaction.atomic",
        'parser.add_argument("--publish"',
        '_seed_articles(publish=bool(options["publish"]))',
        '"coverage_city": coverage_city',
        '"coverage_district": coverage_district',
        '"record_type": "local_solution"',
        '"is_indexable": False',
    ):
        if marker not in bootstrap:
            fail(f"Missing Nakheel Najd bootstrap marker: {marker}")
    if '_seed_articles(publish=not options["draft"])' in bootstrap:
        fail("Generated local articles must remain drafts unless --publish is explicit")


    legacy_scan = read("core/views.py") + read("core/project_media.py") + read("templates/pages/home.html")
    if "2026-03-21" in legacy_scan:
        fail("Legacy project-image references remain in active media code")

def check_api_view_exports() -> None:
    """Ensure every views.X referenced by API URLs is re-exported by core.api.views.

    core/api/urls.py imports the views package (not views.content directly), so a
    class can exist in content.py and still fail at Django startup if __init__.py
    forgets to expose it. Keep this check offline so Render catches regressions
    before django manage.py check runs.
    """
    urls_path = ROOT / "core/api/urls.py"
    init_path = ROOT / "core/api/views/__init__.py"
    try:
        urls_tree = ast.parse(urls_path.read_text(encoding="utf-8-sig"), filename=str(urls_path))
        init_tree = ast.parse(init_path.read_text(encoding="utf-8-sig"), filename=str(init_path))
    except Exception as exc:
        fail(f"Unable to parse API URL/view exports: {exc}")
        return

    referenced: set[str] = set()
    for node in ast.walk(urls_tree):
        if not isinstance(node, ast.Attribute):
            continue
        if isinstance(node.value, ast.Name) and node.value.id == "views":
            referenced.add(node.attr)

    exported: set[str] = set()
    for node in init_tree.body:
        if isinstance(node, ast.ImportFrom):
            exported.update(alias.asname or alias.name for alias in node.names)

    missing = sorted(referenced - exported)
    for name in missing:
        fail(f"API URL references views.{name}, but core.api.views does not export it")
    stats["api_url_views"] = len(referenced)


def check_internal_references() -> None:
    url_sources = [ROOT / "core/urls.py", ROOT / "project/urls.py"]
    url_names: set[str] = set()
    for path in url_sources:
        url_names.update(re.findall(r"\bname\s*=\s*['\"]([^'\"]+)", path.read_text(encoding="utf-8-sig")))

    missing_urls: set[tuple[str, str]] = set()
    for path in project_files("*.html"):
        text = path.read_text(encoding="utf-8-sig")
        for name in re.findall(r"{%\s*url\s+['\"]([^'\"]+)", text):
            if name not in url_names and not name.startswith("admin:"):
                missing_urls.add((str(path.relative_to(ROOT)), name))
    for path in project_files("*.py"):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
        except Exception:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not node.args:
                continue
            func_name = node.func.id if isinstance(node.func, ast.Name) else ""
            if func_name not in {"reverse", "reverse_lazy"}:
                continue
            if isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                name = node.args[0].value
                if name not in url_names and not name.startswith("admin:"):
                    missing_urls.add((str(path.relative_to(ROOT)), name))
    for path, name in sorted(missing_urls):
        fail(f"Missing URL name referenced by {path}: {name}")
    stats["url_names"] = len(url_names)

    command_dir = ROOT / "core/management/commands"
    commands = {path.stem for path in command_dir.glob("*.py") if path.stem != "__init__"}
    builtins = {"check", "collectstatic", "makemigrations", "migrate", "test"}
    for path in project_files("*.py"):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
        except Exception:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not node.args:
                continue
            if not isinstance(node.func, ast.Name) or node.func.id != "call_command":
                continue
            if isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                name = node.args[0].value
                if name not in commands and name not in builtins:
                    fail(f"Missing management command referenced by {path.relative_to(ROOT)}: {name}")
    stats["management_commands"] = len(commands)


def check_migration_graph() -> None:
    migration_dir = ROOT / "core/migrations"
    migration_files = {path.stem: path for path in migration_dir.glob("[0-9][0-9][0-9][0-9]_*.py")}
    dependencies: dict[str, set[str]] = {}
    for name, path in migration_files.items():
        try:
            tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
        except Exception as exc:
            fail(f"Migration parse failed: {path.name}: {exc}")
            continue
        deps: set[str] = set()
        for node in tree.body:
            if not isinstance(node, ast.ClassDef) or node.name != "Migration":
                continue
            for item in node.body:
                if not isinstance(item, ast.Assign):
                    continue
                if not any(isinstance(target, ast.Name) and target.id == "dependencies" for target in item.targets):
                    continue
                elements = item.value.elts if isinstance(item.value, (ast.List, ast.Tuple)) else []
                for element in elements:
                    if not isinstance(element, ast.Tuple) or len(element.elts) != 2:
                        continue
                    try:
                        app_name = ast.literal_eval(element.elts[0])
                        migration_name = ast.literal_eval(element.elts[1])
                    except Exception:
                        continue
                    if app_name == "core":
                        deps.add(migration_name)
        dependencies[name] = deps
        for dep in deps:
            if dep not in migration_files:
                fail(f"Migration {name} depends on missing core migration {dep}")

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(name: str) -> None:
        if name in visited:
            return
        if name in visiting:
            fail(f"Migration dependency cycle detected at {name}")
            return
        visiting.add(name)
        for dep in dependencies.get(name, set()):
            visit(dep)
        visiting.remove(name)
        visited.add(name)

    for name in migration_files:
        visit(name)

    depended_on = {dep for deps in dependencies.values() for dep in deps}
    leaves = sorted(set(migration_files) - depended_on)
    stats["migration_files"] = len(migration_files)
    stats["migration_leaves"] = len(leaves)
    if len(leaves) != 1:
        fail(f"Expected exactly one core migration leaf, found: {', '.join(leaves) or 'none'}")


def check_configuration() -> None:
    settings_text = read("project/settings.py")
    sanitizer = read("core/html_utils.py")
    if '"a": {"href", "title", "target", "rel"}' in sanitizer and "link_rel=" in sanitizer:
        fail("nh3 sanitizer config conflicts: rel cannot be allowlisted while link_rel is managed")
    for marker in ('"a": {"href", "title", "target"}', 'link_rel="noopener noreferrer"'):
        if marker not in sanitizer:
            fail(f"Missing safe nh3 sanitizer marker: {marker}")
    for marker in (
        "DJANGO_SECRET_KEY must be set",
        "django.core.cache.backends.locmem.LocMemCache",
        '"LOCATION": "nakheel-najd-cache"',
        "DATA_UPLOAD_MAX_MEMORY_SIZE",
        "SECURE_HSTS_SECONDS",
        '"site_brand": "نخيل نجد"',
    ):
        if marker not in settings_text:
            fail(f"Missing production setting safeguard/brand marker: {marker}")

    requirements = read("requirements.txt").lower()
    for package in ("django", "gunicorn", "whitenoise", "pillow", "nh3", "cloudinary"):
        if package not in requirements:
            fail(f"Required package missing from requirements.txt: {package}")
    if "django>=5.2.17,<5.3" not in requirements:
        fail("Django must stay on the security-patched 5.2.17+ LTS patch line")
    default_permission_is_safe = any(
        marker in settings_text.lower()
        for marker in (
            "rest_framework.permissions.isauthenticatedorreadonly",
            "core.api.permissions.publicreadonlypermission",
        )
    )
    if not default_permission_is_safe:
        fail("DRF must deny implemented writes by default; public submission views opt in explicitly")
    permissions_text = read("core/api/permissions.py")
    for marker in ("class PublicReadOnlyPermission", "request.method in SAFE_METHODS", "not callable(handler)"):
        if "publicreadonlypermission" in settings_text.lower() and marker not in permissions_text:
            fail(f"Custom DRF read-only permission is incomplete: {marker}")

    middleware = read("core/middleware.py")
    if "https://unpkg.com" in middleware or "\"script-src 'self' 'unsafe-inline' https:\"" in middleware:
        fail("Django CSP script-src is broader than the actual jsDelivr dependency")

    ai = read("core/ai_content.py")
    for marker in ("TOKENMIX_API_KEY", "TOKENMIX_BASE_URL", "TOKENMIX_MODEL", "/chat/completions"):
        if marker not in ai:
            fail(f"Missing TokenMix integration marker: {marker}")
    if "OPENAI_API_KEY" in ai:
        fail("OpenAI API key dependency remains in core/ai_content.py")

    search_console = read("core/search_console.py")
    admin_text = read("core/admin.py")
    if 'credentials_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()' not in search_console:
        fail("Search Console credentials must come from an environment variable in production")
    if '("google_search_console_property", "google_service_account_json")' in admin_text:
        fail("The Google service-account private key must not be editable in the admin")

    models_text = read("core/models.py")
    serializer_text = read("core/api/serializers/site.py")
    layout_text = read("frontend/app/layout.tsx")
    verification_route = read("frontend/app/api/site-verification/google/[token]/route.ts")
    next_config = read("frontend/next.config.ts")
    for marker in ("html_tag", "html_file", "dns_txt", "dns_cname", "google_analytics", "google_tag_manager"):
        if marker not in models_text:
            fail(f"Search Console verification method is missing: {marker}")
    for marker in ('self.name = "google-site-verification"', 're.fullmatch(r"google[A-Za-z0-9_-]{6,180}\\.html"'):
        if marker not in models_text:
            fail(f"Search Console verification input validation is incomplete: {marker}")
    if models_text.count("validators=[validate_image_source]") < 11:
        fail("Local /static and Cloudinary/HTTPS image-source validation is incomplete")
    for marker in ("meta_tags", "html_files", "dns_records", "google_analytics_id", "google_tag_manager_id"):
        if marker not in serializer_text:
            fail(f"Search Console public verification payload is missing: {marker}")
    for marker in ("verificationTags", "GoogleAnalytics", "GoogleTagManager", "ns.html"):
        if marker not in layout_text:
            fail(f"Search Console/Google tag rendering is incomplete: {marker}")
    if "google:token" not in next_config or "site-verification/google" not in next_config:
        fail("Google HTML-file verification rewrite is missing from Next config")
    if "X-Robots-Tag" not in verification_route or "html_files" not in verification_route:
        fail("Google HTML-file verification route is incomplete")

    automation = read("core/management/commands/run_seo_automation.py")
    if 'should_apply_ai = bool(options["apply_ai"])' not in automation:
        fail("AI SEO application must require the explicit --apply-ai flag")
    if "publish_now=False" not in automation:
        fail("AI SEO automation must keep newly generated posts as drafts")

    render_text = read("render.yaml")
    procfile = read("Procfile")
    build_script = read("build.sh")
    start_script = read("start.sh")
    render_build = f"{render_text}\n{build_script}"
    render_start = f"{render_text}\n{start_script}"
    migration_marker = "python manage.py migrate --noinput"
    bootstrap_marker = "python manage.py bootstrap_nakheel_najd"
    gunicorn_marker = "gunicorn project.wsgi:application --bind 0.0.0.0:$PORT"
    for filename, content in (("Render start configuration", render_start), ("Procfile", procfile)):
        if migration_marker not in content or bootstrap_marker not in content:
            fail(f"{filename} must keep migrations and an explicit Nakheel Najd bootstrap path")
        if "DJANGO_BOOTSTRAP_ON_START" not in content:
            fail(f"{filename} must gate the heavy bootstrap behind DJANGO_BOOTSTRAP_ON_START")
        if "(python manage.py bootstrap_nakheel_najd &)" in content:
            fail(f"{filename} must not launch the mutating bootstrap in the background")
        has_render_gunicorn = (
            "gunicorn project.wsgi:application" in content
            and "--bind" in content
            and "PORT" in content
        )
        if gunicorn_marker not in content and not has_render_gunicorn:
            fail(f"{filename} must start Gunicorn and bind to the Render port")
    if 'DJANGO_SUPERUSER_USERNAME\n        value:' in render_text:
        fail("Render blueprint must not publish a fixed administrator username")
    for filename, content in (("Render start configuration", render_start), ("Procfile", procfile)):
        if "ensure_public_catalog" not in content:
            fail(f"{filename} must verify/sync the public catalogue during startup")
    if "makemigrations --check --dry-run" not in render_build:
        fail("Render backend build must fail on missing migrations")
    if "npm ci --include=dev && npm run typecheck && npm run build" not in render_text:
        fail("Render frontend build must include devDependencies, generate Next types, type-check, then build")
    npmrc = read("frontend/.npmrc")
    if "include=dev" not in npmrc:
        fail("Frontend .npmrc must force devDependencies during production builds")
    has_cloudinary_url = "- key: CLOUDINARY_URL" in render_text
    has_split_cloudinary = all(
        marker in render_text
        for marker in ("CLOUDINARY_CLOUD_NAME", "CLOUDINARY_API_KEY", "CLOUDINARY_API_SECRET")
    )
    if not has_cloudinary_url and not has_split_cloudinary:
        fail("Render Cloudinary credential placeholder is missing")
    cloudinary_check = ROOT / "core/management/commands/check_cloudinary_storage.py"
    if not cloudinary_check.exists():
        fail("Cloudinary storage permission diagnostic command is missing")

    url_text = read("core/urls.py")
    views_text = read("core/views.py")
    for marker in ("district_detail", "sitemap-districts.xml"):
        if marker not in url_text:
            fail(f"Missing district URL marker: {marker}")
    unicode_route_markers = (
        '<str:district_slug>',
        '<str:category_slug>',
        '<str:tag_slug>',
    )
    for marker in unicode_route_markers:
        if marker not in url_text:
            fail(f"Unicode slug route is not configured safely: {marker}")
    if '<slug:district_slug>' in url_text:
        fail("District routes must not use Django's ASCII-only slug converter")
    for marker in ("def district_detail", "def sitemap_districts_xml"):
        if marker not in views_text:
            fail(f"Missing district view marker: {marker}")

    migration_files = {path.name for path in (ROOT / "core/migrations").glob("[0-9][0-9][0-9][0-9]_*.py")}
    for expected in (
        "0018_integrity_constraints.py",
        "0019_query_indexes.py",
        "0020_lead_crm_fields.py",
        "0021_location_taxonomy_automation.py",
        "0022_seed_fixed_locations.py",
        "0023_classify_existing_content.py",
        "0024_nakheel_najd_brand.py",
        "0025_cityservicepage_district.py",
        "0026_site_identity_controls.py",
        "0027_site_verification_methods_project_coverage.py",
        "0028_search_console_property_format.py",
        "0029_site_verification_model_state.py",
        "0030_local_image_source_fields.py",
        "0031_homesection_homesectionmedia.py",
        "0032_alter_sitesettings_homepage_meta_description_and_more.py",
    ):
        if expected not in migration_files:
            fail(f"Missing migration: {expected}")

    try:
        import yaml
        for filename in ("render.yaml", ".github/workflows/ci.yml"):
            with (ROOT / filename).open("r", encoding="utf-8") as stream:
                yaml.safe_load(stream)
            stats["yaml_files"] += 1
    except ImportError:
        warn("PyYAML unavailable; YAML parsing skipped")
    except Exception as exc:
        fail(f"YAML parse failed: {exc}")


def check_brand_and_secrets() -> None:
    source_extensions = {".py", ".html", ".css", ".js", ".md", ".yaml", ".yml", ".txt", ".example"}
    allowed_placeholder_files = {".env.example", ".env.production.example", "DEPLOYMENT_AR.md"}
    old_phone_hits = []
    suspicious = []

    for path in ROOT.rglob("*"):
        if not path.is_file() or any(part in EXCLUDED_PARTS for part in path.parts):
            continue
        if path.suffix.lower() not in source_extensions and path.name not in allowed_placeholder_files:
            continue
        try:
            text = path.read_text(encoding="utf-8-sig")
        except (UnicodeError, OSError):
            continue
        rel = path.relative_to(ROOT).as_posix()
        if rel != "scripts/static_audit.py" and ("0557977733" in text or "055 797 7733" in text):
            old_phone_hits.append(rel)
        if rel not in allowed_placeholder_files and rel != "scripts/static_audit.py":
            if re.search(r"cloudinary://(?!API_KEY:API_SECRET@CLOUD_NAME|api_key:api_secret@cloud_name)[^\s'\"`]+", text, flags=re.IGNORECASE):
                suspicious.append(f"Cloudinary credential-like URL in {rel}")
            if re.search(r"(?i)(tokenmix_api_key|openai_api_key)\s*[=:]\s*['\"]?(?!\s*$|ضع|replace|change)[A-Za-z0-9_-]{20,}", text):
                suspicious.append(f"API key-like value in {rel}")

    if old_phone_hits:
        fail("Old phone number remains in: " + ", ".join(sorted(set(old_phone_hits))))
    if suspicious:
        fail("; ".join(sorted(set(suspicious))))

    data_text = read("core/data.py")
    if 'SITE_NAME = "نخيل نجد"' not in data_text or 'PHONE_NUMBER = "0554882724"' not in data_text:
        fail("Brand or phone constants are incorrect in core/data.py")


def check_release_hygiene() -> None:
    forbidden = []
    forbidden_names = {".env", "db.sqlite3"}
    ignored_directory_names = {
        ".git", ".next", ".venv", ".venv-test", "__pycache__",
        "media", "node_modules", "staticfiles_build",
    }
    stale_docs = {"CHANGES_READY_AR.md", "QA_REPORT_AR.md", "QA_V2_REPORT_AR.md", "UPGRADE_V2_AR.md"}

    # Git checkouts on Render always contain a .git directory. Those files are
    # deployment metadata, not release artifacts, so skip ignored directories
    # entirely instead of treating every path inside them as a failure.
    for path in ROOT.rglob("*"):
        if any(part in ignored_directory_names for part in path.relative_to(ROOT).parts):
            continue
        if path.is_file() and path.name == "db.sqlite3" and not is_git_tracked(path):
            warn("Preserved local db.sqlite3 is ignored by Git and excluded from the deployed release")
            continue
        if path.is_file() and (path.suffix == ".pyc" or path.name in forbidden_names):
            forbidden.append(path)

    font_dir = ROOT / "static" / "fonts" / "thmanyah"
    installed_fonts = {path.name for path in font_dir.glob("*.woff2")}
    expected_fonts = {
        "thmanyahsans-Light.woff2",
        "thmanyahsans-Regular.woff2",
        "thmanyahsans-Medium.woff2",
        "thmanyahsans-Bold.woff2",
        "thmanyahsans-Black.woff2",
        "thmanyahserifdisplay-Regular.woff2",
        "thmanyahserifdisplay-Bold.woff2",
        "thmanyahserifdisplay-Black.woff2",
        "thmanyahseriftext-Regular.woff2",
        "thmanyahseriftext-Bold.woff2",
    }
    if installed_fonts:
        missing = expected_fonts - installed_fonts
        unexpected = installed_fonts - expected_fonts
        if missing or unexpected:
            fail(
                "Incomplete Thmanyah font install: "
                f"missing={sorted(missing)}, unexpected={sorted(unexpected)}"
            )
        else:
            stats["thmanyah_fonts"] = len(installed_fonts)
    else:
        warn("Thmanyah font binaries are not installed yet; run scripts/install_thmanyah_fonts.py before deployment")

    if forbidden:
        sample = ", ".join(str(path.relative_to(ROOT)) for path in forbidden[:10])
        suffix = "" if len(forbidden) <= 10 else f" (+{len(forbidden) - 10} more)"
        fail(f"Development or secret artifacts exist before packaging: {sample}{suffix}")
    for name in stale_docs:
        if (ROOT / name).exists():
            fail(f"Stale release document must be removed: {name}")


for check in (
    check_python,
    check_templates,
    check_css,
    check_frontend_contract,
    check_images,
    check_content_catalog,
    check_api_view_exports,
    check_internal_references,
    check_migration_graph,
    check_configuration,
    check_brand_and_secrets,
    check_release_hygiene,
):
    check()

print("Offline audit summary")
for key in sorted(stats):
    print(f"- {key}: {stats[key]}")
for message in warnings:
    print(f"WARNING: {message}")
if errors:
    for message in errors:
        print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)
print("Offline audit passed.")
