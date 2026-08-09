import { ResponsiveImage } from "@/components/content/ResponsiveImage";
import type { SiteSettings } from "@/types";

export function BrandIdentity({ site, compact = false }: { site: SiteSettings | null; compact?: boolean }) {
  const siteName = site?.site_name || "نخيل نجد";
  return (
    <>
      {site?.logo ? (
        <ResponsiveImage image={site.logo} className="brand-logo" sizes="180px" priority />
      ) : (
        <span className="brand-mark" aria-hidden="true">ن</span>
      )}
      <span className="brand-copy">
        <strong>{siteName}</strong>
        {!compact ? <small>{site?.tagline || "نخيل ولاندسكيب"}</small> : null}
      </span>
    </>
  );
}
