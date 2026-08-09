"use client";

import { useEffect, useRef, useState } from "react";

interface CinematicVideoProps {
  src: string;
  mobileSrc?: string;
  poster: string;
  className?: string;
  priority?: boolean;
}

export function CinematicVideo({ src, mobileSrc, poster, className, priority = false }: CinematicVideoProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
    if (reducedMotion.matches) {
      video.pause();
      return;
    }

    const play = () => video.play().catch(() => undefined);
    if (priority) {
      void play();
      return;
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) void play();
        else video.pause();
      },
      { rootMargin: "180px 0px", threshold: 0.08 },
    );
    observer.observe(video);
    return () => observer.disconnect();
  }, [priority]);

  return (
    <video
      ref={videoRef}
      className={`${className || ""}${ready ? " is-ready" : ""}`.trim()}
      autoPlay={priority}
      muted
      loop
      playsInline
      preload={priority ? "auto" : "metadata"}
      poster={poster}
      aria-hidden="true"
      tabIndex={-1}
      onCanPlay={() => setReady(true)}
    >
      {mobileSrc ? <source media="(max-width: 767px)" src={mobileSrc} type="video/mp4" /> : null}
      <source src={src} type="video/mp4" />
    </video>
  );
}
