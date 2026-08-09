import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { CostCalculator } from "@/components/forms/CostCalculator";
import { Breadcrumbs } from "@/components/ui/Breadcrumbs";
import { Container } from "@/components/ui/Container";
import { PageHero } from "@/components/ui/PageHero";
import { detailApi } from "@/lib/page-data";
import { staticMetadata } from "@/lib/metadata";
import type { ToolContent } from "@/types";

async function getCalculator(slug: string) { const tools = await detailApi<ToolContent>("tools/", 3600, ["tools"]); const calculator = tools.calculators.find((item) => item.slug === slug); if (!calculator) notFound(); return { calculator, tools }; }
export async function generateMetadata({ params }: { params: Promise<{ calculatorSlug: string }> }): Promise<Metadata> { const { calculatorSlug } = await params; const { calculator } = await getCalculator(calculatorSlug); return staticMetadata(calculator.title, calculator.description, `/cost-calculator/${calculator.slug}/`); }
export default async function CalculatorDetailPage({ params }: { params: Promise<{ calculatorSlug: string }> }) { const { calculatorSlug } = await params; const { calculator, tools } = await getCalculator(calculatorSlug); return <><PageHero eyebrow="حاسبة تكلفة" title={calculator.title} description={calculator.description}><Breadcrumbs items={[{ label: "حاسبة التكلفة", href: "/cost-calculator/" }, { label: calculator.title }]} /></PageHero><section className="content-section"><Container><CostCalculator calculator={calculator} /><h2>ما الذي يؤثر في التقدير؟</h2><ul className="benefits">{calculator.tips.map((tip) => <li key={tip}>{tip}</li>)}</ul><div className="tool-list">{tools.calculators.filter((item) => item.slug !== calculator.slug).slice(0, 6).map((item) => <Link key={item.slug} href={`/cost-calculator/${item.slug}/`}>{item.title}<span>←</span></Link>)}</div></Container></section></>; }
