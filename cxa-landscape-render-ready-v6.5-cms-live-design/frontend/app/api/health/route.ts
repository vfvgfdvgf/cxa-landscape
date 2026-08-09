import { NextResponse } from "next/server";

import { djangoApi } from "@/lib/django-api";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const backend = await djangoApi<{ ok: boolean; database: string }>("ready/", { revalidate: 0 });
    return NextResponse.json({ ok: backend.ok, service: "getsiaq-frontend", backend: backend.database });
  } catch {
    return NextResponse.json(
      { ok: false, service: "getsiaq-frontend", backend: "unavailable" },
      { status: 503 },
    );
  }
}
