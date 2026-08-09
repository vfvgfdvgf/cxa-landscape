import "server-only";

import { createHmac } from "node:crypto";
import { NextResponse } from "next/server";

import { ApiError, djangoApi } from "@/lib/django-api";
import type { SubmissionResponse } from "@/types";

const MAX_SUBMISSION_BYTES = 64 * 1024;

function submissionClientId(request: Request): string {
  const secret = process.env.DJANGO_API_SECRET || process.env.FRONTEND_API_SECRET || "submission-rate-limit";
  const forwardedChain = request.headers.get("x-forwarded-for")
    ?.split(",")
    .map((part) => part.trim())
    .filter(Boolean);
  // Prefer the reverse proxy's single-address header when present. Otherwise,
  // use the last forwarded hop instead of trusting a client-controlled first hop.
  const forwarded = forwardedChain?.at(-1);
  const address = request.headers.get("x-real-ip")?.trim() || forwarded || "unknown-ip";
  const userAgent = request.headers.get("user-agent") || "unknown-agent";
  const language = request.headers.get("accept-language") || "unknown-language";
  return createHmac("sha256", secret)
    .update(`${address}|${userAgent}|${language}`)
    .digest("hex")
    .slice(0, 40);
}

export async function proxySubmission(request: Request, endpoint: "contact/" | "quote-request/") {
  const declaredLength = Number(request.headers.get("content-length") || "0");
  if (Number.isFinite(declaredLength) && declaredLength > MAX_SUBMISSION_BYTES) {
    return NextResponse.json({ detail: "حجم الطلب أكبر من الحد المسموح." }, { status: 413 });
  }

  let payload: unknown;
  try {
    const raw = await request.text();
    if (new TextEncoder().encode(raw).byteLength > MAX_SUBMISSION_BYTES) {
      return NextResponse.json({ detail: "حجم الطلب أكبر من الحد المسموح." }, { status: 413 });
    }
    payload = JSON.parse(raw);
  } catch {
    return NextResponse.json({ detail: "بيانات الطلب غير صالحة." }, { status: 400 });
  }
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
    return NextResponse.json({ detail: "بيانات الطلب غير صالحة." }, { status: 400 });
  }
  try {
    const result = await djangoApi<SubmissionResponse>(endpoint, {
      method: "POST",
      body: payload,
      authenticated: true,
      submissionClient: submissionClientId(request),
    });
    return NextResponse.json(result, { status: 201 });
  } catch (error) {
    const status = error instanceof ApiError && error.status >= 400 && error.status < 500 ? error.status : 503;
    const detail = error instanceof ApiError && status < 500
      ? error.message
      : "تعذر إرسال الطلب مؤقتًا. حاول مرة أخرى بعد قليل.";
    return NextResponse.json({ detail }, { status });
  }
}
