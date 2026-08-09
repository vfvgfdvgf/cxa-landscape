import type { Metadata } from "next";
import Link from "next/link";

import { DistrictCard } from "@/components/content/Cards";
import { CallToAction } from "@/components/content/CallToAction";
import { JsonLd } from "@/components/seo/JsonLd";
import { Breadcrumbs } from "@/components/ui/Breadcrumbs";
import { Container } from "@/components/ui/Container";
import { PageHero } from "@/components/ui/PageHero";
import { EmptyState, Pagination } from "@/components/ui/States";
import { djangoApi, optionalApi, withQuery } from "@/lib/django-api";
import { SITE_URL, staticMetadata } from "@/lib/metadata";
import { pageNumber } from "@/lib/page-data";
import type { City, DistrictListItem, PaginatedResponse } from "@/types";

export const metadata: Metadata = staticMetadata(
  "أحياء التغطية",
  "تصفح أحياء مدن التغطية والوصول إلى خدمات النخيل واللاندسكيب والمشاريع والمحتوى المحلي لكل حي.",
  "/districts/",
);

export default async function DistrictsPage({
  searchParams,
}: {
  searchParams: Promise<{ page?: string; city?: string; q?: string }>;
}) {
  const query = await searchParams;
  const current = pageNumber(query.page);
  const city = (query.city || "").trim();
  const search = (query.q || "").trim();
  const [districtResponse, cities] = await Promise.all([
    optionalApi<PaginatedResponse<DistrictListItem>>(
      withQuery("districts/", { page: current, page_size: 24, city, q: search }),
      { revalidate: 600, tags: ["districts", city || "all-districts"] },
    ),
    djangoApi<PaginatedResponse<City>>("cities/?page_size=48", { revalidate: 900, tags: ["cities"] }),
  ]);
  const fallbackItems = cities.results
    .flatMap((item) => item.districts.map((district) => ({
      ...district,
      city: { id: item.id, name: item.name, slug: item.slug },
      created_at: item.created_at,
      updated_at: item.updated_at,
    })))
    .filter((district) => !city || district.city.slug === city)
    .filter((district) => !search || `${district.name} ${district.city.name}`.includes(search));
  const fallbackStart = (current - 1) * 24;
  const districts = districtResponse || {
    count: fallbackItems.length,
    next: null,
    previous: null,
    results: fallbackItems.slice(fallbackStart, fallbackStart + 24),
  };
  const paginationHref = withQuery("/districts/", { city, q: search });
  const itemListSchema = {
    "@context": "https://schema.org",
    "@type": "ItemList",
    name: city ? `أحياء ${cities.results.find((item) => item.slug === city)?.name || city}` : "دليل أحياء التغطية",
    numberOfItems: districts.count,
    itemListElement: districts.results.map((district, index) => ({
      "@type": "ListItem",
      position: fallbackStart + index + 1,
      name: `حي ${district.name}، ${district.city.name}`,
      url: `${SITE_URL}${district.url}`,
    })),
  };

  return (
    <>
      <PageHero
        eyebrow="دليل المواقع"
        title="كل حي بوابة لخدمة أقرب"
        description="ابحث باسم الحي أو اختر المدينة، ثم انتقل إلى صفحة محلية تجمع الخدمات والمشاريع والمقالات المرتبطة بالموقع."
      >
        <Breadcrumbs items={[{ label: "الأحياء" }]} />
      </PageHero>
      <section className="content-section district-directory">
        <Container>
          <form className="directory-filter" action="/districts/" method="get">
            <div className="form-field">
              <label htmlFor="district-search">اسم الحي</label>
              <input id="district-search" name="q" type="search" defaultValue={search} placeholder="مثال: النرجس" />
            </div>
            <div className="form-field">
              <label htmlFor="district-city">المدينة</label>
              <select id="district-city" name="city" defaultValue={city}>
                <option value="">جميع المدن</option>
                {cities.results.map((item) => <option key={item.id} value={item.slug}>{item.name}</option>)}
              </select>
            </div>
            <button className="button" type="submit">عرض النتائج</button>
            {city || search ? <Link className="button button--ghost" href="/districts/">إعادة الضبط</Link> : null}
          </form>
          <div className="directory-result-bar">
            <p><strong>{districts.count.toLocaleString("ar-SA")}</strong> حي مطابق</p>
            <span>صفحة {current.toLocaleString("ar-SA")}</span>
          </div>
          <div className="grid grid--3 district-grid">
            {districts.results.length
              ? districts.results.map((district) => <DistrictCard key={district.id} district={district} />)
              : <EmptyState message="لم نجد حيًا مطابقًا. جرّب اسمًا آخر أو اختر جميع المدن." />}
          </div>
          <Pagination current={current} count={districts.count} pageSize={24} href={paginationHref} />
        </Container>
      </section>
      <CallToAction title="لم تجد الحي؟ أخبرنا بموقع المشروع" />
      <JsonLd data={itemListSchema} />
    </>
  );
}
