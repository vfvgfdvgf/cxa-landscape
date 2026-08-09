const DJANGO_ORIGIN = new URL(process.env.DJANGO_API_URL || "https://nakheel-najd.onrender.com").origin;

export async function GET() {
  try {
    const response = await fetch(`${DJANGO_ORIGIN}/sitemap-images.xml`, {
      next: { revalidate: 900, tags: ["image-sitemap"] },
      signal: AbortSignal.timeout(12000),
    });
    if (!response.ok) throw new Error(`Image sitemap upstream returned ${response.status}`);
    return new Response(await response.text(), {
      headers: {
        "Content-Type": "application/xml; charset=utf-8",
        "Cache-Control": "public, s-maxage=900, stale-while-revalidate=86400",
        "X-Content-Type-Options": "nosniff",
      },
    });
  } catch {
    return new Response("Image sitemap is temporarily unavailable.", {
      status: 503,
      headers: { "Content-Type": "text/plain; charset=utf-8", "Retry-After": "300" },
    });
  }
}
