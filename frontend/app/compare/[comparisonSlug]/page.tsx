import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { CallToAction } from "@/components/content/CallToAction";
import { Breadcrumbs } from "@/components/ui/Breadcrumbs";
import { Container } from "@/components/ui/Container";
import { PageHero } from "@/components/ui/PageHero";
import { detailApi } from "@/lib/page-data";
import { staticMetadata } from "@/lib/metadata";
import type { ToolContent } from "@/types";

async function getComparison(slug: string) { const tools = await detailApi<ToolContent>("tools/", 3600, ["tools"]); const comparison = tools.comparisons.find((item) => item.slug === slug); if (!comparison) notFound(); return comparison; }
export async function generateMetadata({ params }: { params: Promise<{ comparisonSlug: string }> }): Promise<Metadata> { const { comparisonSlug } = await params; const item = await getComparison(comparisonSlug); return staticMetadata(item.title, item.description, `/compare/${item.slug}/`); }
export default async function ComparisonPage({ params }: { params: Promise<{ comparisonSlug: string }> }) { const { comparisonSlug } = await params; const item = await getComparison(comparisonSlug); return <><PageHero eyebrow="مقارنة عملية" title={item.title} description={item.description}><Breadcrumbs items={[{ label: item.title }]} /></PageHero><section className="content-section"><Container><div className="comparison-grid"><article className="comparison-column"><h2>{item.left}</h2><ul>{item.left_points.map((point) => <li key={point}>{point}</li>)}</ul></article><article className="comparison-column"><h2>{item.right}</h2><ul>{item.right_points.map((point) => <li key={point}>{point}</li>)}</ul></article></div><article className="rich-text"><h2>الخلاصة</h2><p>{item.recommendation}</p></article></Container></section><CallToAction /></>; }
