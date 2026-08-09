import Link from "next/link";

import { CallToAction } from "@/components/content/CallToAction";
import { ResponsiveImage } from "@/components/content/ResponsiveImage";
import { RichText } from "@/components/content/RichText";
import { JsonLd } from "@/components/seo/JsonLd";
import { Breadcrumbs } from "@/components/ui/Breadcrumbs";
import { Container } from "@/components/ui/Container";
import { PageHero } from "@/components/ui/PageHero";
import { SITE_URL } from "@/lib/metadata";
import { plainText } from "@/lib/text";
import type { CityService } from "@/types";

export function LocalServicePage({ page }: { page: CityService }) {
  const cityUrl = `/${page.city.slug}/`;
  const description = page.seo.description || plainText(page.content);
  const schema = { "@context": "https://schema.org", "@type": "Service", name: page.hero_title || page.service.title, description, url: `${SITE_URL}${page.url}`, areaServed: { "@type": "City", name: page.city.name }, image: page.service.image?.url };
  const crumbs = [{ label: page.city.name, href: cityUrl }];
  if (page.district) crumbs.push({ label: page.district.name, href: `${cityUrl}districts/${page.district.slug}/` });
  crumbs.push({ label: page.hero_title || page.service.title, href: page.url });
  return <><PageHero eyebrow={`خدمات ${page.city.name}`} title={page.hero_title || `${page.service.title} في ${page.city.name}`} description={description}><Breadcrumbs items={crumbs} /></PageHero><section className="content-section"><Container className="detail-layout"><article>{page.service.image ? <ResponsiveImage image={page.service.image} className="detail-media" sizes="(max-width: 960px) 100vw, 70vw" priority /> : null}<RichText html={page.content} />{page.benefits.length ? <><h2>مزايا الخدمة</h2><ul className="benefits">{page.benefits.map((benefit) => <li key={benefit}>{benefit}</li>)}</ul></> : null}</article><aside className="detail-sidebar"><h2>خدمة محلية</h2><p>المدينة: <Link href={cityUrl}>{page.city.name}</Link></p>{page.district ? <p>الحي: <Link href={`${cityUrl}districts/${page.district.slug}/`}>{page.district.name}</Link></p> : null}<Link className="button" href={`/quote-request/?service=${encodeURIComponent(page.service.title)}&city=${encodeURIComponent(page.city.name)}`}>اطلب الخدمة</Link></aside></Container></section><CallToAction title={`احجز معاينة في ${page.city.name}`} /><JsonLd data={schema} /></>;
}
