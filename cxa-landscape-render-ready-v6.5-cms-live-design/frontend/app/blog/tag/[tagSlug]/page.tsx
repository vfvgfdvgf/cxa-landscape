import type { Metadata } from "next";

import { ArticleCard } from "@/components/content/Cards";
import { SeoJsonLd } from "@/components/seo/JsonLd";
import { Breadcrumbs } from "@/components/ui/Breadcrumbs";
import { Container } from "@/components/ui/Container";
import { PageHero } from "@/components/ui/PageHero";
import { EmptyState, Pagination } from "@/components/ui/States";
import { buildMetadata } from "@/lib/metadata";
import { detailApi, normalizeRouteParam, pageNumber } from "@/lib/page-data";
import type { Tag } from "@/types";

async function getTag(slug: string, page = 1) {
  const normalized = normalizeRouteParam(slug);
  return detailApi<Tag>(
    `blog/tags/${encodeURIComponent(normalized)}/?page=${page}`,
    300,
    ["articles", "tags", `tag-${normalized}`],
  );
}

export async function generateMetadata({ params }: { params: Promise<{ tagSlug: string }> }): Promise<Metadata> {
  const { tagSlug } = await params;
  return buildMetadata((await getTag(tagSlug)).seo);
}

export default async function BlogTagPage({
  params,
  searchParams,
}: {
  params: Promise<{ tagSlug: string }>;
  searchParams: Promise<{ page?: string }>;
}) {
  const [{ tagSlug }, query] = await Promise.all([params, searchParams]);
  const current = pageNumber(query.page);
  const tag = await getTag(tagSlug, current);
  const articles = tag.articles;

  return (
    <>
      <PageHero eyebrow="وسم المقالات" title={`#${tag.name}`} description={`المقالات المنشورة المرتبطة بوسم ${tag.name}.`}>
        <Breadcrumbs items={[{ label: "المقالات", href: "/blog/" }, { label: `#${tag.name}` }]} />
      </PageHero>
      <section className="content-section">
        <Container>
          <div className="grid grid--3">
            {articles?.results.length
              ? articles.results.map((article, index) => <ArticleCard key={article.id} article={article} priority={index < 3} />)
              : <EmptyState message="لا توجد مقالات منشورة تحت هذا الوسم حاليًا." />}
          </div>
          {articles ? <Pagination current={current} count={articles.count} pageSize={12} href={tag.url} /> : null}
        </Container>
      </section>
      <SeoJsonLd schema={tag.seo.schema} />
    </>
  );
}
