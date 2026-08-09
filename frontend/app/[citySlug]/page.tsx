import type { Metadata } from "next";
import Link from "next/link";
import { cache } from "react";

import { ArticleCard, ProjectCard, ServiceCard } from "@/components/content/Cards";
import { CallToAction } from "@/components/content/CallToAction";
import { RichText } from "@/components/content/RichText";
import { JsonLd } from "@/components/seo/JsonLd";
import { Breadcrumbs } from "@/components/ui/Breadcrumbs";
import { Container } from "@/components/ui/Container";
import { PageHero } from "@/components/ui/PageHero";
import { SectionHeading } from "@/components/ui/SectionHeading";
import { buildMetadata, SITE_URL } from "@/lib/metadata";
import { detailApi } from "@/lib/page-data";
import { plainText } from "@/lib/text";
import type { City } from "@/types";

const getCity = cache(async (slug: string) => (
  detailApi<City>(`cities/${encodeURIComponent(slug)}/`, 900, ["cities", `city-${slug}`])
));

export async function generateMetadata({ params }: { params: Promise<{ citySlug: string }> }): Promise<Metadata> {
  const { citySlug } = await params;
  return buildMetadata((await getCity(citySlug)).seo);
}

export default async function CityDetailPage({ params }: { params: Promise<{ citySlug: string }> }) {
  const { citySlug } = await params;
  const city = await getCity(citySlug);
  const description = city.seo.description || plainText(city.short_description || city.content);
  const services = city.services || [];
  const projects = city.projects || [];
  const articles = city.articles || [];
  const schema = {
    "@context": "https://schema.org",
    "@type": "City",
    name: city.name,
    description,
    url: `${SITE_URL}${city.url}`,
    containedInPlace: { "@type": "Country", name: "Saudi Arabia" },
  };
  const breadcrumbSchema = {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: [
      { "@type": "ListItem", position: 1, name: "المدن", item: `${SITE_URL}/cities/` },
      { "@type": "ListItem", position: 2, name: city.name, item: `${SITE_URL}${city.url}` },
    ],
  };

  return (
    <>
      <PageHero
        eyebrow={city.region || "مدينة تغطية"}
        title={city.hero_title || `خدمات نخيل ولاندسكيب في ${city.name}`}
        description={description}
      >
        <Breadcrumbs items={[{ label: "المدن", href: "/cities/" }, { label: city.name }]} />
        <dl className="place-stats" aria-label={`ملخص تغطية ${city.name}`}>
          <div><dt>الأحياء</dt><dd>{city.districts.length.toLocaleString("ar-SA")}</dd></div>
          <div><dt>الخدمات المعروضة</dt><dd>{services.length.toLocaleString("ar-SA")}</dd></div>
          <div><dt>الأعمال والنماذج</dt><dd>{projects.length.toLocaleString("ar-SA")}</dd></div>
        </dl>
      </PageHero>

      <section className="content-section">
        <Container>
          {city.content ? <RichText html={city.content} /> : null}
          {city.districts.length ? (
            <>
              <SectionHeading
                eyebrow="تغطية محلية"
                title={`أحياء ${city.name}`}
                intro="اختر الحي للوصول إلى الخدمات والأعمال ونماذج الحلول المرتبطة بنطاقه مباشرة."
              />
              <div className="grid grid--4">
                {city.districts.map((district) => (
                  <article className="archive-stat" key={district.id}>
                    <p className="eyebrow">{city.name}</p>
                    <h2>{district.name}</h2>
                    <Link className="text-link" href={district.url}>استكشف خدمات الحي</Link>
                  </article>
                ))}
              </div>
            </>
          ) : null}
        </Container>
      </section>

      {services.length ? (
        <section className="content-section content-section--tinted">
          <Container>
            <SectionHeading
              eyebrow="الخدمات"
              title={`خدماتنا في ${city.name}`}
              intro="خدمات منظمة بنطاق واضح، ويمكن الانتقال من كل خدمة إلى صفحة المدينة ثم طلب المعاينة."
              action={<Link className="text-link" href="/services/">كل الخدمات</Link>}
            />
            <div className="grid grid--3 experience-grid">
              {services.slice(0, 6).map((local) => (
                <ServiceCard key={local.id} service={{ ...local.service, url: local.url }} />
              ))}
            </div>
          </Container>
        </section>
      ) : null}

      {projects.length ? (
        <section className="content-section">
          <Container>
            <SectionHeading
              eyebrow="معرض بصري"
              title={`أعمال ونماذج ضمن نطاق ${city.name}`}
              intro="نوضح داخل كل بطاقة هل الموقع موثق فعليًا أو أن السجل نموذج حل مرتبط بنطاق الخدمة فقط."
              action={<Link className="text-link" href={`/projects/?city=${encodeURIComponent(city.slug)}`}>كل ما يرتبط بالمدينة</Link>}
            />
            <aside className="transparency-note">
              <strong>شفافية الموقع</strong>
              <p>ربط الصورة بمدينة أو حي كنطاق خدمة لا يعني أن التنفيذ تم هناك؛ موقع التنفيذ لا يظهر إلا عندما يكون موثقًا في لوحة الإدارة.</p>
            </aside>
            <div className="grid grid--3">
              {projects.slice(0, 9).map((project) => <ProjectCard key={project.id} project={project} />)}
            </div>
          </Container>
        </section>
      ) : null}

      {articles.length ? (
        <section className="content-section content-section--tinted">
          <Container>
            <SectionHeading
              eyebrow="دليل قبل التنفيذ"
              title={`مقالات مرتبطة بـ${city.name}`}
              intro="محتوى يساعد على فهم الاختيارات والصيانة والتكاليف قبل بدء المشروع."
            />
            <div className="grid grid--3">
              {articles.slice(0, 3).map((article) => <ArticleCard key={article.id} article={article} />)}
            </div>
          </Container>
        </section>
      ) : null}

      <CallToAction title={`اطلب معاينة في ${city.name}`} />
      <JsonLd data={[schema, breadcrumbSchema]} />
    </>
  );
}
