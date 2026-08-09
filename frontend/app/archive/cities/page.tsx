import type { Metadata } from "next";

import { CityCard } from "@/components/content/Cards";
import { Breadcrumbs } from "@/components/ui/Breadcrumbs";
import { Container } from "@/components/ui/Container";
import { PageHero } from "@/components/ui/PageHero";
import { EmptyState, Pagination } from "@/components/ui/States";
import { djangoApi, withQuery } from "@/lib/django-api";
import { staticMetadata } from "@/lib/metadata";
import { pageNumber } from "@/lib/page-data";
import type { City, PaginatedResponse } from "@/types";

export const metadata: Metadata = staticMetadata("أرشيف المدن", "جميع مدن التغطية المنشورة.", "/archive/cities/");
export default async function ArchiveCities({ searchParams }: { searchParams: Promise<{ page?: string }> }) { const q = await searchParams; const current = pageNumber(q.page); const data = await djangoApi<PaginatedResponse<City>>(withQuery("archive/cities/", { page: current }), { revalidate: 900 }); return <><PageHero eyebrow="الأرشيف" title="أرشيف المدن"><Breadcrumbs items={[{ label: "الأرشيف", href: "/archive/" }, { label: "المدن" }]} /></PageHero><section className="content-section"><Container><div className="grid grid--3">{data.results.length ? data.results.map((item) => <CityCard key={item.id} city={item} />) : <EmptyState />}</div><Pagination current={current} count={data.count} pageSize={12} href="/archive/cities/" /></Container></section></>; }
