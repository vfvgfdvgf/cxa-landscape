import type { Metadata } from "next";
import Link from "next/link";
import { cache } from "react";

import { ArticleCard, ProjectCard, ServiceCard } from "@/components/content/Cards";
import { CallToAction } from "@/components/content/CallToAction";
import { JsonLd } from "@/components/seo/JsonLd";
import { Breadcrumbs } from "@/components/ui/Breadcrumbs";
import { Container } from "@/components/ui/Container";
import { PageHero } from "@/components/ui/PageHero";
import { SectionHeading } from "@/components/ui/SectionHeading";
import { buildMetadata, SITE_URL } from "@/lib/metadata";
import { detailApi, normalizeRouteParam } from "@/lib/page-data";
import type { District } from "@/types";

const getDistrict = cache(async (city: string, district: string) => {
  return detailApi<District>(
    `cities/${encodeURIComponent(city)}/districts/${encodeURIComponent(district)}/`,
    900,
    ["cities", "districts", `district-${district}`],
  );
});

export async function generateMetadata({
  params,
}: {
  params: Promise<{ citySlug: string; districtSlug: string }>;
}): Promise<Metadata> {
  const { citySlug, districtSlug } = await params;
  return buildMetadata((await getDistrict(normalizeRouteParam(citySlug), normalizeRouteParam(districtSlug))).seo);
}

export default async function DistrictDetailPage({
  params,
}: {
  params: Promise<{ citySlug: string; districtSlug: string }>;
}) {
  const { citySlug, districtSlug } = await params;
  const district = await getDistrict(normalizeRouteParam(citySlug), normalizeRouteParam(districtSlug));
  const services = district.services || [];
  const articles = district.articles || [];
  const schema = {
    "@context": "https://schema.org",
    "@type": "Place",
    name: district.name,
    containedInPlace: { "@type": "City", name: district.city.name },
    url: `${SITE_URL}${district.url}`,
  };
  const breadcrumbSchema = {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: [
      { "@type": "ListItem", position: 1, name: "الأحياء", item: `${SITE_URL}/districts/` },
      { "@type": "ListItem", position: 2, name: district.city.name, item: `${SITE_URL}/${district.city.slug}/` },
      { "@type": "ListItem", position: 3, name: district.name, item: `${SITE_URL}${district.url}` },
    ],
  };

  return (
    <>
      <PageHero
        eyebrow={`حي في ${district.city.name}`}
        title={`خدمات النخيل واللاندسكيب في ${district.name}`}
        description={`دليل محلي يجمع الخدمات والمشاريع والنصائح المناسبة لحي ${district.name} في ${district.city.name}.`}
      >
        <Breadcrumbs items={[
          { label: "الأحياء", href: "/districts/" },
          { label: district.city.name, href: `/${district.city.slug}/` },
          { label: district.name },
        ]} />
        <dl className="place-stats" aria-label={`ملخص محتوى حي ${district.name}`}>
          <div><dt>الخدمات</dt><dd>{services.length.toLocaleString("ar-SA")}</dd></div>
          <div><dt>الأعمال والنماذج</dt><dd>{district.projects.length.toLocaleString("ar-SA")}</dd></div>
          <div><dt>المقالات</dt><dd>{articles.length.toLocaleString("ar-SA")}</dd></div>
        </dl>
      </PageHero>

      <section className="content-section">
        <Container className="district-overview">
          <div>
            <p className="eyebrow">خدمة تعرف المكان</p>
            <h2>حلول تبدأ من طبيعة الحي والموقع</h2>
            <p>نربط نوع النخيل، شبكة الري، الخامات وخطة الصيانة بظروف الموقع وطريقة استخدام المساحة قبل بدء التنفيذ.</p>
          </div>
          <aside>
            <span>نطاق الخدمة</span>
            <strong>{district.name}</strong>
            <small>{district.city.name}</small>
            <Link className="button" href={`/quote-request/?city=${encodeURIComponent(district.city.name)}&district=${encodeURIComponent(district.name)}`}>اطلب معاينة</Link>
          </aside>
        </Container>
      </section>

      {services.length ? <section className="content-section content-section--tinted"><Container><SectionHeading title="الخدمات المتاحة" intro="حلول يمكن طلبها مباشرة وفق موقع المشروع واحتياجه." /><div className="grid grid--3 experience-grid">{services.map((local) => <ServiceCard key={local.id} service={{ ...local.service, url: `/${district.city.slug}/districts/${district.slug}/${local.service.slug}/` }} />)}</div></Container></section> : null}
      {district.projects.length ? <section className="content-section"><Container><SectionHeading title="أعمال ونماذج مرتبطة بالحي" intro="نعرض موقع التنفيذ عندما يكون موثقًا، ونميّز نماذج نطاق الخدمة بوضوح." /><div className="grid grid--3">{district.projects.map((project) => <ProjectCard key={project.id} project={project} />)}</div></Container></section> : null}
      {articles.length ? <section className="content-section content-section--tinted"><Container><SectionHeading title="مقالات مرتبطة بالموقع" intro="معرفة عملية تساعدك قبل التوريد والتنفيذ." /><div className="grid grid--3">{articles.map((article) => <ArticleCard key={article.id} article={article} />)}</div></Container></section> : null}
      <CallToAction title={`اطلب خدمة في ${district.name}`} />
      <JsonLd data={[schema, breadcrumbSchema]} />
    </>
  );
}
