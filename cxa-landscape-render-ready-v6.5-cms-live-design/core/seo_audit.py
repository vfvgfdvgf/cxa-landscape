import re

from django.test import Client
from django.urls import reverse

from .models import BlogPost, City, CityServicePage, SEOReportIssue


def _add_issue(issues, page_url, title, issue_type, severity, details, suggested_fix=""):
    issues.append({
        "page_url": page_url,
        "title": title,
        "issue_type": issue_type,
        "severity": severity,
        "details": details,
        "suggested_fix": suggested_fix,
    })


def _audit_html(path, html):
    issues = []
    title = ""
    if "<title>" in html and "</title>" in html:
        title = html.split("<title>", 1)[1].split("</title>", 1)[0].strip()
    description_match = re.search(r'<meta\s+name=["\']description["\']\s+content=["\']([^"\']+)["\']', html)
    description_ok = bool(description_match and description_match.group(1).strip())
    canonical_ok = 'rel="canonical"' in html
    h1_count = html.count("<h1")
    jsonld_count = html.count("application/ld+json")
    missing_alt = html.count("<img") - html.count(" alt=")

    if not title:
        _add_issue(issues, path, "عنوان الصفحة مفقود", "missing_title", "high", "وسم title غير موجود أو فارغ.", "أضف meta_title واضح لكل صفحة.")
    elif len(title) > 65:
        _add_issue(issues, path, "عنوان طويل", "long_title", "medium", f"طول العنوان {len(title)} حرف.", "اختصر العنوان إلى 50-60 حرفًا تقريبًا.")
    if not description_ok:
        _add_issue(issues, path, "وصف SEO مفقود", "missing_description", "high", "وسم meta description غير موجود أو فارغ.")
    if not canonical_ok:
        _add_issue(issues, path, "Canonical مفقود", "missing_canonical", "high", "لا يوجد رابط canonical.")
    if h1_count != 1:
        _add_issue(issues, path, "عدد H1 غير مناسب", "h1_count", "medium", f"عدد H1 الحالي: {h1_count}.")
    if jsonld_count == 0:
        _add_issue(issues, path, "Structured data مفقود", "missing_schema", "medium", "لا يوجد JSON-LD في الصفحة.")
    if missing_alt > 0:
        _add_issue(issues, path, "صور بدون alt", "missing_alt", "medium", f"عدد الصور بدون alt: {missing_alt}.")
    if any(marker in html for marker in ("ط§", "ط®", "ï¿½", "Ã", "Â")):
        _add_issue(issues, path, "نص عربي مشوه", "mojibake", "high", "ظهرت علامات ترميز مشوه داخل HTML.")
    return issues


def collect_public_paths():
    paths = ["/", reverse("services"), reverse("cities"), reverse("blog"), reverse("contact")]
    paths += [reverse("city_detail", kwargs={"city_slug": city.slug}) for city in City.objects.filter(is_active=True, is_system=True)[:30]]
    paths += [
        reverse("city_service_detail", kwargs={"city_slug": item.city.slug, "service_slug": item.custom_slug or item.service.slug})
        for item in CityServicePage.objects.filter(is_active=True).select_related("city", "service")[:80]
    ]
    paths += [reverse("blog_detail", kwargs={"post_slug": post.slug}) for post in BlogPost.objects.filter(status="published")[:50]]
    return list(dict.fromkeys(paths))


def run_seo_audit(host="127.0.0.1:8000"):
    client = Client(HTTP_HOST=host)
    found = []
    for path in collect_public_paths():
        response = client.get(path, follow=True, secure=True)
        if response.status_code >= 400:
            _add_issue(found, path, "صفحة لا تعمل", "bad_status", "high", f"HTTP {response.status_code}")
            continue
        content_type = response.get("Content-Type", "")
        if "text/html" in content_type:
            html = response.content.decode("utf-8", errors="replace")
            found.extend(_audit_html(path, html))

    SEOReportIssue.objects.exclude(status="ignored").update(status="fixed")
    for item in found:
        obj, _ = SEOReportIssue.objects.update_or_create(
            page_url=item["page_url"],
            issue_type=item["issue_type"],
            defaults={**item, "status": "open"},
        )
    return found
