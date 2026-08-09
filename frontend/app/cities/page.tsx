import type { Metadata } from "next";

import { CityCard } from "@/components/content/Cards";
import { CallToAction } from "@/components/content/CallToAction";
import { RichText } from "@/components/content/RichText";
import { SeoJsonLd } from "@/components/seo/JsonLd";
import { Container } from "@/components/ui/Container";
import { PageHero } from "@/components/ui/PageHero";
import { EmptyState, Pagination } from "@/components/ui/States";
import { djangoApi, withQuery } from "@/lib/django-api";
import { buildMetadata, staticMetadata } from "@/lib/metadata";
import { getManagedPage, pageNumber } from "@/lib/page-data";
import type { City, PaginatedResponse } from "@/types";

export async function generateMetadata(): Promise<Metadata> { const page = await getManagedPage("cities"); return page ? buildMetadata({ ...page.seo, canonical_path: "/cities/" }) : staticMetadata("مدن التغطية", "استعرض مدن وأحياء التغطية والخدمات المحلية المنشورة.", "/cities/"); }
export default async function CitiesPage({ searchParams }: { searchParams: Promise<{ page?: string }> }) { const query = await searchParams; const current = pageNumber(query.page); const [page, data] = await Promise.all([getManagedPage("cities"), djangoApi<PaginatedResponse<City>>(withQuery("cities/", { page: current }), { revalidate: 900, tags: ["cities"] })]); return <><PageHero eyebrow="نطاق الخدمة" title={page?.hero_title || page?.title || "من المدينة إلى الحي، محتوى محلي واضح"} description={page?.intro_text || "تصفح الخدمات والمشاريع والمقالات المرتبطة بكل مدينة."} /><section className="content-section"><Container>{page?.body ? <RichText html={page.body} className="listing-intro" /> : null}<div className="grid grid--3">{data.results.length ? data.results.map((city) => <CityCard key={city.id} city={city} />) : <EmptyState />}</div><Pagination current={current} count={data.count} pageSize={12} href="/cities/" /></Container></section><CallToAction /><SeoJsonLd schema={page?.seo.schema} /></>; }
