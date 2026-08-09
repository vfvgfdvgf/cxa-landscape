from rest_framework import serializers

from core.api.utils import clean_text, image_payload
from core.html_utils import sanitize_html


class TextField(serializers.CharField):
    def to_representation(self, value):
        return clean_text(super().to_representation(value))


class HTMLField(serializers.CharField):
    """Repair legacy Arabic text and sanitize stored rich HTML at the API boundary."""

    def to_representation(self, value):
        raw_value = serializers.CharField.to_representation(self, value)
        return sanitize_html(clean_text(raw_value))


class RelatedSummarySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = TextField()
    slug = serializers.CharField()


def related_payload(instance, name_field="name"):
    if not instance:
        return None
    return {
        "id": instance.pk,
        "name": clean_text(getattr(instance, name_field, "")),
        "slug": instance.slug,
    }


def serializer_image(serializer, value, alt):
    return image_payload(serializer.context.get("request"), value, alt)
