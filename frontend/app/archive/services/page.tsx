import type { Metadata } from "next";

import { ServiceCard } from "@/components/content/Cards";
import { Breadcrumbs } from "@/components/ui/Breadcrumbs";
import { Container } from "@/components/ui/Container";
import { PageHero } from "@/components/ui/PageHero";
import { EmptyState, Pagination } from "@/components/ui/States";
import { djangoApi, withQuery } from "@/lib/django-api";
import { staticMetadata } from "@/lib/metadata";
import { pageNumber } from "@/lib/page-data";
import type { PaginatedResponse, Service } from "@/types";

export const metadata: Metadata = staticMetadata("أرشيف الخدمات", "جميع الخدمات المنشورة في الموقع.", "/archive/services/");
export default async function ArchiveServices({ searchParams }: { searchParams: Promise<{ page?: string }> }) { const q = await searchParams; const current = pageNumber(q.page); const data = await djangoApi<PaginatedResponse<Service>>(withQuery("archive/services/", { page: current }), { revalidate: 900 }); return <><PageHero eyebrow="الأرشيف" title="أرشيف الخدمات"><Breadcrumbs items={[{ label: "الأرشيف", href: "/archive/" }, { label: "الخدمات" }]} /></PageHero><section className="content-section"><Container><div className="grid grid--3">{data.results.length ? data.results.map((item) => <ServiceCard key={item.id} service={item} />) : <EmptyState />}</div><Pagination current={current} count={data.count} pageSize={12} href="/archive/services/" /></Container></section></>; }
