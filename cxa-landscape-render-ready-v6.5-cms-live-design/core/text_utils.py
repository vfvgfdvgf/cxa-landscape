import re
from typing import Any


ARABIC_RE = re.compile(r"[\u0600-\u06FF]")
MOJIBAKE_MARKERS = ("ط", "ظ", "Ø", "Ù", "Ã")


def _score_text(value: str) -> int:
    if not value:
        return -999

    arabic_count = len(ARABIC_RE.findall(value))
    marker_count = sum(value.count(marker) for marker in MOJIBAKE_MARKERS)

    # نعطي وزن أعلى للعربي ونقلل تأثير التشويه
    return (arabic_count * 2) - (marker_count * 3)


def fix_arabic_text(value: Any) -> Any:
    if not isinstance(value, str) or not value.strip():
        return value

    candidates = [value]

    # محاولات إصلاح شائعة
    encodings = ("cp1256", "latin1")

    for source_encoding in encodings:
        try:
            repaired = value.encode(source_encoding, errors="ignore").decode("utf-8", errors="ignore")
            if repaired and repaired != value:
                candidates.append(repaired)
        except Exception:
            continue

    # محاولة إضافية (حالة معكوسة شائعة)
    try:
        repaired = value.encode("utf-8", errors="ignore").decode("latin1", errors="ignore")
        if repaired and repaired != value:
            candidates.append(repaired)
    except Exception:
        pass

    # اختيار الأفضل
    best = max(candidates, key=_score_text)

    # لا نغير النص إلا إذا كان الفرق واضح
    if _score_text(best) > _score_text(value):
        return best

    return value


def fix_payload_text(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: fix_payload_text(v) for k, v in value.items()}

    if isinstance(value, list):
        return [fix_payload_text(v) for v in value]

    if isinstance(value, tuple):
        return tuple(fix_payload_text(v) for v in value)

    return fix_arabic_text(value)