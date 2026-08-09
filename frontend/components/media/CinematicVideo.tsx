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
  const [readySource, setReadySource] = useState("");
  const [failedSource, setFailedSource] = useState("");
  const ready = readySource === src;
  const failed = failedSource === src;

  const mimeType = (value: string) => {
    const cleanValue = value.split(/[?#]/, 1)[0].toLowerCase();
    if (cleanValue.endsWith(".webm")) return "video/webm";
    if (cleanValue.endsWith(".mov")) return "video/quicktime";
    return "video/mp4";
  };

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
      className={`${className || ""}${ready ? " is-ready" : ""}${failed ? " is-failed" : ""}`.trim()}
      autoPlay={priority}
      muted
      loop
      playsInline
      preload={priority ? "auto" : "metadata"}
      poster={poster}
      aria-hidden="true"
      tabIndex={-1}
      onCanPlay={() => setReadySource(src)}
      onError={() => setFailedSource(src)}
    >
      {mobileSrc ? <source media="(max-width: 767px)" src={mobileSrc} type={mimeType(mobileSrc)} /> : null}
      <source src={src} type={mimeType(src)} />
    </video>
  );
}
