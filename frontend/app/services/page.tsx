import type { Metadata } from "next";
import Link from "next/link";

import { ServiceCard } from "@/components/content/Cards";
import { CallToAction } from "@/components/content/CallToAction";
import { RichText } from "@/components/content/RichText";
import { SeoJsonLd } from "@/components/seo/JsonLd";
import { Breadcrumbs } from "@/components/ui/Breadcrumbs";
import { PageHero } from "@/components/ui/PageHero";
import { Container } from "@/components/ui/Container";
import { EmptyState, Pagination } from "@/components/ui/States";
import { djangoApi, withQuery } from "@/lib/django-api";
import { getManagedPage, pageNumber } from "@/lib/page-data";
import { buildMetadata, staticMetadata } from "@/lib/metadata";
import type { PaginatedResponse, Service, ServiceCategory } from "@/types";

export async function generateMetadata(): Promise<Metadata> {
  const page = await getManagedPage("services");
  return page ? buildMetadata({ ...page.seo, canonical_path: "/services/" }) : staticMetadata("خدمات النخيل واللاندسكيب", "خدمات متخصصة في تنسيق الحدائق والنخيل والري والشبوك للمشاريع السكنية والتجارية.", "/services/");
}

export default async function ServicesPage({ searchParams }: { searchParams: Promise<{ page?: string; q?: string }> }) {
  const query = await searchParams;
  const current = pageNumber(query.page);
  const [page, data, categories] = await Promise.all([
    getManagedPage("services"),
    djangoApi<PaginatedResponse<Service>>(withQuery("services/", { page: current, q: query.q }), { revalidate: 900, tags: ["services"] }),
    djangoApi<ServiceCategory[]>("service-categories/", { revalidate: 900, tags: ["services", "service-categories"] }),
  ]);
  return (
    <>
      <PageHero
        eyebrow="الخدمات"
        title={page?.hero_title || page?.title || "خبرة تبدأ من الأرض وتنتهي بالتفاصيل"}
        description={page?.intro_text || "حلول متخصصة تُبنى حول طبيعة الموقع وطموحك للمساحة، من التوريد والتنسيق إلى الري والصيانة."}
      >
        <Breadcrumbs items={[{ label: "الخدمات" }]} />
        <form className="button-row hero-search" action="/services/" method="get" role="search">
          <div className="form-field">
            <label className="sr-only" htmlFor="service-search">ابحث في الخدمات</label>
            <input id="service-search" name="q" type="search" defaultValue={query.q || ""} placeholder="ابحث عن خدمة" />
          </div>
          <button className="button" type="submit">بحث</button>
        </form>
      </PageHero>
      <section className="content-section">
        <Container>
          {page?.body ? <RichText html={page.body} className="listing-intro" /> : null}
          {categories.length ? <nav className="tag-list" aria-label="تصنيفات الخدمات">{categories.map((category) => <Link key={category.id} href={category.url}>{category.name} <span aria-hidden="true">({category.service_count})</span></Link>)}</nav> : null}
          <div className="grid grid--3">{data.results.length ? data.results.map((service, index) => <ServiceCard key={service.id} service={service} priority={index < 3} />) : <EmptyState message="لم نجد خدمة تطابق بحثك." />}</div>
          <Pagination current={current} count={data.count} pageSize={12} href={query.q ? `/services/?q=${encodeURIComponent(query.q)}` : "/services/"} />
        </Container>
      </section>
      <CallToAction />
      <SeoJsonLd schema={page?.seo.schema} />
    </>
  );
}
