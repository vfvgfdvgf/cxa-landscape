import type { Metadata } from "next";
import Link from "next/link";

import { CostCalculator } from "@/components/forms/CostCalculator";
import { Breadcrumbs } from "@/components/ui/Breadcrumbs";
import { Container } from "@/components/ui/Container";
import { PageHero } from "@/components/ui/PageHero";
import { detailApi } from "@/lib/page-data";
import { staticMetadata } from "@/lib/metadata";
import type { ToolContent } from "@/types";

export const dynamic = "force-dynamic";

export const metadata: Metadata = staticMetadata("حاسبة تكلفة اللاندسكيب والنخيل", "تقدير أولي لتكاليف خدمات اللاندسكيب والنخيل والري والشبوك.", "/cost-calculator/");
export default async function CalculatorIndexPage() { const tools = await detailApi<ToolContent>("tools/", 3600, ["tools"]); const selected = tools.calculators.find((item) => item.slug === "landscape") || tools.calculators[0]; return <><PageHero eyebrow="أداة تقديرية" title="ابدأ بنطاق تكلفة واضح" description="اختر نوع الخدمة وأدخل الكمية للحصول على نطاق أولي قبل المعاينة."><Breadcrumbs items={[{ label: "حاسبة التكلفة" }]} /></PageHero><section className="content-section"><Container>{selected ? <CostCalculator calculator={selected} /> : null}<div className="tool-list">{tools.calculators.map((item) => <Link key={item.slug} href={`/cost-calculator/${item.slug}/`}>{item.title}<span>←</span></Link>)}</div></Container></section></>; }
