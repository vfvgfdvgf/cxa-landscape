import type { Metadata } from "next";
import Link from "next/link";

import { ArticleCard, ServiceCard } from "@/components/content/Cards";
import { CallToAction } from "@/components/content/CallToAction";
import { ResponsiveImage } from "@/components/content/ResponsiveImage";
import { RichText } from "@/components/content/RichText";
import { JsonLd } from "@/components/seo/JsonLd";
import { Breadcrumbs } from "@/components/ui/Breadcrumbs";
import { Container } from "@/components/ui/Container";
import { PageHero } from "@/components/ui/PageHero";
import { SectionHeading } from "@/components/ui/SectionHeading";
import { djangoApi, withQuery } from "@/lib/django-api";
import { buildMetadata, SITE_URL } from "@/lib/metadata";
import { detailApi } from "@/lib/page-data";
import { plainText } from "@/lib/text";
import type { Article, PaginatedResponse, Service } from "@/types";

async function getService(slug: string) {
  return detailApi<Service>(`services/${encodeURIComponent(slug)}/`, 900, ["services", `service-${slug}`]);
}

export async function generateMetadata({ params }: { params: Promise<{ serviceSlug: string }> }): Promise<Metadata> {
  const { serviceSlug } = await params;
  return buildMetadata((await getService(serviceSlug)).seo);
}

export default async function ServiceDetailPage({ params }: { params: Promise<{ serviceSlug: string }> }) {
  const { serviceSlug } = await params;
  const service = await getService(serviceSlug);
  const description = service.seo.description || plainText(service.description);
  const serviceUrl = `${SITE_URL}${service.url}`;
  const [relatedServices, relatedArticles] = await Promise.all([
    djangoApi<PaginatedResponse<Service>>(withQuery("services/", { category: service.category?.slug }), { revalidate: 900, tags: ["services"] }),
    djangoApi<PaginatedResponse<Article>>(withQuery("blog/", { q: service.short_title || service.title }), { revalidate: 300, tags: ["articles"] }),
  ]);
  const siblingServices = relatedServices.results.filter((item) => item.id !== service.id).slice(0, 3);
  const schema = [
    {
      "@context": "https://schema.org",
      "@type": "Service",
      name: service.title,
      serviceType: service.short_title || service.title,
      description,
      url: serviceUrl,
      image: service.image?.url,
      category: service.category?.name,
      provider: { "@type": "Organization", name: "نخيل نجد", url: SITE_URL },
      areaServed: service.cities.length ? service.cities.map((city) => ({ "@type": "City", name: city.name })) : { "@type": "Country", name: "Saudi Arabia" },
    },
    {
      "@context": "https://schema.org",
      "@type": "BreadcrumbList",
      itemListElement: [
        { "@type": "ListItem", position: 1, name: "الرئيسية", item: SITE_URL },
        { "@type": "ListItem", position: 2, name: "الخدمات", item: `${SITE_URL}/services/` },
        { "@type": "ListItem", position: 3, name: service.title, item: serviceUrl },
      ],
    },
  ];

  return (
    <>
      <PageHero eyebrow={service.category?.name || "خدمة"} title={service.title} description={description}>
        <Breadcrumbs items={[{ label: "الخدمات", href: "/services/" }, { label: service.title }]} />
        <div className="detail-facts">
          <span><strong>{service.benefits.length.toLocaleString("ar-SA")}</strong> نقاط ضمن النطاق</span>
          <span><strong>{service.cities.length ? service.cities.length.toLocaleString("ar-SA") : "السعودية"}</strong> {service.cities.length ? "مدن مرتبطة" : "نطاق خدمة"}</span>
          <span><strong>معاينة</strong> قبل اعتماد العرض</span>
        </div>
      </PageHero>

      <section className="content-section detail-section">
        <Container>
          {service.image ? <ResponsiveImage image={service.image} className="detail-media detail-media--hero" sizes="100vw" priority /> : null}
          <div className="detail-layout detail-layout--editorial">
            <article className="detail-article">
              <p className="detail-kicker">الخدمة / {service.short_title || service.title}</p>
              <p className="detail-deck">{description}</p>
              <RichText html={service.description} />
              {service.benefits.length ? (
                <section className="detail-block">
                  <h2>ما الذي يدخل ضمن نطاق الخدمة؟</h2>
                  <ol className="detail-checklist">{service.benefits.map((benefit, index) => <li key={benefit}><span>{String(index + 1).padStart(2, "0")}</span><p>{benefit}</p></li>)}</ol>
                </section>
              ) : null}
              {service.cities.length ? (
                <section className="detail-block">
                  <h2>صفحات الخدمة حسب المدينة</h2>
                  <p>اختر المدينة لعرض الصفحة المحلية المرتبطة بالخدمة والمحتوى المتاح فيها.</p>
                  <div className="tag-list">{service.cities.map((city) => <Link key={city.id} href={`/${city.slug}/${service.slug}/`}>{service.title} في {city.name}</Link>)}</div>
                </section>
              ) : null}
            </article>
            <aside className="detail-sidebar detail-sidebar--editorial">
              <p className="eyebrow">قبل طلب السعر</p>
              <h2>أرسل معلومات تكفي لتسعير أدق</h2>
              <ul className="detail-mini-list"><li>المدينة والحي</li><li>صور الموقع من عدة زوايا</li><li>المقاسات أو المخطط إن وجد</li><li>الاستخدام المطلوب والموعد التقريبي</li></ul>
              <Link className="button" href={`/quote-request/?service=${encodeURIComponent(service.title)}`}>طلب عرض سعر</Link>
              {service.primary_city ? <p className="detail-sidebar__note">المدينة الأساسية: <Link href={`/${service.primary_city.slug}/`}>{service.primary_city.name}</Link></p> : null}
            </aside>
          </div>
        </Container>
      </section>

      {siblingServices.length ? <section className="content-section content-section--tinted"><Container><SectionHeading eyebrow="خدمات مرتبطة" title="كمّل المشروع من نفس المسار" intro="خدمات قريبة من نفس التصنيف تساعدك تجمع نطاق المشروع بدل ما تتعامل مع كل عنصر بشكل منفصل." /><div className="grid grid--3 listing-grid">{siblingServices.map((item, index) => <ServiceCard key={item.id} service={item} index={index} />)}</div></Container></section> : null}
      {relatedArticles.results.length ? <section className="content-section"><Container><SectionHeading eyebrow="قبل القرار" title="اقرأ قبل التنفيذ" intro="مقالات مرتبطة بالخدمة تساعدك تقارن الخيارات وتفهم عوامل التكلفة والصيانة." /><div className="grid grid--3 listing-grid">{relatedArticles.results.slice(0, 3).map((item, index) => <ArticleCard key={item.id} article={item} index={index} />)}</div></Container></section> : null}
      <CallToAction title={`هل تبحث عن ${service.short_title || service.title}؟`} />
      <JsonLd data={schema} />
    </>
  );
}
