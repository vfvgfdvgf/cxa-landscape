export function JsonLd({ data }: { data: Record<string, unknown> | Array<Record<string, unknown>> }) {
  const content = JSON.stringify(data).replace(/</g, "\\u003c");
  return <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: content }} />;
}

export function SeoJsonLd({ schema }: { schema?: Record<string, unknown> | null }) {
  if (!schema || !Object.keys(schema).length) return null;
  return <JsonLd data={{ "@context": "https://schema.org", ...schema }} />;
}
