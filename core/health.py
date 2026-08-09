from django.db import connections
from django.db.utils import DatabaseError


def readiness_status():
    """Return a small readiness payload without leaking connection details."""
    try:
        with connections["default"].cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except DatabaseError:
        return False, {"ok": False, "service": "cxa-api", "database": "unavailable"}
    return True, {"ok": True, "service": "cxa-api", "database": "ready"}
