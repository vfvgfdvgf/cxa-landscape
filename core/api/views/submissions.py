from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.permissions import HasFrontendSecret
from core.api.serializers import LeadSubmissionSerializer
from core.api.throttles import SubmissionRateThrottle


class BaseSubmissionView(APIView):
    permission_classes = [HasFrontendSecret]
    throttle_classes = [SubmissionRateThrottle]
    submission_kind = "lead"

    def post(self, request):
        serializer = LeadSubmissionSerializer(
            data=request.data,
            context={"request": request, "submission_kind": self.submission_kind},
        )
        serializer.is_valid(raise_exception=True)
        lead = serializer.save()
        return Response(
            {"ok": True, "reference": lead.pk, "message": "تم استلام طلبك وسنتواصل معك قريبًا."},
            status=status.HTTP_201_CREATED,
        )


class ContactSubmissionView(BaseSubmissionView):
    submission_kind = "contact"


class QuoteSubmissionView(BaseSubmissionView):
    submission_kind = "quote"


class LeadSubmissionView(BaseSubmissionView):
    submission_kind = "lead"
