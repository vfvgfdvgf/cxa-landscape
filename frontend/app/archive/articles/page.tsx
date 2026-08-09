import type { Metadata } from "next";

import { ArticleCard } from "@/components/content/Cards";
import { Breadcrumbs } from "@/components/ui/Breadcrumbs";
import { Container } from "@/components/ui/Container";
import { PageHero } from "@/components/ui/PageHero";
import { EmptyState, Pagination } from "@/components/ui/States";
import { djangoApi, withQuery } from "@/lib/django-api";
import { staticMetadata } from "@/lib/metadata";
import { pageNumber } from "@/lib/page-data";
import type { Article, PaginatedResponse } from "@/types";

export const metadata: Metadata = staticMetadata("أرشيف المقالات", "جميع المقالات المنشورة في الموقع.", "/archive/articles/");
export default async function ArchiveArticles({ searchParams }: { searchParams: Promise<{ page?: string }> }) { const q = await searchParams; const current = pageNumber(q.page); const data = await djangoApi<PaginatedResponse<Article>>(withQuery("archive/articles/", { page: current }), { revalidate: 300 }); return <><PageHero eyebrow="الأرشيف" title="أرشيف المقالات"><Breadcrumbs items={[{ label: "الأرشيف", href: "/archive/" }, { label: "المقالات" }]} /></PageHero><section className="content-section"><Container><div className="grid grid--3">{data.results.length ? data.results.map((item) => <ArticleCard key={item.id} article={item} />) : <EmptyState />}</div><Pagination current={current} count={data.count} pageSize={12} href="/archive/articles/" /></Container></section></>; }
