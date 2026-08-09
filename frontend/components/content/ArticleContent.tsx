import { RichText } from "@/components/content/RichText";
import { plainText } from "@/lib/text";

interface Heading {
  id: string;
  label: string;
  level: "h2" | "h3";
}

function enhanceHeadings(html: string): { html: string; headings: Heading[] } {
  const headings: Heading[] = [];
  const enhanced = html.replace(/<(h2|h3)([^>]*)>([\s\S]*?)<\/\1>/gi, (match, level: "h2" | "h3", attributes: string, content: string) => {
    const label = plainText(content);
    if (!label) return match;
    const id = `article-section-${headings.length + 1}`;
    headings.push({ id, label, level: level.toLowerCase() as "h2" | "h3" });
    return `<${level}${attributes} id="${id}">${content}</${level}>`;
  });
  return { html: enhanced, headings };
}

export function ArticleContent({ html }: { html: string }) {
  const content = enhanceHeadings(html);
  return (
    <>
      {content.headings.length >= 3 ? (
        <nav className="article-toc" aria-label="محتويات المقال">
          <h2>محتويات المقال</h2>
          <ol>{content.headings.map((heading) => <li key={heading.id} className={heading.level === "h3" ? "article-toc__nested" : undefined}><a href={`#${heading.id}`}>{heading.label}</a></li>)}</ol>
        </nav>
      ) : null}
      <RichText html={content.html} />
    </>
  );
}
