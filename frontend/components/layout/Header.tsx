import Link from "next/link";

import { DesktopNavigation, MobileMenu } from "@/components/layout/Navigation";
import { BrandIdentity } from "@/components/layout/BrandIdentity";
import { Container } from "@/components/ui/Container";
import { whatsappUrl } from "@/lib/contact";
import type { NavigationItem, SiteSettings } from "@/types";

export function Header({ navigation, site }: { navigation: NavigationItem[]; site: SiteSettings | null }) {
  const siteName = site?.site_name || "نخيل نجد";
  return (
    <header className="site-header">
      <Container className="header-inner">
        <Link className="brand" href="/" aria-label={`${siteName} — الرئيسية`}>
          <BrandIdentity site={site} />
        </Link>
        <DesktopNavigation navigation={navigation} />
        <div className="header-actions">
          {site?.whatsapp_number ? <a className="header-contact-link" href={whatsappUrl(site.whatsapp_number)} target="_blank" rel="noreferrer">واتساب</a> : null}
          <Link className="button button--small" href="/quote-request/">طلب عرض سعر</Link>
          <MobileMenu navigation={navigation} phone={site?.contact_phone} whatsapp={site?.whatsapp_number} />
        </div>
      </Container>
    </header>
  );
}
