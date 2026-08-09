import type { Metadata } from "next";
import Link from "next/link";

import { RichText } from "@/components/content/RichText";
import { LeadForm } from "@/components/forms/LeadForm";
import { SeoJsonLd } from "@/components/seo/JsonLd";
import { Breadcrumbs } from "@/components/ui/Breadcrumbs";
import { Container } from "@/components/ui/Container";
import { PageHero } from "@/components/ui/PageHero";
import { djangoApi } from "@/lib/django-api";
import { buildMetadata, staticMetadata } from "@/lib/metadata";
import { getManagedPage } from "@/lib/page-data";
import type { City, PaginatedResponse, Service, SiteSettings } from "@/types";

export async function generateMetadata(): Promise<Metadata> {
  const page = await getManagedPage("contact");
  return page
    ? buildMetadata({ ...page.seo, canonical_path: "/contact/" })
    : staticMetadata("تواصل معنا", "شاركنا موقع مشروعك واحتياجك لنرتب المعاينة ونقترح الخطوة الأنسب.", "/contact/");
}

export default async function ContactPage({
  searchParams,
}: {
  searchParams: Promise<{ service?: string; city?: string }>;
}) {
  const query = await searchParams;
  const [page, site, services, cities] = await Promise.all([
    getManagedPage("contact"),
    djangoApi<SiteSettings>("site/", { revalidate: 300 }),
    djangoApi<PaginatedResponse<Service>>("services/?page_size=48", { revalidate: 900 }),
    djangoApi<PaginatedResponse<City>>("cities/?page_size=48", { revalidate: 900 }),
  ]);

  return (
    <>
      <PageHero
        eyebrow="تواصل مباشر"
        title={page?.hero_title || page?.title || "أخبرنا عن المساحة التي تتخيلها"}
        description={page?.intro_text || "شاركنا موقع المشروع ونوع الخدمة، وسيعود إليك الفريق لترتيب الخطوة التالية بوضوح."}
      >
        <Breadcrumbs items={[{ label: "تواصل معنا" }]} />
      </PageHero>
      <section className="content-section">
        <Container className="contact-layout">
          <div>
            {page?.body ? <RichText html={page.body} className="listing-intro" /> : null}
            <LeadForm
              endpoint="contact"
              services={services.results.map((item) => item.title)}
              cities={cities.results.map((item) => item.name)}
              defaultService={query.service}
              defaultCity={query.city}
            />
          </div>
          <aside className="contact-card">
            <p className="eyebrow">نحن بالقرب</p>
            <h2>تواصل بالطريقة الأنسب لك</h2>
            {site.contact_phone ? <a href={`tel:${site.contact_phone}`}>هاتف: {site.contact_phone}</a> : null}
            {site.email ? <a href={`mailto:${site.email}`}>البريد: {site.email}</a> : null}
            {site.address ? <p>{site.address}</p> : null}
            <p>للتسعير التفصيلي أرسل مساحة المشروع والميزانية المتوقعة لنجهّز تصورًا أوليًا أدق.</p>
            <Link className="button" href="/quote-request/">طلب عرض سعر</Link>
          </aside>
        </Container>
      </section>
      <SeoJsonLd schema={page?.seo.schema} />
    </>
  );
}
