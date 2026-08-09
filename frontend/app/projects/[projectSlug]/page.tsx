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
import type { ImageData, Project } from "@/types";

async function getProject(slug: string) {
  return detailApi<Project>(`projects/${encodeURIComponent(slug)}/`, 900, ["projects", `project-${slug}`]);
}

export async function generateMetadata({ params }: { params: Promise<{ projectSlug: string }> }): Promise<Metadata> {
  const { projectSlug } = await params;
  return buildMetadata((await getProject(projectSlug)).seo);
}

export default async function ProjectDetailPage({ params }: { params: Promise<{ projectSlug: string }> }) {
  const { projectSlug } = await params;
  const project = await getProject(projectSlug);
  const description = project.seo.description || plainText(project.description);
  const images = [project.image, ...project.gallery.map((item) => item.image)].filter((image): image is ImageData => image !== null);
  const actualLocation = project.city ? `${project.city.name}${project.district ? ` · ${project.district.name}` : ""}` : "";
  const coverageLocation = project.coverage_city ? `${project.coverage_city.name}${project.coverage_district ? ` · ${project.coverage_district.name}` : ""}` : "";
  const schema = {
    "@context": "https://schema.org",
    "@type": project.record_type === "local_solution" ? "CreativeWork" : "VisualArtwork",
    name: project.title,
    description,
    url: `${SITE_URL}${project.url}`,
    image: images.map((image) => image.url),
  };
  const imageSchemas = images.map((image) => ({ "@context": "https://schema.org", "@type": "ImageObject", contentUrl: image.url, caption: image.alt || project.title, width: image.width || undefined, height: image.height || undefined }));

  return (
    <>
      <PageHero eyebrow={project.record_type === "local_solution" ? "نموذج حل ضمن نطاق الخدمة" : project.category_label} title={project.title} description={description}>
        <Breadcrumbs items={[{ label: "المشاريع", href: "/projects/" }, { label: project.title }]} />
        <div className="detail-facts"><span><strong>{project.category_label}</strong> التصنيف</span><span><strong>{project.gallery.length.toLocaleString("ar-SA")}</strong> صور إضافية</span><span><strong>{actualLocation ? "موثق" : "نطاق خدمة"}</strong> الموقع</span></div>
      </PageHero>

      <section className="content-section detail-section detail-section--project">
        <Container>
          {project.image ? <ResponsiveImage image={project.image} className="detail-media detail-media--hero" priority sizes="100vw" /> : null}
          <div className="detail-layout detail-layout--editorial">
            <article className="detail-article">
              <p className="detail-kicker">المعرض / {project.category_label}</p>
              <p className="detail-deck">{description}</p>
              {project.record_type === "local_solution" ? <aside className="transparency-note"><strong>توضيح مهم</strong><p>هذا نموذج بصري لخدمة ضمن نطاق المنطقة الموضح، وليس ادعاءً بأن الصورة نُفذت في هذا الحي بعينه.</p></aside> : null}
              <RichText html={project.description} />
              {project.gallery.length ? <section className="detail-block"><h2>تفاصيل بصرية إضافية</h2><div className="project-gallery-editorial">{project.gallery.map((item, index) => item.image ? <figure key={item.id}><ResponsiveImage image={item.image} sizes="(max-width: 720px) 100vw, 50vw" /><figcaption><span>{String(index + 1).padStart(2, "0")}</span>{item.title || project.title}</figcaption></figure> : null)}</div></section> : null}
            </article>
            <aside className="detail-sidebar detail-sidebar--editorial">
              <p className="eyebrow">بيانات العرض</p>
              <h2>{project.title}</h2>
              <p><strong>التصنيف</strong><span>{project.category_label}</span></p>
              {actualLocation ? <p><strong>موقع التنفيذ الموثق</strong><span>{actualLocation}</span></p> : null}
              {!actualLocation && coverageLocation ? <p><strong>نطاق الخدمة المرتبط</strong><span>{coverageLocation}</span></p> : null}
              {!actualLocation && !coverageLocation ? <p><strong>الموقع</strong><span>غير منشور لهذا السجل</span></p> : null}
              {project.city ? <Link className="text-link" href={`/${project.city.slug}/`}>صفحة {project.city.name}</Link> : !project.city && project.coverage_city ? <Link className="text-link" href={`/${project.coverage_city.slug}/`}>خدمات {project.coverage_city.name}</Link> : null}
              <Link className="button" href="/quote-request/">اطلب معاينة لمشروع مشابه</Link>
            </aside>
          </div>
        </Container>
      </section>
      <CallToAction />
      <JsonLd data={[schema, ...imageSchemas]} />
    </>
  );
}
