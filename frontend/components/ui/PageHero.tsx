import type { ReactNode } from "react";

import { CinematicVideo } from "@/components/media/CinematicVideo";
import { Container } from "@/components/ui/Container";

interface PageHeroProps {
  eyebrow?: string;
  title: string;
  description?: string;
  children?: ReactNode;
  videoSrc?: string;
  poster?: string;
}

export function PageHero({
  eyebrow,
  title,
  description,
  children,
  videoSrc = "/videos/story-finished.mp4",
  poster = "/video-posters/story-finished.webp",
}: PageHeroProps) {
  return (
    <header className="page-hero page-hero--cinematic">
      <div className="page-hero__media">
        <CinematicVideo src={videoSrc} poster={poster} />
      </div>
      <div className="page-hero__veil" />
      <Container className="page-hero__cinematic-content">
        {eyebrow ? <div className="cinematic-label" data-reveal-line><span>{eyebrow}</span><i /></div> : null}
        <h1 data-reveal>{title}</h1>
        {description ? <p className="page-hero__lead" data-reveal>{description}</p> : null}
        <div className="page-hero__children" data-reveal>{children}</div>
      </Container>
    </header>
  );
}
