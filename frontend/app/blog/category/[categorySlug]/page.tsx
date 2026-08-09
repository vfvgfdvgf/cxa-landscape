import type { Metadata } from "next";

import { ArticleCard } from "@/components/content/Cards";
import { SeoJsonLd } from "@/components/seo/JsonLd";
import { Breadcrumbs } from "@/components/ui/Breadcrumbs";
import { Container } from "@/components/ui/Container";
import { PageHero } from "@/components/ui/PageHero";
import { EmptyState, Pagination } from "@/components/ui/States";
import { buildMetadata } from "@/lib/metadata";
import { detailApi, normalizeRouteParam, pageNumber } from "@/lib/page-data";
import type { Category } from "@/types";

async function getCategory(slug: string, page = 1) {
  const normalized = normalizeRouteParam(slug);
  return detailApi<Category>(
    `blog/categories/${encodeURIComponent(normalized)}/?page=${page}`,
    300,
    ["articles", "categories", `category-${normalized}`],
  );
}

export async function generateMetadata({ params }: { params: Promise<{ categorySlug: string }> }): Promise<Metadata> {
  const { categorySlug } = await params;
  return buildMetadata((await getCategory(categorySlug)).seo);
}

export default async function BlogCategoryPage({
  params,
  searchParams,
}: {
  params: Promise<{ categorySlug: string }>;
  searchParams: Promise<{ page?: string }>;
}) {
  const [{ categorySlug }, query] = await Promise.all([params, searchParams]);
  const current = pageNumber(query.page);
  const category = await getCategory(categorySlug, current);
  const articles = category.articles;

  return (
    <>
      <PageHero eyebrow="تصنيف المقالات" title={category.name} description={category.description || `مقالات وأدلة ضمن ${category.name}.`}>
        <Breadcrumbs items={[{ label: "المقالات", href: "/blog/" }, { label: category.name }]} />
      </PageHero>
      <section className="content-section">
        <Container>
          <div className="grid grid--3">
            {articles?.results.length
              ? articles.results.map((article, index) => <ArticleCard key={article.id} article={article} priority={index < 3} />)
              : <EmptyState message="لا توجد مقالات منشورة في هذا التصنيف حاليًا." />}
          </div>
          {articles ? <Pagination current={current} count={articles.count} pageSize={12} href={category.url} /> : null}
        </Container>
      </section>
      <SeoJsonLd schema={category.seo.schema} />
    </>
  );
}
