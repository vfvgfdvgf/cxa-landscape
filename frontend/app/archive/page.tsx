import type { Metadata } from "next";
import Link from "next/link";

import { Breadcrumbs } from "@/components/ui/Breadcrumbs";
import { Container } from "@/components/ui/Container";
import { PageHero } from "@/components/ui/PageHero";
import { djangoApi } from "@/lib/django-api";
import { staticMetadata } from "@/lib/metadata";
import type { ArchiveStats } from "@/types";

export const dynamic = "force-dynamic";

export const metadata: Metadata = staticMetadata("أرشيف الموقع", "بوابة إلى أرشيف الخدمات والمدن والأحياء والمقالات المنشورة.", "/archive/");
export default async function ArchivePage() { const stats = await djangoApi<ArchiveStats>("archive/", { revalidate: 900, tags: ["archive"] }); const items = [{ label: "الخدمات", count: stats.services, href: "/archive/services/" }, { label: "المدن", count: stats.cities, href: "/archive/cities/" }, { label: "الأحياء", count: stats.districts, href: "/districts/" }, { label: "المقالات", count: stats.articles, href: "/archive/articles/" }, { label: "المشاريع", count: stats.projects, href: "/projects/" }]; return <><PageHero eyebrow="شبكة المحتوى" title="أرشيف منظم لكل ما هو منشور" description="وصول مباشر إلى الخدمات والمواقع والمحتوى الحالي."><Breadcrumbs items={[{ label: "الأرشيف" }]} /></PageHero><section className="content-section"><Container><div className="grid grid--3">{items.map((item) => <article className="archive-stat" key={item.label}><strong>{item.count.toLocaleString("ar-SA")}</strong><h2>{item.label}</h2><Link className="text-link" href={item.href}>استعرض {item.label}</Link></article>)}</div></Container></section></>; }
