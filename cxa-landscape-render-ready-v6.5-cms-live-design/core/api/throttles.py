from rest_framework.throttling import AnonRateThrottle


class SubmissionRateThrottle(AnonRateThrottle):
    scope = "submissions"

    def get_cache_key(self, request, view):
        # Submission requests are proxied by the Next.js server. Using REMOTE_ADDR
        # would group many real visitors under the same Render egress IP. The
        # frontend therefore sends an opaque, HMAC-derived visitor identifier.
        client_key = request.headers.get("X-Submission-Client", "").strip()
        if client_key and len(client_key) <= 128:
            ident = f"frontend:{client_key}"
        else:
            ident = self.get_ident(request)
        return self.cache_format % {"scope": self.scope, "ident": ident}
