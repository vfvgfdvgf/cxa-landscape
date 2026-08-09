import type { Metadata } from "next";

import { LeadForm } from "@/components/forms/LeadForm";
import { Breadcrumbs } from "@/components/ui/Breadcrumbs";
import { Container } from "@/components/ui/Container";
import { PageHero } from "@/components/ui/PageHero";
import { djangoApi } from "@/lib/django-api";
import { staticMetadata } from "@/lib/metadata";
import type { City, PaginatedResponse, Service, SiteSettings } from "@/types";

export const metadata: Metadata = staticMetadata(
  "طلب عرض سعر",
  "أرسل تفاصيل الموقع والمساحة والخدمة المطلوبة للحصول على عرض سعر بعد مراجعة نطاق المشروع.",
  "/quote-request/",
);

export default async function QuoteRequestPage({ searchParams }: { searchParams: Promise<{ service?: string; city?: string }> }) {
  const query = await searchParams;
  const [site, services, cities] = await Promise.all([
    djangoApi<SiteSettings>("site/", { revalidate: 300 }),
    djangoApi<PaginatedResponse<Service>>("services/?page_size=48", { revalidate: 900 }),
    djangoApi<PaginatedResponse<City>>("cities/?page_size=48", { revalidate: 900 }),
  ]);
  return (
    <>
      <PageHero eyebrow="تقدير نطاق المشروع" title="اطلب عرض سعر مبنيًا على تفاصيل واضحة" description="شاركنا المدينة والحي والمساحة والميزانية التقريبية، وسيراجع الفريق الطلب قبل التواصل معك.">
        <Breadcrumbs items={[{ label: "طلب عرض سعر" }]} />
      </PageHero>
      <section className="content-section">
        <Container className="contact-layout">
          <div><LeadForm endpoint="quote-request" services={services.results.map((item) => item.title)} cities={cities.results.map((item) => item.name)} defaultService={query.service} defaultCity={query.city} /></div>
          <aside className="contact-card">
            <h2>ماذا يحدث بعد الإرسال؟</h2>
            <p>نراجع نوع الخدمة وموقع المشروع ومساحته، ثم نتواصل لتأكيد التفاصيل أو ترتيب معاينة عند الحاجة.</p>
            {site.contact_phone ? <a href={`tel:${site.contact_phone}`}>للاستفسار: {site.contact_phone}</a> : null}
            <p>القيمة النهائية تعتمد على المعاينة والخامات وكميات التنفيذ، لذلك لا يُعد إرسال النموذج التزامًا تعاقديًا.</p>
          </aside>
        </Container>
      </section>
    </>
  );
}
