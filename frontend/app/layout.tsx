import type { Metadata, Viewport } from "next";
import localFont from "next/font/local";

import { Footer } from "@/components/layout/Footer";
import { Header } from "@/components/layout/Header";
import { SmoothExperience } from "@/components/motion/SmoothExperience";
import { JsonLd } from "@/components/seo/JsonLd";
import { optionalApi } from "@/lib/django-api";
import { SITE_URL } from "@/lib/metadata";
import type { NavigationItem, SiteSettings } from "@/types";

import "./globals.css";
import "./cinematic.css";

// The content is managed by Django. Rendering on demand keeps a first-time
// Render Blueprint deployment independent from backend build order.
export const dynamic = "force-dynamic";

const uiFont = localFont({
  src: [
    { path: "../public/fonts/thmanyahsans-Regular.woff2", weight: "400", style: "normal" },
    { path: "../public/fonts/thmanyahsans-Bold.woff2", weight: "700", style: "normal" },
  ],
  variable: "--font-ui",
  display: "swap",
});

const displayFont = localFont({
  src: [
    { path: "../public/fonts/thmanyahserifdisplay-Regular.woff2", weight: "400", style: "normal" },
    { path: "../public/fonts/thmanyahserifdisplay-Bold.woff2", weight: "700", style: "normal" },
  ],
  variable: "--font-display",
  display: "swap",
});

export async function generateMetadata(): Promise<Metadata> {
  const site = await optionalApi<SiteSettings>("site/", { revalidate: 300, tags: ["site"] });
  const siteName = site?.site_name || "نخيل نجد";
  const description = site?.seo_defaults.description || "خدمات النخيل واللاندسكيب والري والشبوك في السعودية.";
  const socialImage = site?.default_image || site?.hero_image;
  return {
    metadataBase: new URL(SITE_URL),
    title: siteName,
    description,
    keywords: site?.seo_defaults.keywords?.split(",").map((item) => item.trim()).filter(Boolean),
    applicationName: siteName,
    authors: [{ name: siteName, url: SITE_URL }],
    creator: siteName,
    publisher: siteName,
    category: "Landscaping",
    alternates: { canonical: SITE_URL, languages: { "ar-SA": SITE_URL, "x-default": SITE_URL } },
    icons: { icon: "/images/favicon.svg", apple: "/images/favicon.svg" },
    formatDetection: { telephone: false, email: false, address: false },
    robots: { index: true, follow: true, googleBot: { index: true, follow: true, "max-image-preview": "large" } },
    openGraph: {
      type: "website",
      locale: "ar_SA",
      url: SITE_URL,
      siteName,
      title: siteName,
      description,
      images: socialImage ? [{ url: socialImage.url, alt: socialImage.alt || siteName }] : undefined,
    },
    twitter: {
      card: "summary_large_image",
      title: siteName,
      description,
      images: socialImage ? [socialImage.url] : undefined,
    },
  };
}

export const viewport: Viewport = { width: "device-width", initialScale: 1, themeColor: "#0c0f0d", colorScheme: "light dark" };

const fallbackNavigation: NavigationItem[] = [
  { label: "الرئيسية", url: "/", new_tab: false },
  { label: "من نحن", url: "/about/", new_tab: false },
  { label: "الخدمات", url: "/services/", new_tab: false },
  { label: "المشاريع", url: "/projects/", new_tab: false },
  { label: "المدن", url: "/cities/", new_tab: false },
  { label: "الأحياء", url: "/districts/", new_tab: false },
  { label: "المقالات", url: "/blog/", new_tab: false },
  { label: "تواصل معنا", url: "/contact/", new_tab: false },
];

function withDistrictsLink(items: NavigationItem[]): NavigationItem[] {
  if (items.some((item) => item.url.split(/[?#]/, 1)[0].replace(/\/$/, "") === "/districts")) return items;
  const result = [...items];
  const cityIndex = result.findIndex((item) => item.url.split(/[?#]/, 1)[0].replace(/\/$/, "") === "/cities");
  result.splice(cityIndex >= 0 ? cityIndex + 1 : Math.min(4, result.length), 0, {
    label: "الأحياء",
    url: "/districts/",
    new_tab: false,
  });
  return result;
}

function safeAnalyticsId(value?: string): string {
  const normalized = (value || "").trim().toUpperCase();
  return /^(?:G|GT)-[A-Z0-9]+$/.test(normalized) ? normalized : "";
}

function safeTagManagerId(value?: string): string {
  const normalized = (value || "").trim().toUpperCase();
  return /^GTM-[A-Z0-9]+$/.test(normalized) ? normalized : "";
}

export default async function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  const [site, navigation] = await Promise.all([
    optionalApi<SiteSettings>("site/", { revalidate: 300, tags: ["site"] }),
    optionalApi<NavigationItem[]>("navigation/", { revalidate: 300, tags: ["navigation"] }),
  ]);
  const resolvedNavigation = withDistrictsLink(navigation?.length ? navigation : fallbackNavigation);
  const analyticsId = safeAnalyticsId(site?.verification?.google_analytics_id);
  const tagManagerId = safeTagManagerId(site?.verification?.google_tag_manager_id);
  const verificationTags = site?.verification?.meta_tags || [];
  const usesCloudinary = [site?.hero_image?.url, site?.hero_mobile_image?.url, site?.default_image?.url, site?.logo?.url]
    .some((value) => value?.startsWith("https://res.cloudinary.com/"));
  const organization = {
    "@context": "https://schema.org",
    "@type": site?.business.type || "LocalBusiness",
    name: site?.business.legal_name || site?.site_name || "نخيل نجد",
    url: SITE_URL,
    telephone: site?.contact_phone || undefined,
    email: site?.email || undefined,
    image: site?.default_image?.url || undefined,
    logo: site?.logo?.url || undefined,
    sameAs: site ? Object.values(site.social_links).filter(Boolean) : [],
    areaServed: site?.business.area_served || ["SA"],
    openingHours: site?.business.opening_hours.length ? site.business.opening_hours : undefined,
    contactPoint: site?.contact_phone ? {
      "@type": "ContactPoint",
      telephone: site.contact_phone,
      contactType: "customer service",
      areaServed: "SA",
      availableLanguage: ["ar"],
    } : undefined,
    address: site?.business.address.street_address ? {
      "@type": "PostalAddress",
      streetAddress: site.business.address.street_address,
      addressLocality: site.business.address.locality || undefined,
      addressRegion: site.business.address.region || undefined,
      postalCode: site.business.address.postal_code || undefined,
      addressCountry: site.business.address.country,
    } : undefined,
    geo: site?.business.latitude && site.business.longitude ? {
      "@type": "GeoCoordinates",
      latitude: site.business.latitude,
      longitude: site.business.longitude,
    } : undefined,
  };
  return (
    <html lang="ar" dir="rtl" className={`${uiFont.variable} ${displayFont.variable}`} suppressHydrationWarning>
      <head>
        {usesCloudinary ? <link rel="preconnect" href="https://res.cloudinary.com" crossOrigin="anonymous" /> : null}
        {verificationTags.map((item) => (
          item.name && item.content ? <meta key={`${item.name}-${item.content}`} name={item.name} content={item.content} /> : null
        ))}
        {analyticsId ? <script async src={`https://www.googletagmanager.com/gtag/js?id=${analyticsId}`} /> : null}
        {analyticsId ? (
          <script dangerouslySetInnerHTML={{ __html: `window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments);}gtag('js',new Date());gtag('config','${analyticsId}',{anonymize_ip:true});` }} />
        ) : null}
        {tagManagerId ? (
          <script dangerouslySetInnerHTML={{ __html: `(function(w,d,s,l,i){w[l]=w[l]||[];w[l].push({'gtm.start':new Date().getTime(),event:'gtm.js'});var f=d.getElementsByTagName(s)[0],j=d.createElement(s),dl=l!='dataLayer'?'&l='+l:'';j.async=true;j.src='https://www.googletagmanager.com/gtm.js?id='+i+dl;f.parentNode.insertBefore(j,f);})(window,document,'script','dataLayer','${tagManagerId}');` }} />
        ) : null}
      </head>
      <body style={site ? ({
        "--brand": site.colors.primary,
        "--brand-dark": site.colors.secondary,
        "--accent": site.colors.accent,
        "--paper": site.colors.background,
        "--ink": site.colors.text,
      } as React.CSSProperties) : undefined}>
        <SmoothExperience />
        {tagManagerId ? (
          <noscript><iframe src={`https://www.googletagmanager.com/ns.html?id=${tagManagerId}`} height="0" width="0" style={{ display: "none", visibility: "hidden" }} title="Google Tag Manager" /></noscript>
        ) : null}
        <a className="skip-link" href="#main-content">انتقل إلى المحتوى</a>
        <Header navigation={resolvedNavigation} site={site} />
        <main id="main-content">{children}</main>
        <Footer site={site} />
        <JsonLd data={organization} />
      </body>
    </html>
  );
}
