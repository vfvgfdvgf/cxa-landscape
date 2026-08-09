import type { Metadata } from "next";

import { ProjectCard } from "@/components/content/Cards";
import { CallToAction } from "@/components/content/CallToAction";
import { RichText } from "@/components/content/RichText";
import { SeoJsonLd } from "@/components/seo/JsonLd";
import { Breadcrumbs } from "@/components/ui/Breadcrumbs";
import { Container } from "@/components/ui/Container";
import { PageHero } from "@/components/ui/PageHero";
import { EmptyState, Pagination } from "@/components/ui/States";
import { djangoApi, withQuery } from "@/lib/django-api";
import { buildMetadata, staticMetadata } from "@/lib/metadata";
import { getManagedPage, pageNumber } from "@/lib/page-data";
import type { PaginatedResponse, Project } from "@/types";

export async function generateMetadata(): Promise<Metadata> {
  const page = await getManagedPage("portfolio");
  return page
    ? buildMetadata({ ...page.seo, canonical_path: "/projects/" })
    : staticMetadata("مشاريع النخيل واللاندسكيب", "شاهد نماذج من أعمال النخيل والحدائق والري والمساحات الخارجية في مدن المملكة.", "/projects/");
}

export default async function ProjectsPage({
  searchParams,
}: {
  searchParams: Promise<{ page?: string; city?: string }>;
}) {
  const query = await searchParams;
  const current = pageNumber(query.page);
  const [page, data] = await Promise.all([
    getManagedPage("portfolio"),
    djangoApi<PaginatedResponse<Project>>(
      withQuery("projects/", { page: current, city: query.city }),
      { revalidate: 600, tags: ["projects"] },
    ),
  ]);

  return (
    <>
      <PageHero
        eyebrow="معرض الأعمال"
        title={page?.hero_title || page?.title || "أماكن تحولت من فكرة إلى مساحة حية"}
        description={page?.intro_text || "معرض بصري يجمع الأعمال المصورة ونماذج الحلول المحلية مع توضيح موقع التنفيذ عندما يكون موثقًا."}
      >
        <Breadcrumbs items={[{ label: "المشاريع" }]} />
      </PageHero>
      <section className="content-section">
        <Container>
          {page?.body ? <RichText html={page.body} className="listing-intro" /> : null}
          <aside className="transparency-note listing-intro"><strong>كيف تقرأ المعرض؟</strong><p>السجل الذي يحمل «موقع تنفيذ موثق» مرتبط بموقع معروف. أما «نطاق الخدمة» أو «نموذج حل محلي» فهو مرجع بصري مرتبط بالمدينة أو الحي ولا يعني أن الصورة التقطت هناك.</p></aside>
          <div className="grid grid--3">
            {data.results.length ? data.results.map((project, index) => <ProjectCard key={project.id} project={project} priority={index < 3} />) : <EmptyState message="لا توجد مشاريع مطابقة حاليًا." />}
          </div>
          <Pagination current={current} count={data.count} pageSize={12} href={query.city ? `/projects/?city=${encodeURIComponent(query.city)}` : "/projects/"} />
        </Container>
      </section>
      <CallToAction title="مشروعك قد يكون الفصل القادم" />
      <SeoJsonLd schema={page?.seo.schema} />
    </>
  );
}
