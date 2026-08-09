import type { Metadata } from "next";

import { RichText } from "@/components/content/RichText";
import { SeoJsonLd } from "@/components/seo/JsonLd";
import { Breadcrumbs } from "@/components/ui/Breadcrumbs";
import { Container } from "@/components/ui/Container";
import { PageHero } from "@/components/ui/PageHero";
import { buildMetadata } from "@/lib/metadata";
import { detailApi } from "@/lib/page-data";
import type { ManagedPage } from "@/types";

async function getPage(slug: string) { return detailApi<ManagedPage>(`pages/${encodeURIComponent(slug)}/`, 300, ["pages", `page-${slug}`]); }
export async function generateMetadata({ params }: { params: Promise<{ pageSlug: string }> }): Promise<Metadata> { const { pageSlug } = await params; return buildMetadata((await getPage(pageSlug)).seo); }
export default async function ManagedPageView({ params }: { params: Promise<{ pageSlug: string }> }) { const { pageSlug } = await params; const page = await getPage(pageSlug); return <><PageHero eyebrow={page.menu_title || "صفحة"} title={page.hero_title || page.title} description={page.intro_text}><Breadcrumbs items={[{ label: page.title }]} /></PageHero><section className="content-section"><Container><RichText html={page.body} /></Container></section><SeoJsonLd schema={page.seo.schema} /></>; }
