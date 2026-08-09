import type { Metadata } from "next";

import { CallToAction } from "@/components/content/CallToAction";
import { RichText } from "@/components/content/RichText";
import { Breadcrumbs } from "@/components/ui/Breadcrumbs";
import { Container } from "@/components/ui/Container";
import { PageHero } from "@/components/ui/PageHero";
import { optionalApi } from "@/lib/django-api";
import { buildMetadata, staticMetadata } from "@/lib/metadata";
import type { ManagedPage, SiteSettings } from "@/types";

async function getAbout() {
  return Promise.all([
    optionalApi<ManagedPage>("pages/about/", { revalidate: 300, tags: ["pages"] }),
    optionalApi<SiteSettings>("site/", { revalidate: 300, tags: ["site"] }),
  ]);
}

export async function generateMetadata(): Promise<Metadata> {
  const [page, site] = await getAbout();
  return page
    ? buildMetadata({ ...page.seo, canonical_path: "/about/" })
    : staticMetadata("من نحن", site?.seo_defaults.description || "تعرّف على نهج نخيل نجد في تصميم وتنفيذ المساحات الخارجية.", "/about/");
}

export default async function AboutPage() {
  const [page, site] = await getAbout();
  const title = page?.hero_title || page?.title || `عن ${site?.site_name || "نخيل نجد"}`;
  const intro = page?.intro_text || site?.tagline || "خبرة تربط جمال الفكرة بجودة التنفيذ واستدامة العناية.";

  return (
    <>
      <PageHero eyebrow="من نحن" title={title} description={intro}>
        <Breadcrumbs items={[{ label: "من نحن" }]} />
      </PageHero>
      <section className="content-section">
        <Container className="detail-layout">
          <article>
            {page?.body ? <RichText html={page.body} /> : (
              <>
                <p className="eyebrow">فلسفتنا</p>
                <h2>نصنع مساحات تنتمي إلى مكانها</h2>
                <p>{intro}</p>
                <p>نوازن بين طبيعة التربة والمناخ، طريقة استخدام المساحة، اختيار النباتات والخامات وكفاءة الري لنصل إلى نتيجة جميلة وعملية تدوم.</p>
                <p>تبدأ علاقتنا بالمشروع بالاستماع والمعاينة، وتستمر بالتنسيق الواضح والعناية بأدق تفاصيل التنفيذ.</p>
              </>
            )}
          </article>
          <aside className="detail-sidebar">
            <p className="eyebrow">نخدمك حيث أنت</p>
            <h2>{site?.site_name || "نخيل نجد"}</h2>
            <p>{site?.address || "نصل إلى مدن وأحياء متعددة ضمن نطاق تغطيتنا."}</p>
            {site?.contact_phone ? <a className="button" href={`tel:${site.contact_phone}`}>تحدث معنا</a> : null}
          </aside>
        </Container>
      </section>
      <CallToAction />
    </>
  );
}
