import type { Metadata } from "next";

import { ArticleCard } from "@/components/content/Cards";
import { RichText } from "@/components/content/RichText";
import { SeoJsonLd } from "@/components/seo/JsonLd";
import { Breadcrumbs } from "@/components/ui/Breadcrumbs";
import { Container } from "@/components/ui/Container";
import { PageHero } from "@/components/ui/PageHero";
import { EmptyState, Pagination } from "@/components/ui/States";
import { djangoApi, withQuery } from "@/lib/django-api";
import { buildMetadata, staticMetadata } from "@/lib/metadata";
import { getManagedPage, pageNumber } from "@/lib/page-data";
import type { Article, PaginatedResponse } from "@/types";

export async function generateMetadata(): Promise<Metadata> {
  const page = await getManagedPage("blog");
  return page
    ? buildMetadata({ ...page.seo, canonical_path: "/blog/" })
    : staticMetadata("مقالات النخيل واللاندسكيب", "أدلة عملية للعناية بالنخيل والحدائق والري واتخاذ قرارات أفضل للمساحات الخارجية.", "/blog/");
}

export default async function BlogPage({
  searchParams,
}: {
  searchParams: Promise<{ page?: string; q?: string }>;
}) {
  const query = await searchParams;
  const current = pageNumber(query.page);
  const [page, data] = await Promise.all([
    getManagedPage("blog"),
    djangoApi<PaginatedResponse<Article>>(
      withQuery("blog/", { page: current, q: query.q }),
      { revalidate: 300, tags: ["articles"] },
    ),
  ]);

  return (
    <>
      <PageHero
        eyebrow="دليل الخبرة"
        title={page?.hero_title || page?.title || "قرارات أفضل تبدأ بمعلومة واضحة"}
        description={page?.intro_text || "معرفة عملية تساعدك على اختيار الأنسب والعناية بمشروعك بثقة على المدى الطويل."}
      >
        <Breadcrumbs items={[{ label: "المقالات" }]} />
        <form className="button-row hero-search" action="/blog/" method="get" role="search">
          <div className="form-field">
            <label className="sr-only" htmlFor="blog-search">ابحث في المقالات</label>
            <input id="blog-search" name="q" type="search" defaultValue={query.q || ""} placeholder="ما الذي تبحث عنه؟" />
          </div>
          <button className="button" type="submit">بحث</button>
        </form>
      </PageHero>
      <section className="content-section">
        <Container>
          {page?.body ? <RichText html={page.body} className="listing-intro" /> : null}
          <div className="grid grid--3">
            {data.results.length ? data.results.map((article, index) => <ArticleCard key={article.id} article={article} priority={index < 3} />) : <EmptyState message="لم نجد مقالات تطابق بحثك." />}
          </div>
          <Pagination current={current} count={data.count} pageSize={12} href={query.q ? `/blog/?q=${encodeURIComponent(query.q)}` : "/blog/"} />
        </Container>
      </section>
      <SeoJsonLd schema={page?.seo.schema} />
    </>
  );
}
