import type { Metadata } from "next";
import { cache } from "react";

import { LocalServicePage } from "@/components/content/LocalServicePage";
import { buildMetadata } from "@/lib/metadata";
import { detailApi, normalizeRouteParam } from "@/lib/page-data";
import type { CityService } from "@/types";

const getLocal = cache(async (city: string, district: string, service: string) => {
  return detailApi<CityService>(
    `cities/${encodeURIComponent(city)}/districts/${encodeURIComponent(district)}/services/${encodeURIComponent(service)}/`,
    600,
    ["cities", "services", `local-${city}-${district}-${service}`],
  );
});

function normalizeParams(params: { citySlug: string; districtSlug: string; serviceSlug: string }) {
  return {
    city: normalizeRouteParam(params.citySlug),
    district: normalizeRouteParam(params.districtSlug),
    service: normalizeRouteParam(params.serviceSlug),
  };
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ citySlug: string; districtSlug: string; serviceSlug: string }>;
}): Promise<Metadata> {
  const route = normalizeParams(await params);
  return buildMetadata((await getLocal(route.city, route.district, route.service)).seo);
}

export default async function DistrictServicePage({
  params,
}: {
  params: Promise<{ citySlug: string; districtSlug: string; serviceSlug: string }>;
}) {
  const route = normalizeParams(await params);
  return <LocalServicePage page={await getLocal(route.city, route.district, route.service)} />;
}
