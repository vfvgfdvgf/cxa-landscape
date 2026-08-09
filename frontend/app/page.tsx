import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { cache } from "react";

import { ResponsiveImage } from "@/components/content/ResponsiveImage";
import { CoverageChart } from "@/components/data/CoverageChart";
import { CinematicVideo } from "@/components/media/CinematicVideo";
import { JsonLd } from "@/components/seo/JsonLd";
import { Container } from "@/components/ui/Container";
import { djangoApi } from "@/lib/django-api";
import { buildMetadata, SITE_URL } from "@/lib/metadata";
import type { HomePageData } from "@/types";

export const revalidate = 900;

const getHome = cache(() => djangoApi<HomePageData>("home/", { revalidate: 900, tags: ["home"] }));

const videoStories = [
  {
    src: "/videos/story-night.mp4",
    poster: "/video-posters/story-night.webp",
    index: "01",
    label: "المشهد بعد التنفيذ",
    title: "نخيل يصنع إيقاع المكان",
  },
  {
    src: "/videos/story-transplant.mp4",
    poster: "/video-posters/story-transplant.webp",
    index: "02",
    label: "نقل وزراعة",
    title: "تنفيذ محسوب من الرفع إلى التثبيت",
  },
  {
    src: "/videos/story-care.mp4",
    poster: "/video-posters/story-care.webp",
    index: "03",
    label: "العناية",
    title: "تفاصيل تحافظ على الأثر",
  },
];

const ownerGallery = [
  { src: "/editorial/gardens/palm-entry.webp", alt: "نخيل مزروع عند مدخل مشروع سكني", label: "نخيل ومداخل" },
  { src: "/editorial/gardens/lawn-park.webp", alt: "مسطح أخضر وممرات ضمن حديقة", label: "مسطحات خضراء" },
  { src: "/editorial/gardens/palm-lawn.webp", alt: "مجموعة نخيل وسط مسطح أخضر", label: "تكوين نباتي" },
  { src: "/editorial/gardens/garden-lighting.webp", alt: "حديقة نخيل وإنارة أرضية وقت الغروب", label: "إنارة خارجية" },
  { src: "/editorial/gardens/garden-water.webp", alt: "حديقة خضراء مع عنصر مائي ونباتات", label: "حدائق وعناصر مائية" },
  { src: "/editorial/gardens/palm-nursery.webp", alt: "نخيل واشنطونيا داخل المشتل", label: "اختيار من المشتل" },
];

export async function generateMetadata(): Promise<Metadata> {
  return buildMetadata((await getHome()).seo);
}

export default async function HomePage() {
  const home = await getHome();
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
  const marqueeItems = home.site.service_highlights.length
    ? home.site.service_highlights
    : ["النخيل", "اللاندسكيب", "شبكات الري", "الصيانة", "المساحات الخارجية"];
  const websiteSchema = {
    "@context": "https://schema.org",
    "@type": "WebSite",
    name: home.site.site_name,
    url: SITE_URL,
    inLanguage: "ar-SA",
  };

  return (
    <div className="cinematic-home">
      <section className="cinematic-hero" aria-labelledby="home-title">
        <div className="cinematic-hero__media">
          <CinematicVideo
            src="/videos/hero-triptych.mp4"
            mobileSrc="/videos/hero-mobile.mp4"
            poster="/video-posters/hero-triptych.webp"
            priority
          />
        </div>
        <div className="cinematic-hero__veil" />
        <div className="cinematic-hero__grid" aria-hidden="true"><i /><i /><i /></div>
        <Container className="cinematic-hero__content">
          <div className="cinematic-hero__kicker" data-reveal-line>
            <span>نخيل نجد</span>
            <span>PALMS · LANDSCAPE · SAUDI ARABIA</span>
          </div>
          <h1 id="home-title" data-reveal>
            <span>نزرع</span>
            <span>مشهدًا</span>
            <span className="cinematic-hero__accent">يبقى.</span>
          </h1>
          <div className="cinematic-hero__bottom" data-reveal>
            <p>{home.hero.description || home.site.tagline}</p>
            <div className="cinematic-actions">
              <Link className="cinematic-button cinematic-button--light" href={home.hero.primary_cta.url}>اطلب معاينة <b>↗</b></Link>
              <Link className="cinematic-button" href="/projects/">شاهد الأعمال <b>←</b></Link>
            </div>
          </div>
          <dl className="cinematic-hero__stats" aria-label="أرقام التغطية">
            <div><dt>خدمة متخصصة</dt><dd>{counts.services.toLocaleString("ar-SA")}</dd></div>
            <div><dt>مدينة نخدمها</dt><dd>{counts.cities.toLocaleString("ar-SA")}</dd></div>
            <div><dt>حيًا ضمن النطاق</dt><dd>{counts.districts.toLocaleString("ar-SA")}</dd></div>
          </dl>
        </Container>
        <span className="cinematic-hero__scroll" aria-hidden="true">مرّر للاكتشاف <i /></span>
      </section>

      <section className="manifesto cinematic-dark">
        <Container>
          <div className="cinematic-label" data-reveal-line><span>من نحن</span><i /></div>
          <div className="manifesto__grid">
            <h2 data-reveal>النخلة مو تفصيل.<br />هي توقيع المكان.</h2>
            <div data-reveal>
              <p>نحوّل الأرض إلى تجربة حية؛ من قراءة الموقع واختيار النخيل، إلى الزراعة والري والعناية التي تحفظ النتيجة.</p>
              <Link className="cinematic-button" href="/about/">اكتشف قصتنا <b>←</b></Link>
            </div>
          </div>
          <p className="manifesto__ghost" aria-hidden="true">NAKHEEL</p>
        </Container>
      </section>

      <section className="story-section cinematic-paper">
        <Container>
          <div className="cinematic-label cinematic-label--dark" data-reveal-line><span>قصص من الميدان</span><i /></div>
          <div className="story-section__heading">
            <h2 data-reveal>نخلي العمل<br />يتكلم.</h2>
            <p data-reveal>لقطات حقيقية من المواد اللي شاركتها معنا؛ رتبناها حسب الجودة والسياق عشان تكون جزءًا من القصة، مو مجرد خلفية.</p>
          </div>
          <div className="video-stories">
            {videoStories.map((story, index) => (
              <article className={`video-story video-story--${index + 1}`} key={story.src} data-reveal>
                <div className="video-story__media">
                  <CinematicVideo src={story.src} poster={story.poster} />
                  <span>{story.index}</span>
                </div>
                <p>{story.label}</p>
                <h3>{story.title}</h3>
              </article>
            ))}
          </div>
        </Container>
      </section>

      <section className="owner-gallery cinematic-paper">
        <Container>
          <div className="cinematic-label cinematic-label--dark" data-reveal-line><span>صور من المواد الأصلية</span><i /></div>
          <div className="owner-gallery__heading">
            <h2 data-reveal>من الزراعة<br />إلى المشهد المكتمل.</h2>
            <p data-reveal>اختيرت الصور الأعلى دقة للمشاهد النهائية، وفُصلت صور التركيب والنقل في مجلدها الخاص حتى يبقى استخدام كل مادة واضح.</p>
          </div>
          <div className="owner-gallery__grid">
            {ownerGallery.map((item, index) => (
              <figure className={`owner-shot owner-shot--${index + 1}`} key={item.src} data-reveal>
                <Image src={item.src} width={960} height={1280} sizes="(max-width: 700px) 78vw, 32vw" alt={item.alt} />
                <figcaption><span>{String(index + 1).padStart(2, "0")}</span>{item.label}</figcaption>
              </figure>
            ))}
          </div>
        </Container>
      </section>

      <section className="services-editorial cinematic-dark">
        <Container>
          <div className="cinematic-label" data-reveal-line><span>ما نقدمه</span><i /></div>
          <div className="services-editorial__intro">
            <h2 data-reveal>خبرة تبدأ<br />من الأرض.</h2>
            <p data-reveal>كل خدمة مرتبطة بطبيعة الموقع والمناخ والاستخدام؛ نطاق واضح قبل المعاينة وتنفيذ يعرف كيف يعيش مع المكان.</p>
          </div>
          <div className="service-index">
            {home.services.slice(0, 6).map((service, index) => (
              <Link href={service.url} className="service-index__item" key={service.id} data-reveal>
                <span>{String(index + 1).padStart(2, "0")}</span>
                <h3>{service.short_title || service.title}</h3>
                <p>{service.description}</p>
                <b aria-hidden="true">↗</b>
              </Link>
            ))}
          </div>
          <Link className="cinematic-button services-editorial__all" href="/services/">جميع الخدمات <b>←</b></Link>
        </Container>
      </section>

      {featuredProject ? (
        <section className="featured-scene">
          {featuredProject.image ? <ResponsiveImage image={featuredProject.image} sizes="100vw" priority /> : null}
          <div className="featured-scene__veil" />
          <Container className="featured-scene__copy" data-reveal>
            <div className="cinematic-label"><span>مشهد مختار</span><i /></div>
            <p>{featuredProject.category_label}</p>
            <h2>{featuredProject.title}</h2>
            <Link className="cinematic-button cinematic-button--light" href={featuredProject.url}>تفاصيل العمل <b>↗</b></Link>
          </Container>
        </section>
      ) : null}

      <section className="coverage-section cinematic-paper">
        <Container>
          <div className="cinematic-label cinematic-label--dark" data-reveal-line><span>نطاق التغطية</span><i /></div>
          <div className="coverage-section__grid">
            <div>
              <h2 data-reveal>معرفة محلية.<br />على امتداد المملكة.</h2>
              <p data-reveal>نربط الخدمة بالمدينة والحي عشان توصل للمعلومة الأقرب لموقعك، وتعرف الخيارات قبل ما تبدأ المحادثة.</p>
              <Link className="cinematic-button cinematic-button--dark" href="/cities/">استكشف المدن <b>←</b></Link>
            </div>
            <div data-reveal>
              <CoverageChart data={coverage} />
            </div>
          </div>
          <div className="city-lineup">
            {home.cities.slice(0, 8).map((city, index) => (
              <Link href={city.url} key={city.id} data-reveal>
                <span>{String(index + 1).padStart(2, "0")}</span>
                <strong>{city.name}</strong>
                <small>{(city.district_count || city.districts.length).toLocaleString("ar-SA")} حي</small>
                <b>↗</b>
              </Link>
            ))}
          </div>
        </Container>
      </section>

      {home.projects.length > 1 ? (
        <section className="project-journal cinematic-dark">
          <Container>
            <div className="cinematic-label" data-reveal-line><span>معرض الأعمال</span><i /></div>
            <div className="project-journal__heading">
              <h2 data-reveal>تفاصيل تشوفها<br />قبل ما تختار.</h2>
              <Link className="cinematic-button" href="/projects/">كامل المعرض <b>←</b></Link>
            </div>
            <div className="project-journal__grid">
              {home.projects.slice(1, 4).map((project, index) => (
                <Link className={`journal-card journal-card--${index + 1}`} href={project.url} key={project.id} data-reveal>
                  {project.image ? <ResponsiveImage image={project.image} sizes="(max-width: 760px) 100vw, 38vw" /> : null}
                  <span>{project.category_label}</span>
                  <h3>{project.title}</h3>
                </Link>
              ))}
            </div>
          </Container>
        </section>
      ) : null}

      {home.articles.length ? (
        <section className="insights-section cinematic-paper">
          <Container>
            <div className="cinematic-label cinematic-label--dark" data-reveal-line><span>دليل الخبرة</span><i /></div>
            <div className="insights-section__heading">
              <h2 data-reveal>معرفة تسبق التنفيذ.</h2>
              <Link className="cinematic-button cinematic-button--dark" href="/blog/">كل المقالات <b>←</b></Link>
            </div>
            <div className="insight-list">
              {home.articles.slice(0, 3).map((article, index) => (
                <Link href={article.url} key={article.id} data-reveal>
                  <span>{String(index + 1).padStart(2, "0")}</span>
                  <div>
                    <small>{article.category?.name || "دليل نخيل نجد"} · {article.reading_time_minutes.toLocaleString("ar-SA")} دقائق</small>
                    <h3>{article.title}</h3>
                  </div>
                  {article.image ? <ResponsiveImage image={article.image} sizes="180px" /> : null}
                  <b>↗</b>
                </Link>
              ))}
            </div>
          </Container>
        </section>
      ) : null}

      <section className="closing-scene">
        <CinematicVideo src="/videos/story-finished.mp4" poster="/video-posters/story-finished.webp" />
        <div className="closing-scene__veil" />
        <Container className="closing-scene__content" data-reveal>
          <div className="cinematic-label"><span>ابدأ مشروعك</span><i /></div>
          <h2>خلّ المكان<br />يتكلم عنك.</h2>
          <p>أرسل موقع المشروع واحتياجك، ونرتب معك المعاينة والخطوة الأنسب بوضوح.</p>
          <div className="cinematic-actions">
            <Link className="cinematic-button cinematic-button--light" href="/quote-request/">اطلب عرض سعر <b>↗</b></Link>
            <Link className="cinematic-button" href="/contact/">تواصل معنا <b>←</b></Link>
          </div>
        </Container>
      </section>

      <div className="word-marquee cinematic-dark" aria-label={marqueeItems.join("، ")}>
        <div className="word-marquee__track" aria-hidden="true">
          {[...marqueeItems, ...marqueeItems].map((item, index) => <span key={`${item}-${index}`}>{item}<i>✦</i></span>)}
        </div>
      </div>

      <JsonLd data={[websiteSchema, { "@context": "https://schema.org", ...home.seo.schema }]} />
    </div>
  );
}
