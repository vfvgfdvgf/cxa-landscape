import type { Metadata } from "next";
import Link from "next/link";

import { ArticleContent } from "@/components/content/ArticleContent";
import { ArticleCard } from "@/components/content/Cards";
import { CallToAction } from "@/components/content/CallToAction";
import { ResponsiveImage } from "@/components/content/ResponsiveImage";
import { JsonLd } from "@/components/seo/JsonLd";
import { Breadcrumbs } from "@/components/ui/Breadcrumbs";
import { Container } from "@/components/ui/Container";
import { PageHero } from "@/components/ui/PageHero";
import { SectionHeading } from "@/components/ui/SectionHeading";
import { buildMetadata, SITE_URL } from "@/lib/metadata";
import { detailApi } from "@/lib/page-data";
import type { Article } from "@/types";

async function getArticle(slug: string) {
  return detailApi<Article>(`blog/${encodeURIComponent(slug)}/`, 300, ["articles", `article-${slug}`]);
}

export async function generateMetadata({ params }: { params: Promise<{ postSlug: string }> }): Promise<Metadata> {
  const { postSlug } = await params;
  return buildMetadata((await getArticle(postSlug)).seo);
}

export default async function ArticlePage({ params }: { params: Promise<{ postSlug: string }> }) {
  const { postSlug } = await params;
  const article = await getArticle(postSlug);
  const date = article.published_at || article.created_at;
  const articleUrl = `${SITE_URL}${article.url}`;
  const shareText = encodeURIComponent(article.title);
  const shareUrl = encodeURIComponent(articleUrl);
  const formatDate = (value: string) => new Intl.DateTimeFormat("ar-SA", { dateStyle: "long" }).format(new Date(value));
  const schema = [
    {
      "@context": "https://schema.org",
      "@type": "BlogPosting",
      headline: article.title,
      description: article.excerpt,
      image: article.image?.url,
      datePublished: date,
      dateModified: article.updated_at,
      mainEntityOfPage: articleUrl,
      inLanguage: "ar-SA",
      author: { "@type": "Organization", name: "نخيل نجد", url: SITE_URL },
      publisher: { "@type": "Organization", name: "نخيل نجد", url: SITE_URL },
    },
    {
      "@context": "https://schema.org",
      "@type": "BreadcrumbList",
      itemListElement: [
        { "@type": "ListItem", position: 1, name: "الرئيسية", item: SITE_URL },
        { "@type": "ListItem", position: 2, name: "المقالات", item: `${SITE_URL}/blog/` },
        { "@type": "ListItem", position: 3, name: article.title, item: articleUrl },
      ],
    },
  ];

  return (
    <>
      <PageHero eyebrow={article.category?.name || "دليل الخبرة"} title={article.title} description={article.excerpt}>
        <Breadcrumbs items={[{ label: "المقالات", href: "/blog/" }, { label: article.title }]} />
        <div className="detail-facts"><span><strong>{article.reading_time_minutes.toLocaleString("ar-SA")}</strong> دقائق قراءة</span><span><strong>{formatDate(date)}</strong> نشر</span><span><strong>{formatDate(article.updated_at)}</strong> تحديث</span></div>
      </PageHero>

      <section className="content-section detail-section detail-section--article">
        <Container>
          {article.image ? <ResponsiveImage image={article.image} className="detail-media detail-media--hero" sizes="100vw" priority /> : null}
          <div className="detail-layout detail-layout--editorial">
            <article className="detail-article article-prose">
              <p className="detail-kicker">دليل عملي / {article.category?.name || "اللاندسكيب"}</p>
              <p className="detail-deck">{article.excerpt}</p>
              <ArticleContent html={article.content} />
              {article.tags.length ? <div className="tag-list article-tags">{article.tags.map((tag) => <Link key={tag.id} href={tag.url}>#{tag.name}</Link>)}</div> : null}
            </article>
            <aside className="detail-sidebar detail-sidebar--editorial article-sidebar">
              <p className="eyebrow">عن الدليل</p>
              {article.category ? <p><strong>التصنيف</strong><Link href={article.category.url}>{article.category.name}</Link></p> : null}
              {article.city ? <p><strong>المدينة</strong><Link href={`/${article.city.slug}/`}>{article.city.name}</Link></p> : null}
              <p><strong>القراءة</strong><span>{article.reading_time_minutes} دقائق تقريبًا</span></p>
              <div className="article-meta-stack"><span>نشر: {formatDate(date)}</span><span>آخر تحديث: {formatDate(article.updated_at)}</span></div>
              <h2>شارك الدليل</h2>
              <div className="share-links"><a href={`https://wa.me/?text=${shareText}%20${shareUrl}`} target="_blank" rel="noreferrer">واتساب</a><a href={`https://twitter.com/intent/tweet?text=${shareText}&url=${shareUrl}`} target="_blank" rel="noreferrer">منصة X</a></div>
              <Link className="button" href="/quote-request/">استشارة المشروع</Link>
            </aside>
          </div>
        </Container>
      </section>

      {article.related_articles?.length ? <section className="content-section content-section--tinted"><Container><SectionHeading eyebrow="من نفس الملف" title="مقالات تكمل الصورة" intro="انتقل لمواضيع مرتبطة بدل ما تبدأ البحث من الصفر." /><div className="grid grid--3 listing-grid">{article.related_articles.map((item, index) => <ArticleCard key={item.id} article={item} index={index} />)}</div></Container></section> : null}
      <CallToAction />
      <JsonLd data={schema} />
    </>
  );
}
