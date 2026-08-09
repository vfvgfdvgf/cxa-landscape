import Link from "next/link";

import { ResponsiveImage } from "@/components/content/ResponsiveImage";
import { plainText } from "@/lib/text";
import type { Article, City, DistrictListItem, HomeCity, Project, Service, Testimonial } from "@/types";

export function ServiceCard({ service, priority = false }: { service: Service; priority?: boolean }) {
  return (
    <article className="content-card">
      {service.image ? <Link className="content-card__media" href={service.url}><ResponsiveImage image={service.image} sizes="(max-width: 720px) 100vw, 33vw" priority={priority} /></Link> : null}
      <div className="content-card__body">
        <div className="content-card__meta">{service.category ? <span>{service.category.name}</span> : null}{service.primary_city ? <span>{service.primary_city.name}</span> : null}</div>
        <h2><Link href={service.url}>{service.title}</Link></h2>
        <p>{plainText(service.description)}</p>
        <Link className="text-link" href={service.url}>تفاصيل {service.short_title || service.title}</Link>
      </div>
    </article>
  );
}

export function ProjectCard({ project, priority = false }: { project: Project; priority?: boolean }) {
  const actualLocation = project.city
    ? `${project.city.name}${project.district ? ` · ${project.district.name}` : ""}`
    : "";
  const coverageLocation = project.coverage_city
    ? `${project.coverage_city.name}${project.coverage_district ? ` · ${project.coverage_district.name}` : ""}`
    : "";
  return (
    <article className="content-card">
      {project.image ? <Link className="content-card__media" href={project.url}><ResponsiveImage image={project.image} sizes="(max-width: 720px) 100vw, 33vw" priority={priority} /></Link> : null}
      <div className="content-card__body">
        <div className="content-card__meta">
          <span>{project.category_label}</span>
          {project.record_type === "local_solution" ? <span className="content-card__badge">نموذج حل محلي</span> : null}
        </div>
        {actualLocation ? <p className="project-location"><strong>موقع تنفيذ موثق</strong> · {actualLocation}</p> : coverageLocation ? <p className="project-location"><strong>نطاق الخدمة</strong> · {coverageLocation}</p> : null}
        <h2><Link href={project.url}>{project.title}</Link></h2>
        <p>{plainText(project.description)}</p>
        <Link className="text-link" href={project.url}>{project.record_type === "local_solution" ? "استعرض نموذج الحل" : "استعرض العمل"}</Link>
      </div>
    </article>
  );
}

export function CityCard({ city }: { city: City | HomeCity }) {
  const districtCount = "district_count" in city ? city.district_count : city.districts.length;
  return (
    <article className="content-card city-card" style={{ background: `linear-gradient(145deg, ${city.secondary_color || "var(--brand)"}, ${city.primary_color || "var(--brand-dark)"})` }}>
      <div><p className="city-card__count">{districtCount} حي منشور</p><h2><Link href={city.url}>{city.name}</Link></h2><p>{plainText(city.short_description || ("content" in city ? city.content : ""))}</p></div>
      <Link className="text-link" href={city.url}>خدمات {city.name}</Link>
    </article>
  );
}

export function DistrictCard({ district }: { district: DistrictListItem }) {
  return (
    <article className="district-card">
      <div className="district-card__index" aria-hidden="true">{String(district.sort_order || district.id).padStart(2, "0")}</div>
      <div>
        <p className="eyebrow">{district.city.name}</p>
        <h2><Link href={district.url}>حي {district.name}</Link></h2>
        <p>خدمات وأعمال ونماذج محلية ومحتوى مرتبط بالحي.</p>
      </div>
      <Link className="text-link" href={district.url}>استكشف الحي</Link>
    </article>
  );
}

export function ArticleCard({ article, priority = false }: { article: Article; priority?: boolean }) {
  return (
    <article className="content-card">
      {article.image ? <Link className="content-card__media" href={article.url}><ResponsiveImage image={article.image} sizes="(max-width: 720px) 100vw, 33vw" priority={priority} /></Link> : null}
      <div className="content-card__body">
        <div className="content-card__meta">{article.category ? <span>{article.category.name}</span> : null}{article.city ? <span>{article.city.name}</span> : null}<span>{article.reading_time_minutes} دقائق</span></div>
        <h2><Link href={article.url}>{article.title}</Link></h2>
        <p>{plainText(article.excerpt)}</p>
        <Link className="text-link" href={article.url}>قراءة المقال</Link>
      </div>
    </article>
  );
}

export function TestimonialCard({ testimonial }: { testimonial: Testimonial }) {
  return (
    <article className="testimonial">
      <div className="testimonial__stars" aria-label={`${testimonial.rating} من 5`}>{"★".repeat(testimonial.rating)}{"☆".repeat(5 - testimonial.rating)}</div>
      <blockquote>“{testimonial.review}”</blockquote>
      <footer>{testimonial.name}{testimonial.city_name ? ` — ${testimonial.city_name}` : ""}{testimonial.is_verified ? " · تقييم موثق" : ""}</footer>
    </article>
  );
}
