import type { ImageData } from "@/types";

/**
 * Local static portfolio images are mirrored into the Next.js public directory
 * during build. Serving them from the frontend removes a second-origin TLS hop
 * to Django/Render and lets the CDN cache them for a year.
 */
export function fastImageUrl(url: string): string {
  if (!url) return url;
  try {
    const parsed = new URL(url, "https://getsiaq.online");
    const match = parsed.pathname.match(/^\/static\/([^/]+)$/);
    if (match) return `/media/${encodeURIComponent(decodeURIComponent(match[1]))}`;
  } catch {
    // Keep the original URL when parsing fails.
  }
  return url;
}

export function imageSourceSet(image: ImageData, format: "webp" | "avif" = "webp"): string | undefined {
  const variants = image.variants || [];
  const values = variants.flatMap((variant) => {
    const url = format === "avif" ? variant.avif_url : variant.url;
    return url ? [`${fastImageUrl(url)} ${variant.width}w`] : [];
  });
  return values.length ? values.join(", ") : undefined;
}


export function preferredImageUrl(
  image: ImageData,
  targetWidth = 768,
  format: "webp" | "avif" = "webp",
): string {
  const variants = [...(image.variants || [])].sort((a, b) => a.width - b.width);
  const selected = variants.find((variant) => variant.width >= targetWidth) || variants.at(-1);
  if (selected) {
    const candidate = format === "avif" ? selected.avif_url || selected.url : selected.url;
    if (candidate) return fastImageUrl(candidate);
  }
  return fastImageUrl(image.url);
}
