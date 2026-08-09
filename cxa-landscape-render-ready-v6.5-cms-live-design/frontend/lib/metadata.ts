import type { Metadata } from "next";

import type { SeoData } from "@/types";

export const SITE_URL = (process.env.NEXT_PUBLIC_SITE_URL || "https://getsiaq.online").replace(/\/$/, "");
const DJANGO_ORIGIN = new URL(process.env.DJANGO_API_URL || "https://nakheel-najd.onrender.com").origin;
const DEFAULT_SOCIAL_IMAGE = process.env.NEXT_PUBLIC_SOCIAL_IMAGE || `${DJANGO_ORIGIN}/static/hero-desktop.webp`;

export function absoluteUrl(path = "/"): string {
  const normalized = path.startsWith("/") ? path : `/${path}`;
  return `${SITE_URL}${normalized === "/" ? "" : normalized}`;
}

export function buildMetadata(seo?: SeoData | null): Metadata {
  const sourceTitle = seo?.title || "نخيل نجد";
  const title = sourceTitle.includes("نخيل نجد") ? sourceTitle : `${sourceTitle} | نخيل نجد`;
  const description = seo?.description || "خدمات النخيل واللاندسكيب والري والشبوك في السعودية.";
  const canonicalPath = seo?.canonical_path || "/";
  const canonical = absoluteUrl(canonicalPath);
  const image = seo?.image || DEFAULT_SOCIAL_IMAGE;
  const robotsValue = (seo?.robots || "index, follow, max-image-preview:large").toLowerCase();
  const index = !robotsValue.includes("noindex");
  const follow = !robotsValue.includes("nofollow");
  return {
    title,
    description,
    keywords: seo?.keywords ? seo.keywords.split(",").map((item) => item.trim()) : undefined,
    alternates: { canonical, languages: { "ar-SA": canonical, "x-default": canonical } },
    robots: { index, follow, googleBot: { index, follow, "max-image-preview": "large" } },
    openGraph: {
      type: seo?.og_type === "article" ? "article" : "website",
      locale: "ar_SA",
      url: canonical,
      siteName: "نخيل نجد",
      title,
      description,
      images: [{ url: image, alt: title }],
      ...(seo?.og_type === "article"
        ? { publishedTime: seo.published_time || undefined, modifiedTime: seo.modified_time || undefined }
        : {}),
    },
    twitter: { card: "summary_large_image", title, description, images: [image] },
  };
}

export function staticMetadata(title: string, description: string, path: string): Metadata {
  return buildMetadata({
    title,
    description,
    keywords: "",
    robots: "index, follow",
    canonical_path: path,
    image: "",
    og_type: "website",
    published_time: "",
    modified_time: "",
    schema: {},
  });
}
