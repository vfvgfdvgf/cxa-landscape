import type { Metadata } from "next";

import { ArticleCard } from "@/components/content/Cards";
import { IntentRail } from "@/components/content/IntentRail";
import { RichText } from "@/components/content/RichText";
import { SeoJsonLd } from "@/components/seo/JsonLd";
import { Breadcrumbs } from "@/components/ui/Breadcrumbs";
import { Container } from "@/components/ui/Container";
import { PageHero } from "@/components/ui/PageHero";
import { EmptyState, Pagination } from "@/components/ui/States";
import { djangoApi, withQuery } from "@/lib/django-api";
import { ARTICLE_MARKET_INTENTS } from "@/lib/market-intents";
import { buildMetadata, staticMetadata } from "@/lib/metadata";
import { getManagedPage, pageNumber } from "@/lib/page-data";
import type { Article, PaginatedResponse } from "@/types";

export async function generateMetadata(): Promise<Metadata> {
  const page = await getManagedPage("blog");
  return page ? buildMetadata({ ...page.seo, canonical_path: "/blog/" }) : staticMetadata("مقالات النخيل واللاندسكيب", "أدلة عملية عن تنسيق الحدائق والعشب والنخيل والري والأسعار والصيانة في السعودية.", "/blog/");
}

export default async function BlogPage({ searchParams }: { searchParams: Promise<{ page?: string; q?: string }> }) {
  const query = await searchParams;
  const current = pageNumber(query.page);
  const [page, data] = await Promise.all([
    getManagedPage("blog"),
    djangoApi<PaginatedResponse<Article>>(withQuery("blog/", { page: current, q: query.q }), { revalidate: 300, tags: ["articles"] }),
  ]);
  const offset = (current - 1) * 12;
  return (
    <>
      <PageHero eyebrow="دليل الخبرة" title={page?.hero_title || page?.title || "قرارات أفضل تبدأ بمعلومة واضحة"} description={page?.intro_text || "أدلة عملية تجيب عن أسئلة السعر والاختيار والتنفيذ والصيانة قبل أن تبدأ مشروعك."}>
        <Breadcrumbs items={[{ label: "المقالات" }]} />
        <div className="listing-facts" aria-label="ملخص مكتبة المقالات"><span><strong>{data.count.toLocaleString("ar-SA")}</strong> مقال ودليل</span><span><strong>عملي</strong> قبل التنفيذ</span><span><strong>سعودي</strong> في السياق</span></div>
        <form className="button-row hero-search" action="/blog/" method="get" role="search"><div className="form-field"><label className="sr-only" htmlFor="blog-search">ابحث في المقالات</label><input id="blog-search" name="q" type="search" defaultValue={query.q || ""} placeholder="مثال: سعر العشب، تكلفة الحديقة، شبكة الري" /></div><button className="button" type="submit">بحث</button></form>
      </PageHero>
      <section className="content-section content-section--editorial-listing">
        <Container>
          {page?.body ? <RichText html={page.body} className="listing-intro" /> : null}
          <IntentRail eyebrow="أسئلة قبل الشراء" title="المعلومة اللي يحتاجها العميل قبل عرض السعر" description="مسارات مبنية على الأسئلة المتكررة في نتائج البحث: التكلفة، المقارنة، الصيانة، واختيار الحل المناسب للمناخ والمساحة." items={ARTICLE_MARKET_INTENTS} />
          <div className="grid grid--3 listing-grid listing-grid--articles">{data.results.length ? data.results.map((article, index) => <ArticleCard key={article.id} article={article} priority={index < 3} index={offset + index} />) : <EmptyState message="لم نجد مقالات تطابق بحثك." />}</div>
          <Pagination current={current} count={data.count} pageSize={12} href={query.q ? `/blog/?q=${encodeURIComponent(query.q)}` : "/blog/"} />
        </Container>
      </section>
      <SeoJsonLd schema={page?.seo.schema} />
    </>
  );
}
