import type { Metadata } from "next";
import Link from "next/link";

import { CallToAction } from "@/components/content/CallToAction";
import { ResponsiveImage } from "@/components/content/ResponsiveImage";
import { RichText } from "@/components/content/RichText";
import { JsonLd } from "@/components/seo/JsonLd";
import { Breadcrumbs } from "@/components/ui/Breadcrumbs";
import { Container } from "@/components/ui/Container";
import { PageHero } from "@/components/ui/PageHero";
import { buildMetadata, SITE_URL } from "@/lib/metadata";
import { detailApi } from "@/lib/page-data";
import { plainText } from "@/lib/text";
import type { Service } from "@/types";

async function getService(slug: string) { return detailApi<Service>(`services/${encodeURIComponent(slug)}/`, 900, ["services", `service-${slug}`]); }

export async function generateMetadata({ params }: { params: Promise<{ serviceSlug: string }> }): Promise<Metadata> { const { serviceSlug } = await params; return buildMetadata((await getService(serviceSlug)).seo); }

export default async function ServiceDetailPage({ params }: { params: Promise<{ serviceSlug: string }> }) {
  const { serviceSlug } = await params;
  const service = await getService(serviceSlug);
  const description = service.seo.description || plainText(service.description);
  const serviceUrl = `${SITE_URL}${service.url}`;
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
      areaServed: service.cities.length
        ? service.cities.map((city) => ({ "@type": "City", name: city.name }))
        : { "@type": "Country", name: "Saudi Arabia" },
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
  return <><PageHero eyebrow={service.category?.name || "خدمة"} title={service.title} description={description}><Breadcrumbs items={[{ label: "الخدمات", href: "/services/" }, { label: service.title }]} /></PageHero><section className="content-section"><Container className="detail-layout"><article>{service.image ? <ResponsiveImage image={service.image} className="detail-media" sizes="(max-width: 960px) 100vw, 70vw" priority /> : null}<RichText html={service.description} />{service.benefits.length ? <><h2>ما تتضمنه الخدمة</h2><ul className="benefits">{service.benefits.map((benefit) => <li key={benefit}>{benefit}</li>)}</ul></> : null}{service.cities.length ? <><h2>مدن تتوفر فيها الخدمة</h2><div className="tag-list">{service.cities.map((city) => <Link key={city.id} href={`/${city.slug}/${service.slug}/`}>{service.title} في {city.name}</Link>)}</div></> : null}</article><aside className="detail-sidebar"><h2>اطلب هذه الخدمة</h2><p>شاركنا موقع المشروع واحتياجك لنرتب المعاينة.</p><Link className="button" href={`/quote-request/?service=${encodeURIComponent(service.title)}`}>طلب عرض سعر</Link>{service.primary_city ? <p>المدينة الأساسية: <Link href={`/${service.primary_city.slug}/`}>{service.primary_city.name}</Link></p> : null}</aside></Container></section><CallToAction title={`هل تبحث عن ${service.short_title || service.title}؟`} /><JsonLd data={schema} /></>;
}
