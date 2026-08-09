import Image from "next/image";
import Link from "next/link";

import { Container } from "@/components/ui/Container";
import { BrandIdentity } from "@/components/layout/BrandIdentity";
import { whatsappUrl } from "@/lib/contact";
import type { SiteSettings } from "@/types";

export function Footer({ site }: { site: SiteSettings | null }) {
  return (
    <footer className="site-footer">
      <Container className="footer-grid">
        <div>
          <Link className="brand brand--footer" href="/" aria-label={`${site?.site_name || "نخيل نجد"} — الرئيسية`}><BrandIdentity site={site} compact /></Link>
          <p>{site?.footer_text || site?.tagline || "حلول نخيل ولاندسكيب مصممة للمكان والمناخ."}</p>
        </div>
        <div><h2>استكشف</h2><Link href="/services/">الخدمات</Link><Link href="/projects/">المشاريع</Link><Link href="/cities/">مدن التغطية</Link><Link href="/districts/">الأحياء</Link><Link href="/blog/">المقالات</Link></div>
        <div><h2>معلومات</h2><Link href="/about/">من نحن</Link><Link href="/quote-request/">طلب عرض سعر</Link><Link href="/cost-calculator/">حاسبة التكلفة</Link><Link href="/privacy/">سياسة الخصوصية</Link><Link href="/terms/">الشروط والأحكام</Link></div>
        <div><h2>تواصل</h2>{site?.contact_phone ? <a href={`tel:${site.contact_phone}`}>{site.contact_phone}</a> : null}{site?.email ? <a href={`mailto:${site.email}`}>{site.email}</a> : null}<a className="whatsapp-link" href={whatsappUrl(site?.whatsapp_number)} target="_blank" rel="noreferrer"><Image src="/images/whatsapp.svg" width={20} height={20} alt="" /> واتساب</a></div>
      </Container>
      <Container className="footer-bottom"><span>© {new Date().getFullYear()} {site?.site_name || "نخيل نجد"}</span><span>الموقع العام: getsiaq.online</span></Container>
    </footer>
  );
}
