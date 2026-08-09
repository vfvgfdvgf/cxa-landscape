import type { MetadataRoute } from "next";

import { optionalApi } from "@/lib/django-api";
import { absoluteUrl } from "@/lib/metadata";
import type { PublicUrlItem } from "@/types";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const items = await optionalApi<PublicUrlItem[]>("public-urls/", { revalidate: 900, tags: ["sitemap"] });
  const fallback: PublicUrlItem[] = [
    { url: "/", priority: 1, change_frequency: "weekly" },
    { url: "/services/", priority: .9, change_frequency: "weekly" },
    { url: "/projects/", priority: .8, change_frequency: "weekly" },
    { url: "/cities/", priority: .9, change_frequency: "weekly" },
    { url: "/districts/", priority: .9, change_frequency: "weekly" },
    { url: "/blog/", priority: .8, change_frequency: "daily" },
    { url: "/about/", priority: .6, change_frequency: "monthly" },
    { url: "/contact/", priority: .6, change_frequency: "monthly" },
    { url: "/privacy/", priority: .3, change_frequency: "yearly" },
    { url: "/terms/", priority: .3, change_frequency: "yearly" },
    { url: "/cost-calculator/", priority: .6, change_frequency: "monthly" },
    { url: "/archive/", priority: .4, change_frequency: "weekly" },
    { url: "/archive/services/", priority: .4, change_frequency: "weekly" },
    { url: "/archive/cities/", priority: .4, change_frequency: "weekly" },
    { url: "/archive/articles/", priority: .4, change_frequency: "daily" },
  ];
  return (items?.length ? items : fallback).map((item) => ({
    url: absoluteUrl(item.url),
    lastModified: item.updated_at ? new Date(item.updated_at) : undefined,
    changeFrequency: item.change_frequency,
    priority: item.priority,
  }));
}
