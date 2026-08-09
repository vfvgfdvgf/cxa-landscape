export function RichText({ html, className = "" }: { html: string; className?: string }) {
  if (!html) return null;
  return <div className={`rich-text ${className}`.trim()} dangerouslySetInnerHTML={{ __html: html }} />;
}
