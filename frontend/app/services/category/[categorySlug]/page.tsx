import type { Metadata } from "next";

import { ServiceCard } from "@/components/content/Cards";
import { CallToAction } from "@/components/content/CallToAction";
import { JsonLd } from "@/components/seo/JsonLd";
import { Breadcrumbs } from "@/components/ui/Breadcrumbs";
import { Container } from "@/components/ui/Container";
import { PageHero } from "@/components/ui/PageHero";
import { EmptyState, Pagination } from "@/components/ui/States";
import { djangoApi, withQuery } from "@/lib/django-api";
import { buildMetadata, SITE_URL } from "@/lib/metadata";
import { detailApi, pageNumber } from "@/lib/page-data";
import type { PaginatedResponse, Service, ServiceCategory } from "@/types";

async function getCategory(slug: string) {
  return detailApi<ServiceCategory>(`service-categories/${encodeURIComponent(slug)}/`, 900, ["service-categories", `service-category-${slug}`]);
}

export async function generateMetadata({ params }: { params: Promise<{ categorySlug: string }> }): Promise<Metadata> {
  const { categorySlug } = await params;
  return buildMetadata((await getCategory(categorySlug)).seo);
}

export default async function ServiceCategoryPage({
  params,
  searchParams,
}: {
  params: Promise<{ categorySlug: string }>;
  searchParams: Promise<{ page?: string }>;
}) {
  const [{ categorySlug }, query] = await Promise.all([params, searchParams]);
  const current = pageNumber(query.page);
  const [category, services] = await Promise.all([
    getCategory(categorySlug),
    djangoApi<PaginatedResponse<Service>>(
      withQuery("services/", { category: categorySlug, page: current }),
      { revalidate: 900, tags: ["services", `service-category-${categorySlug}`] },
    ),
  ]);
  const categoryUrl = `${SITE_URL}${category.url}`;
  const schema = [
    {
      "@context": "https://schema.org",
      "@type": "CollectionPage",
      name: `خدمات ${category.name}`,
      description: category.description || `استعرض خدمات ${category.name} المتاحة لدى نخيل نجد.`,
      url: categoryUrl,
      mainEntity: {
        "@type": "ItemList",
        numberOfItems: services.count,
        itemListElement: services.results.map((service, index) => ({
          "@type": "ListItem",
          position: (current - 1) * 12 + index + 1,
          name: service.title,
          url: `${SITE_URL}${service.url}`,
        })),
      },
    },
    {
      "@context": "https://schema.org",
      "@type": "BreadcrumbList",
      itemListElement: [
        { "@type": "ListItem", position: 1, name: "الرئيسية", item: SITE_URL },
        { "@type": "ListItem", position: 2, name: "الخدمات", item: `${SITE_URL}/services/` },
        { "@type": "ListItem", position: 3, name: category.name, item: categoryUrl },
      ],
    },
  ];

  return (
    <>
      <PageHero
        eyebrow="تصنيف خدمات"
        title={`خدمات ${category.name}`}
        description={category.description || `استعرض خدمات ${category.name} واختر الخدمة الأقرب لطبيعة موقعك.`}
      >
        <Breadcrumbs items={[{ label: "الخدمات", href: "/services/" }, { label: category.name }]} />
      </PageHero>
      <section className="content-section">
        <Container>
          <div className="grid grid--3">
            {services.results.length
              ? services.results.map((service, index) => <ServiceCard key={service.id} service={service} priority={index < 3} />)
              : <EmptyState message="لا توجد خدمات منشورة في هذا التصنيف حاليًا." />}
          </div>
          <Pagination current={current} count={services.count} pageSize={12} href={category.url} />
        </Container>
      </section>
      <CallToAction title={`هل تحتاج خدمة ضمن ${category.name}؟`} />
      <JsonLd data={schema} />
    </>
  );
}
