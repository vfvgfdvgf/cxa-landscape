import type { Metadata } from "next";

import { LocalServicePage } from "@/components/content/LocalServicePage";
import { buildMetadata } from "@/lib/metadata";
import { detailApi } from "@/lib/page-data";
import type { CityService } from "@/types";

async function getLocal(city: string, service: string) { return detailApi<CityService>(`cities/${encodeURIComponent(city)}/services/${encodeURIComponent(service)}/`, 600, ["cities", "services", `local-${city}-${service}`]); }
export async function generateMetadata({ params }: { params: Promise<{ citySlug: string; serviceSlug: string }> }): Promise<Metadata> { const { citySlug, serviceSlug } = await params; return buildMetadata((await getLocal(citySlug, serviceSlug)).seo); }
export default async function CityServicePage({ params }: { params: Promise<{ citySlug: string; serviceSlug: string }> }) { const { citySlug, serviceSlug } = await params; return <LocalServicePage page={await getLocal(citySlug, serviceSlug)} />; }
