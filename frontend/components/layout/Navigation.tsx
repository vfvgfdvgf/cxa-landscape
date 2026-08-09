"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef } from "react";
import type { KeyboardEvent } from "react";

import { whatsappUrl } from "@/lib/contact";
import type { NavigationItem } from "@/types";

function isInternal(url: string): boolean {
  return url.startsWith("/") && !url.startsWith("//");
}

function isActivePath(pathname: string, url: string): boolean {
  if (!isInternal(url)) return false;
  const target = url.split(/[?#]/, 1)[0].replace(/\/$/, "") || "/";
  const current = pathname.replace(/\/$/, "") || "/";
  return target === "/" ? current === "/" : current === target || current.startsWith(`${target}/`);
}

function NavigationLink({ item, pathname, onNavigate }: { item: NavigationItem; pathname: string; onNavigate?: () => void }) {
  const active = isActivePath(pathname, item.url);
  const className = active ? "is-active" : undefined;
  const common = { className, "aria-current": active ? ("page" as const) : undefined, onClick: onNavigate };
  if (!isInternal(item.url) || item.new_tab) {
    return <a href={item.url} target={item.new_tab ? "_blank" : undefined} rel={item.new_tab ? "noreferrer" : undefined} {...common}>{item.label}</a>;
  }
  return <Link href={item.url} {...common}>{item.label}</Link>;
}

export function DesktopNavigation({ navigation }: { navigation: NavigationItem[] }) {
  const pathname = usePathname();
  return (
    <nav className="desktop-nav" aria-label="التنقل الرئيسي">
      {navigation.map((item) => <NavigationLink key={`${item.label}-${item.url}`} item={item} pathname={pathname} />)}
    </nav>
  );
}

export function MobileMenu({ navigation, phone, whatsapp }: { navigation: NavigationItem[]; phone?: string; whatsapp?: string }) {
  const pathname = usePathname();
  const detailsRef = useRef<HTMLDetailsElement>(null);

  function closeMenu() {
    if (detailsRef.current) detailsRef.current.open = false;
  }

  useEffect(() => {
    if (detailsRef.current) detailsRef.current.open = false;
  }, [pathname]);

  return (
    <details ref={detailsRef} className="mobile-menu" onKeyDown={(event: KeyboardEvent<HTMLDetailsElement>) => { if (event.key === "Escape") closeMenu(); }}>
      <summary aria-label="فتح قائمة الموقع"><span></span><span></span><span></span></summary>
      <div className="mobile-menu__panel">
        <nav aria-label="قائمة الجوال">
          {navigation.map((item) => <NavigationLink key={`${item.label}-${item.url}-mobile`} item={item} pathname={pathname} onNavigate={closeMenu} />)}
        </nav>
        <div className="mobile-menu__actions">
          <Link className="button" href="/quote-request/" onClick={closeMenu}>اطلب عرض سعر</Link>
          {whatsapp ? <a className="button button--ghost" href={whatsappUrl(whatsapp)} target="_blank" rel="noreferrer" onClick={closeMenu}>واتساب</a> : null}
          {phone ? <a className="text-link" href={`tel:${phone}`} onClick={closeMenu}>اتصال مباشر</a> : null}
        </div>
      </div>
    </details>
  );
}
