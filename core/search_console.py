import json
import os
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from .models import SearchConsoleQuery, SiteSettings


def fetch_search_console_queries(days=28, row_limit=250):
    settings_obj = SiteSettings.load()
    property_url = (os.environ.get("GOOGLE_SEARCH_CONSOLE_PROPERTY") or settings_obj.google_search_console_property or "").strip()
    credentials_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    # Service-account JSON is a private key. Production must load it from the
    # environment instead of persisting it in the application database/admin.
    if not credentials_json and settings.DEBUG:
        credentials_json = (settings_obj.google_service_account_json or "").strip()
    if not property_url or not credentials_json:
        return {"fetched": 0, "saved": 0, "skipped": "missing_settings"}

    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
    except Exception as exc:
        return {"fetched": 0, "saved": 0, "skipped": f"missing_google_client: {exc}"}

    info = json.loads(credentials_json)
    credentials = service_account.Credentials.from_service_account_info(
        info,
        scopes=["https://www.googleapis.com/auth/webmasters.readonly"],
    )
    service = build("searchconsole", "v1", credentials=credentials)
    end_date = timezone.now().date() - timedelta(days=2)
    start_date = end_date - timedelta(days=days)
    body = {
        "startDate": start_date.isoformat(),
        "endDate": end_date.isoformat(),
        "dimensions": ["query", "page", "country", "device"],
        "rowLimit": row_limit,
    }
    result = service.searchanalytics().query(
        siteUrl=property_url,
        body=body,
    ).execute()

    saved = 0
    for row in result.get("rows", []):
        keys = row.get("keys", [])
        query = keys[0] if len(keys) > 0 else ""
        page = keys[1] if len(keys) > 1 else ""
        country = keys[2] if len(keys) > 2 else ""
        device = keys[3] if len(keys) > 3 else ""
        SearchConsoleQuery.objects.update_or_create(
            query=query,
            page=page,
            country=country,
            device=device,
            date_from=start_date,
            date_to=end_date,
            defaults={
                "clicks": int(row.get("clicks", 0)),
                "impressions": int(row.get("impressions", 0)),
                "ctr": float(row.get("ctr", 0)),
                "position": float(row.get("position", 0)),
            },
        )
        saved += 1
    return {"fetched": len(result.get("rows", [])), "saved": saved, "skipped": ""}
