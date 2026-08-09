import { NextResponse } from "next/server";

import { optionalApi } from "@/lib/django-api";
import type { SiteSettings } from "@/types";

export async function GET(_request: Request, { params }: { params: Promise<{ token: string }> }) {
  const { token } = await params;
  if (!/^[A-Za-z0-9_-]{6,180}$/.test(token)) {
    return new NextResponse("Not found", { status: 404 });
  }
  const site = await optionalApi<SiteSettings>("site/", { revalidate: 60, tags: ["site", "verification"] });
  const filename = `google${token}.html`;
  const file = site?.verification?.html_files.find((item) => item.name === filename);
  if (!file) return new NextResponse("Not found", { status: 404 });
  return new NextResponse(file.content, {
    status: 200,
    headers: {
      "Content-Type": "text/html; charset=utf-8",
      "Cache-Control": "public, max-age=300, s-maxage=300",
      "X-Robots-Tag": "noindex, nofollow",
    },
  });
}
