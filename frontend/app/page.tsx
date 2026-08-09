import type { Metadata } from "next";
import Link from "next/link";
import { cache } from "react";

import { ResponsiveImage } from "@/components/content/ResponsiveImage";
import { CoverageChart } from "@/components/data/CoverageChart";
import { CinematicVideo } from "@/components/media/CinematicVideo";
import { JsonLd } from "@/components/seo/JsonLd";
import { Container } from "@/components/ui/Container";
import { djangoApi } from "@/lib/django-api";
import { enforceHomeMediaBudget } from "@/lib/media-budget";
import { buildMetadata, SITE_URL } from "@/lib/metadata";
import type { HomePageData, HomeSection } from "@/types";

export const revalidate = 60;

const getHome = cache(() => djangoApi<HomePageData>("home/", { revalidate: 60, tags: ["home"] }));

function lines(value: string, fallback: string) {
  return (value || fallback).split(/\r?\n/).map((item) => item.trim()).filter(Boolean);
}

function TitleLines({ value, fallback }: { value: string | undefined; fallback: string }) {
  return <>{lines(value || "", fallback).map((line, index) => <span key={`${line}-${index}`}>{line}</span>)}</>;
}

function SectionLabel({ section, fallback }: { section?: HomeSection; fallback: string }) {
  return <div className={`cinematic-label${section?.theme === "paper" ? " cinematic-label--dark" : ""}`} data-reveal-line><span>{section?.eyebrow || fallback}</span><i /></div>;
}

function sectionTheme(section: HomeSection | undefined, fallback: "dark" | "paper") {
  const resolved = section?.theme === "paper" ? "paper" : section?.theme === "dark" ? "dark" : fallback;
  return `cinematic-${resolved}`;
}

function Cta({ label, url, light = false, dark = false }: { label: string; url: string; light?: boolean; dark?: boolean }) {
  if (!label || !url) return null;
  return <Link className={`cinematic-button${light ? " cinematic-button--light" : ""}${dark ? " cinematic-button--dark" : ""}`} href={url}>{label}<b aria-hidden="true">↗</b></Link>;
}

export async function generateMetadata(): Promise<Metadata> {
  return buildMetadata((await getHome()).seo);
}

export default async function HomePage() {
  const home = enforceHomeMediaBudget(await getHome());
  const sectionMap = new Map((home.sections || []).filter((section) => section.is_visible).map((section) => [section.key, section]));
  const section = (key: string) => sectionMap.get(key);
  const heroTitle = lines(home.hero.title, "تنسيق حدائق\nولاندسكيب\nيصنع الفرق.");
  const featuredProject = home.projects[0];
  const counts = home.counts || {
    services: home.services.length,
    projects: home.projects.length,
    portfolio_projects: home.projects.length,
    local_solutions: 0,
    cities: home.cities.length,
    districts: home.cities.reduce((total, city) => total + city.districts.length, 0),
  };
  const coverage = home.cities.slice(0, 7).map((city) => ({
    name: city.name,
    count: city.district_count || city.districts.length,
  }));
  const manifesto = section("manifesto");
  const stories = section("stories");
  const gallery = section("gallery");
  const services = section("services");
  const process = section("process");
  const feature = section("feature");
  const coverageSection = section("coverage");
  const projects = section("projects");
  const testimonials = section("testimonials");
  const insights = section("insights");
  const faq = section("faq");
  const closing = section("closing");
  const marquee = section("marquee");
  const marqueeItems = (marquee?.supporting_text || home.site.service_highlights.join("\n"))
    .split(/\r?\n/).map((item) => item.trim()).filter(Boolean);
  const trustItems = lines(section("hero")?.supporting_text || "", "تصميم مدروس للمناخ\nمواد حقيقية من الميدان\nتنفيذ ومتابعة واضحة\nتغطية محلية واسعة").slice(0, 4);

  const websiteSchema = {
    "@context": "https://schema.org",
    "@type": "WebSite",
    name: home.site.site_name,
    url: SITE_URL,
    inLanguage: "ar-SA",
  };
  const serviceListSchema = {
    "@context": "https://schema.org",
    "@type": "ItemList",
    name: "خدمات تنسيق الحدائق واللاندسكيب",
    itemListElement: home.services.slice(0, 8).map((item, index) => ({
      "@type": "ListItem",
      position: index + 1,
      name: item.title,
      url: new URL(item.url, SITE_URL).toString(),
    })),
  };
  const faqSchema = faq?.items.length ? {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: faq.items.map((item) => ({
      "@type": "Question",
      name: item.title,
      acceptedAnswer: { "@type": "Answer", text: item.description },
    })),
  } : null;

  return (
    <div className="cinematic-home">
      <section className="cinematic-hero" aria-labelledby="home-title">
        <div className="cinematic-hero__media">
          {home.hero.video ? (
            <CinematicVideo
              src={home.hero.video}
              mobileSrc={home.hero.mobile_video || undefined}
              poster={home.hero.poster || home.hero.image?.url || ""}
              priority
            />
          ) : home.hero.image ? <ResponsiveImage image={home.hero.image} sizes="100vw" priority /> : null}
        </div>
        <div className="cinematic-hero__veil" style={{ opacity: Math.max(.2, Math.min(.95, home.hero.overlay_opacity / 100)) }} />
        <div className="cinematic-hero__grid" aria-hidden="true"><i /><i /><i /></div>
        <Container className="cinematic-hero__content">
          <div className="cinematic-hero__kicker" data-reveal-line>
            <span>{home.hero.eyebrow || home.site.site_name}</span>
            <span>{home.hero.kicker || "PALMS · LANDSCAPE · SAUDI ARABIA"}</span>
          </div>
          <h1 id="home-title" data-reveal>
            {heroTitle.map((title, index) => <span className={index === heroTitle.length - 1 ? "cinematic-hero__accent" : undefined} key={`${title}-${index}`}>{title}</span>)}
          </h1>
          <div className="cinematic-hero__bottom" data-reveal>
            <p>{home.hero.description || home.site.tagline}</p>
            <div className="cinematic-actions">
              <Cta label={home.hero.primary_cta.label} url={home.hero.primary_cta.url} light />
              <Cta label={home.hero.secondary_cta.label} url={home.hero.secondary_cta.url} />
            </div>
          </div>
          <dl className="cinematic-hero__stats" aria-label="أرقام نطاق الخدمة">
            <div><dt>خدمة متخصصة</dt><dd>{counts.services.toLocaleString("ar-SA")}</dd></div>
            <div><dt>مدينة نخدمها</dt><dd>{counts.cities.toLocaleString("ar-SA")}</dd></div>
            <div><dt>حيًا ضمن النطاق</dt><dd>{counts.districts.toLocaleString("ar-SA")}</dd></div>
          </dl>
        </Container>
        <span className="cinematic-hero__scroll" aria-hidden="true">مرّر للاكتشاف<i /></span>
      </section>

      <div className="trust-ribbon cinematic-paper" aria-label="مجالات الخبرة">
        <Container>
          {trustItems.map((item, index) => <span key={item}>{item}{index < trustItems.length - 1 ? <i /> : null}</span>)}
        </Container>
      </div>

      {manifesto ? (
        <section className={`manifesto ${sectionTheme(manifesto, "dark")}`}>
          <Container>
            <SectionLabel section={manifesto} fallback="من نحن" />
            <div className="manifesto__grid">
              <h2 data-reveal><TitleLines value={manifesto.title} fallback="النخلة مو تفصيل.\nهي توقيع المكان." /></h2>
              <div data-reveal>
                <p>{manifesto.description}</p>
                {manifesto.supporting_text ? <p className="section-supporting">{manifesto.supporting_text}</p> : null}
                <Cta label={manifesto.primary_cta.label} url={manifesto.primary_cta.url} />
              </div>
            </div>
            <p className="manifesto__ghost" aria-hidden="true">NAKHEEL</p>
          </Container>
        </section>
      ) : null}

      {stories?.items.some((item) => item.video) ? (
        <section className={`story-section ${sectionTheme(stories, "paper")}`}>
          <Container>
            <SectionLabel section={stories} fallback="قصص من الميدان" />
            <div className="story-section__heading">
              <h2 data-reveal><TitleLines value={stories.title} fallback="التنفيذ\nيتكلم." /></h2>
              <p data-reveal>{stories.description}</p>
            </div>
            <div className="video-stories">
              {stories.items.filter((item) => item.video).slice(0, 6).map((item, index) => (
                <article className={`video-story video-story--${index + 1}`} key={item.id} data-reveal>
                  <div className="video-story__media">
                    <CinematicVideo src={item.video} mobileSrc={item.mobile_video || undefined} poster={item.poster || ""} />
                    <span>{item.label.split("·")[0].trim() || String(index + 1).padStart(2, "0")}</span>
                  </div>
                  <p>{item.label.split("·").slice(1).join("·").trim() || item.label}</p>
                  <h3>{item.title}</h3>
                  {item.description ? <small>{item.description}</small> : null}
                </article>
              ))}
            </div>
          </Container>
        </section>
      ) : null}

      {gallery?.items.some((item) => item.image) ? (
        <section className={`owner-gallery ${sectionTheme(gallery, "paper")}`}>
          <Container>
            <SectionLabel section={gallery} fallback="تفاصيل من أعمالنا" />
            <div className="owner-gallery__heading">
              <h2 data-reveal><TitleLines value={gallery.title} fallback="من الزراعة\nإلى المشهد المكتمل." /></h2>
              <p data-reveal>{gallery.description}</p>
            </div>
            <div className="owner-gallery__grid">
              {gallery.items.filter((item) => item.image).slice(0, 9).map((item, index) => (
                <figure className={`owner-shot owner-shot--${index + 1}`} key={item.id} data-reveal>
                  {item.image ? <ResponsiveImage image={item.image} sizes="(max-width: 700px) 78vw, 32vw" /> : null}
                  <figcaption><span>{item.label || String(index + 1).padStart(2, "0")}</span>{item.title}</figcaption>
                </figure>
              ))}
            </div>
          </Container>
        </section>
      ) : null}

      {services ? (
        <section className={`services-editorial ${sectionTheme(services, "dark")}`}>
          <Container>
            <SectionLabel section={services} fallback="خدماتنا" />
            <div className="services-editorial__intro">
              <h2 data-reveal><TitleLines value={services.title} fallback="خبرة تبدأ\nمن الأرض." /></h2>
              <p data-reveal>{services.description}</p>
            </div>
            <div className="service-index">
              {home.services.slice(0, 7).map((item, index) => (
                <Link href={item.url} className="service-index__item" key={item.id} data-reveal>
                  <span>{String(index + 1).padStart(2, "0")}</span>
                  <h3>{item.short_title || item.title}</h3>
                  <p>{item.description}</p>
                  <b aria-hidden="true">↗</b>
                </Link>
              ))}
            </div>
            <Cta label={services.primary_cta.label} url={services.primary_cta.url} />
          </Container>
        </section>
      ) : null}

      {process?.items.length ? (
        <section className={`process-editorial ${sectionTheme(process, "paper")}`}>
          <Container>
            <SectionLabel section={process} fallback="منهج التنفيذ" />
            <div className="process-editorial__heading">
              <h2 data-reveal><TitleLines value={process.title} fallback="من المعاينة\nإلى مشهد مكتمل." /></h2>
              <div data-reveal><p>{process.description}</p><Cta label={process.primary_cta.label} url={process.primary_cta.url} dark /></div>
            </div>
            <ol className="process-editorial__grid">
              {process.items.slice(0, 6).map((item, index) => (
                <li key={item.id} data-reveal>
                  <span>{item.label || String(index + 1).padStart(2, "0")}</span>
                  <h3>{item.title}</h3>
                  <p>{item.description}</p>
                </li>
              ))}
            </ol>
          </Container>
        </section>
      ) : null}

      {featuredProject && feature ? (
        <section className="featured-scene">
          {feature.media.video ? <CinematicVideo src={feature.media.video} mobileSrc={feature.media.mobile_video || undefined} poster={feature.media.poster || ""} />
            : feature.media.image ? <ResponsiveImage image={feature.media.image} sizes="100vw" priority />
              : featuredProject.image ? <ResponsiveImage image={featuredProject.image} sizes="100vw" priority /> : null}
          <div className="featured-scene__veil" />
          <Container className="featured-scene__copy" data-reveal>
            <SectionLabel section={feature} fallback="مشهد مختار" />
            <p>{featuredProject.category_label}</p>
            <h2><TitleLines value={feature.title} fallback="مشروع يختصر\nجودة التنفيذ." /></h2>
            <h3>{featuredProject.title}</h3>
            <Cta label={feature.primary_cta.label || "تفاصيل العمل"} url={feature.primary_cta.url || featuredProject.url} light />
          </Container>
        </section>
      ) : null}

      {coverageSection ? (
        <section className={`coverage-section ${sectionTheme(coverageSection, "paper")}`}>
          <Container>
            <SectionLabel section={coverageSection} fallback="نطاق التغطية" />
            <div className="coverage-section__grid">
              <div>
                <h2 data-reveal><TitleLines value={coverageSection.title} fallback="معرفة محلية.\nعلى امتداد المملكة." /></h2>
                <p data-reveal>{coverageSection.description}</p>
                <Cta label={coverageSection.primary_cta.label} url={coverageSection.primary_cta.url} dark />
              </div>
              <div data-reveal><CoverageChart data={coverage} /></div>
            </div>
            <div className="city-lineup">
              {home.cities.slice(0, 8).map((city, index) => (
                <Link href={city.url} key={city.id} data-reveal>
                  <span>{String(index + 1).padStart(2, "0")}</span>
                  <strong>{city.name}</strong>
                  <small>{(city.district_count || city.districts.length).toLocaleString("ar-SA")} حي</small>
                  <b aria-hidden="true">↗</b>
                </Link>
              ))}
            </div>
          </Container>
        </section>
      ) : null}

      {projects && home.projects.length > 1 ? (
        <section className={`project-journal ${sectionTheme(projects, "dark")}`}>
          <Container>
            <SectionLabel section={projects} fallback="معرض الأعمال" />
            <div className="project-journal__heading">
              <h2 data-reveal><TitleLines value={projects.title} fallback="تفاصيل تشوفها\nقبل ما تختار." /></h2>
              <Cta label={projects.primary_cta.label} url={projects.primary_cta.url} />
            </div>
            <div className="project-journal__grid">
              {home.projects.slice(1, 5).map((item, index) => (
                <Link className={`journal-card journal-card--${index + 1}`} href={item.url} key={item.id} data-reveal>
                  {item.image ? <ResponsiveImage image={item.image} sizes="(max-width: 760px) 100vw, 38vw" /> : null}
                  <span>{item.category_label}</span>
                  <h3>{item.title}</h3>
                </Link>
              ))}
            </div>
          </Container>
        </section>
      ) : null}

      {testimonials && home.testimonials.length ? (
        <section className={`testimonial-editorial ${sectionTheme(testimonials, "paper")}`}>
          <Container>
            <SectionLabel section={testimonials} fallback="تجارب العملاء" />
            <div className="testimonial-editorial__heading">
              <h2 data-reveal><TitleLines value={testimonials.title} fallback="ثقة تُبنى\nفي التفاصيل." /></h2>
              <p data-reveal>{testimonials.description}</p>
            </div>
            <div className="testimonial-editorial__grid">
              {home.testimonials.slice(0, 6).map((item, index) => (
                <article key={item.id} data-reveal>
                  <span>{String(index + 1).padStart(2, "0")}</span>
                  <div className="testimonial-editorial__stars" aria-label={`تقييم ${item.rating} من 5`}>{"★".repeat(Math.max(1, Math.min(5, item.rating)))}</div>
                  <blockquote>{item.review}</blockquote>
                  <footer><strong>{item.name}</strong>{item.city_name ? <small>{item.city_name}</small> : null}</footer>
                </article>
              ))}
            </div>
          </Container>
        </section>
      ) : null}

      {insights && home.articles.length ? (
        <section className={`insights-section ${sectionTheme(insights, "paper")}`}>
          <Container>
            <SectionLabel section={insights} fallback="دليل الخبرة" />
            <div className="insights-section__heading">
              <div><h2 data-reveal><TitleLines value={insights.title} fallback="معرفة تسبق التنفيذ." /></h2>{insights.description ? <p>{insights.description}</p> : null}</div>
              <Cta label={insights.primary_cta.label} url={insights.primary_cta.url} dark />
            </div>
            <div className="insight-list">
              {home.articles.slice(0, 4).map((article, index) => (
                <Link href={article.url} key={article.id} data-reveal>
                  <span>{String(index + 1).padStart(2, "0")}</span>
                  <div>
                    <small>{article.category?.name || "دليل نخيل نجد"} · {article.reading_time_minutes.toLocaleString("ar-SA")} دقائق</small>
                    <h3>{article.title}</h3>
                  </div>
                  {article.image ? <ResponsiveImage image={article.image} sizes="180px" /> : null}
                  <b aria-hidden="true">↗</b>
                </Link>
              ))}
            </div>
          </Container>
        </section>
      ) : null}

      {faq?.items.length ? (
        <section className={`faq-editorial ${sectionTheme(faq, "dark")}`}>
          <Container>
            <SectionLabel section={faq} fallback="أسئلة قبل البداية" />
            <div className="faq-editorial__layout">
              <div>
                <h2 data-reveal><TitleLines value={faq.title} fallback="قرارات أوضح\nلمشروع أفضل." /></h2>
                <p data-reveal>{faq.description}</p>
              </div>
              <div className="faq-editorial__list">
                {faq.items.map((item, index) => (
                  <details key={item.id} data-reveal>
                    <summary><span>{String(index + 1).padStart(2, "0")}</span>{item.title}<b aria-hidden="true">＋</b></summary>
                    <p>{item.description}</p>
                  </details>
                ))}
              </div>
            </div>
          </Container>
        </section>
      ) : null}

      {closing ? (
        <section className="closing-scene">
          {closing.media.video ? <CinematicVideo src={closing.media.video} mobileSrc={closing.media.mobile_video || undefined} poster={closing.media.poster || ""} />
            : closing.media.image ? <ResponsiveImage image={closing.media.image} sizes="100vw" /> : null}
          <div className="closing-scene__veil" style={{ opacity: Math.max(.25, Math.min(.95, closing.media.overlay_opacity / 100)) }} />
          <Container className="closing-scene__content" data-reveal>
            <SectionLabel section={closing} fallback="ابدأ مشروعك" />
            <h2><TitleLines value={closing.title} fallback="خلّ المكان\nيتكلم عنك." /></h2>
            <p>{closing.description}</p>
            <div className="cinematic-actions">
              <Cta label={closing.primary_cta.label} url={closing.primary_cta.url} light />
              <Cta label={closing.secondary_cta.label} url={closing.secondary_cta.url} />
            </div>
          </Container>
        </section>
      ) : null}

      {marqueeItems.length ? (
        <div className="word-marquee cinematic-dark" aria-label={marqueeItems.join("، ")}>
          <div className="word-marquee__track" aria-hidden="true">
            {[...marqueeItems, ...marqueeItems].map((item, index) => <span key={`${item}-${index}`}>{item}<i>✦</i></span>)}
          </div>
        </div>
      ) : null}

      <JsonLd data={[
        websiteSchema,
        { "@context": "https://schema.org", ...home.seo.schema },
        serviceListSchema,
        ...(faqSchema ? [faqSchema] : []),
      ]} />
    </div>
  );
}
