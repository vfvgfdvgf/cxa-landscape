"use client";

import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import Lenis from "lenis";
import { usePathname } from "next/navigation";
import { useEffect } from "react";

gsap.registerPlugin(ScrollTrigger);

export function SmoothExperience() {
  const pathname = usePathname();

  useEffect(() => {
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
    const root = document.documentElement;
    root.classList.add("motion-ready");

    if (reducedMotion.matches) {
      root.style.setProperty("--scroll-progress", "1");
      return () => root.classList.remove("motion-ready");
    }

    const lenis = new Lenis({
      duration: 1.05,
      smoothWheel: true,
      syncTouch: false,
      wheelMultiplier: 0.9,
    });
    const raf = (time: number) => lenis.raf(time * 1000);
    const context = gsap.context(() => {
      gsap.utils.toArray<HTMLElement>("[data-reveal]").forEach((element) => {
        gsap.fromTo(
          element,
          { autoAlpha: 0, y: 64 },
          {
            autoAlpha: 1,
            y: 0,
            duration: 1.05,
            ease: "power3.out",
            scrollTrigger: { trigger: element, start: "top 88%", once: true },
          },
        );
      });

      gsap.utils.toArray<HTMLElement>("[data-reveal-line]").forEach((element) => {
        gsap.fromTo(
          element,
          { clipPath: "inset(0 100% 0 0)" },
          {
            clipPath: "inset(0 0% 0 0)",
            duration: 1.25,
            ease: "power3.inOut",
            scrollTrigger: { trigger: element, start: "top 90%", once: true },
          },
        );
      });

      const heroMedia = document.querySelector<HTMLElement>(".cinematic-hero__media");
      if (heroMedia) {
        gsap.to(heroMedia, {
          scale: 1.075,
          ease: "none",
          scrollTrigger: { trigger: ".cinematic-hero", start: "top top", end: "bottom top", scrub: 1 },
        });
      }

      ScrollTrigger.create({
        start: 0,
        end: "max",
        onUpdate: (self) => root.style.setProperty("--scroll-progress", self.progress.toFixed(4)),
      });
    });

    lenis.on("scroll", ScrollTrigger.update);
    gsap.ticker.add(raf);
    gsap.ticker.lagSmoothing(0);
    const refreshFrame = window.requestAnimationFrame(() => ScrollTrigger.refresh());

    return () => {
      window.cancelAnimationFrame(refreshFrame);
      gsap.ticker.remove(raf);
      lenis.destroy();
      context.revert();
      ScrollTrigger.getAll().forEach((trigger) => trigger.kill());
      root.classList.remove("motion-ready");
      root.style.removeProperty("--scroll-progress");
    };
  }, [pathname]);

  return (
    <div className="scroll-rail" aria-hidden="true">
      <span />
    </div>
  );
}
