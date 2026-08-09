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

const INTERIOR_HERO_MEDIA = [
  { video: "/videos/story-night.mp4", poster: "/video-posters/story-night.webp" },
  { video: "/videos/story-transplant.mp4", poster: "/video-posters/story-transplant.webp" },
  { video: "/videos/story-care.mp4", poster: "/video-posters/story-care.webp" },
  { video: "/videos/story-finished.mp4", poster: "/video-posters/story-finished.webp" },
] as const;

function mediaForPage(identity: string) {
  let hash = 0;
  for (const character of identity) hash = (hash * 31 + character.codePointAt(0)!) >>> 0;
  return INTERIOR_HERO_MEDIA[hash % INTERIOR_HERO_MEDIA.length];
}

export function PageHero({
  eyebrow,
  title,
  description,
  children,
  videoSrc,
  poster,
}: PageHeroProps) {
  const selectedMedia = mediaForPage(`${eyebrow || ""}|${title}`);
  const resolvedVideo = videoSrc || selectedMedia.video;
  const resolvedPoster = poster || selectedMedia.poster;
  return (
    <header className="page-hero page-hero--cinematic">
      <div className="page-hero__media">
        <CinematicVideo src={resolvedVideo} poster={resolvedPoster} />
      </div>
      <div className="page-hero__veil" />
      <Container className="page-hero__cinematic-content">
        <div className="page-hero__edition" aria-hidden="true">
          <span>NAKHEEL NAJD</span>
          <span>{eyebrow || "LANDSCAPE"}</span>
        </div>
        {eyebrow ? <div className="cinematic-label" data-reveal-line><span>{eyebrow}</span><i /></div> : null}
        <h1 data-reveal>{title}</h1>
        {description ? <p className="page-hero__lead" data-reveal>{description}</p> : null}
        <div className="page-hero__children" data-reveal>{children}</div>
      </Container>
    </header>
  );
}
