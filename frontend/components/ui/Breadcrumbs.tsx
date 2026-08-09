import Link from "next/link";

import { JsonLd } from "@/components/seo/JsonLd";
import { absoluteUrl } from "@/lib/metadata";

interface Crumb {
  label: string;
  href?: string;
}

export function Breadcrumbs({ items }: { items: Crumb[] }) {
  const schemaItems = [{ label: "الرئيسية", href: "/" }, ...items].map((item, index) => ({
    "@type": "ListItem",
    position: index + 1,
    name: item.label,
    ...(item.href ? { item: absoluteUrl(item.href) } : {}),
  }));
  return (
    <>
      <nav className="breadcrumbs" aria-label="مسار التنقل">
        <ol>
          <li><Link href="/">الرئيسية</Link></li>
          {items.map((item, index) => (
            <li key={`${item.label}-${index}`} aria-current={index === items.length - 1 ? "page" : undefined}>
              {item.href && index !== items.length - 1 ? <Link href={item.href}>{item.label}</Link> : <span>{item.label}</span>}
            </li>
          ))}
        </ol>
      </nav>
      <JsonLd data={{ "@context": "https://schema.org", "@type": "BreadcrumbList", itemListElement: schemaItems }} />
    </>
  );
}
