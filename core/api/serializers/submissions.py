import re

from rest_framework import serializers

from core.models import Lead


PHONE_PATTERN = re.compile(r"^\+?[0-9\s()\-]{8,20}$")
BUDGET_CHOICES = (
    "أقل من 25,000 ريال",
    "25,000 - 50,000 ريال",
    "50,000 - 80,000 ريال",
    "80,000 - 150,000 ريال",
    "أكثر من 150,000 ريال",
    "أحتاج مساعدة في التقدير",
)
CONTACT_TIME_CHOICES = (
    "صباحًا (8 - 12)",
    "ظهرًا (12 - 4)",
    "مساءً (4 - 8)",
    "أي وقت",
)


class ArabicCharField(serializers.CharField):
    default_error_messages = {
        "invalid": "أدخل نصًا صالحًا.",
        "blank": "هذا الحقل مطلوب.",
        "required": "هذا الحقل مطلوب.",
        "max_length": "القيمة أطول من الحد المسموح.",
        "min_length": "القيمة أقصر من الحد المطلوب.",
    }


class ArabicChoiceField(serializers.ChoiceField):
    default_error_messages = {
        "invalid_choice": "اختر قيمة من الخيارات المتاحة.",
    }


class LeadSubmissionSerializer(serializers.Serializer):
    name = ArabicCharField(min_length=2, max_length=120, trim_whitespace=True)
    phone = ArabicCharField(min_length=8, max_length=20, trim_whitespace=True)
    email = serializers.EmailField(
        required=False,
        allow_blank=True,
        max_length=254,
        error_messages={"invalid": "أدخل بريدًا إلكترونيًا صحيحًا.", "max_length": "البريد الإلكتروني أطول من الحد المسموح."},
    )
    city = ArabicCharField(required=False, allow_blank=True, max_length=120, trim_whitespace=True)
    district = ArabicCharField(required=False, allow_blank=True, max_length=140, trim_whitespace=True)
    service = ArabicCharField(required=False, allow_blank=True, max_length=180, trim_whitespace=True)
    project_area = ArabicCharField(required=False, allow_blank=True, max_length=80, trim_whitespace=True)
    budget = ArabicChoiceField(required=False, allow_blank=True, choices=BUDGET_CHOICES)
    preferred_contact_time = ArabicChoiceField(required=False, allow_blank=True, choices=CONTACT_TIME_CHOICES)
    message = ArabicCharField(min_length=5, max_length=3000, trim_whitespace=True)
    privacy_consent = serializers.BooleanField(
        error_messages={"required": "يلزم قبول سياسة الخصوصية.", "invalid": "قيمة الموافقة غير صالحة."}
    )
    company = ArabicCharField(required=False, allow_blank=True, max_length=200, write_only=True)
    page_url = serializers.URLField(
        required=False,
        allow_blank=True,
        max_length=500,
        error_messages={"invalid": "رابط الصفحة غير صالح.", "max_length": "رابط الصفحة أطول من الحد المسموح."},
    )
    utm_source = ArabicCharField(required=False, allow_blank=True, max_length=120)
    utm_medium = ArabicCharField(required=False, allow_blank=True, max_length=120)
    utm_campaign = ArabicCharField(required=False, allow_blank=True, max_length=160)

    def validate_phone(self, value):
        if not PHONE_PATTERN.fullmatch(value):
            raise serializers.ValidationError("أدخل رقم هاتف صحيحًا.")
        return value

    def validate_privacy_consent(self, value):
        if not value:
            raise serializers.ValidationError("يلزم قبول سياسة الخصوصية لإرسال الطلب.")
        return value

    def validate_company(self, value):
        if value:
            raise serializers.ValidationError("تعذر قبول الطلب.")
        return value

    def create(self, validated_data):
        submission_kind = self.context.get("submission_kind", "lead")
        email = validated_data.pop("email", "")
        service = validated_data.pop("service", "")
        project_area = validated_data.pop("project_area", "")
        budget = validated_data.pop("budget", "")
        preferred_contact_time = validated_data.pop("preferred_contact_time", "")
        validated_data.pop("privacy_consent", None)
        validated_data.pop("company", None)
        notes = [f"نوع الطلب: {submission_kind}"]
        if email:
            notes.append(f"البريد: {email}")
        if service:
            notes.append(f"الخدمة: {service}")
        if project_area:
            notes.append(f"مساحة المشروع: {project_area}")
        if budget:
            notes.append(f"الميزانية التقريبية: {budget}")
        if preferred_contact_time:
            notes.append(f"الوقت المفضل للتواصل: {preferred_contact_time}")
        return Lead.objects.create(
            name=validated_data["name"],
            phone=validated_data["phone"],
            city_name=validated_data.get("city", ""),
            district_name=validated_data.get("district", ""),
            message=validated_data["message"],
            source="website",
            page_url=validated_data.get("page_url", ""),
            utm_source=validated_data.get("utm_source", ""),
            utm_medium=validated_data.get("utm_medium", ""),
            utm_campaign=validated_data.get("utm_campaign", ""),
            notes="\n".join(notes),
        )
