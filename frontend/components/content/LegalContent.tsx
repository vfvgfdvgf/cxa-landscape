import { Breadcrumbs } from "@/components/ui/Breadcrumbs";
import { Container } from "@/components/ui/Container";
import { PageHero } from "@/components/ui/PageHero";
import type { LegalPage } from "@/types";

export function LegalContent({ page }: { page: LegalPage }) {
  return <><PageHero eyebrow="معلومات قانونية" title={page.title} description={page.description}><Breadcrumbs items={[{ label: page.title }]} /></PageHero><section className="content-section"><Container className="rich-text">{page.sections.map(([title, content]) => <section key={title}><h2>{title}</h2><p>{content}</p></section>)}</Container></section></>;
}
