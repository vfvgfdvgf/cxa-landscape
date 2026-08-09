import type { HomePageData, HomeSection, HomeSectionItem, ImageData } from "@/types";

type MediaKind = "image" | "video";

function mediaIdentity(value: string) {
  if (!value) return "";
  try {
    const parsed = new URL(value, "https://getsiaq.online");
    return `${parsed.host.toLowerCase()}${parsed.pathname}`.replace(/\/$/, "").toLowerCase();
  } catch {
    return value.split(/[?#]/, 1)[0].replace(/\/$/, "").toLowerCase();
  }
}

/**
 * Frontend safety net for cached/legacy API payloads. The backend applies the
 * same policy, but keeping it here prevents stale data from repeating one
 * photo or video through an entire rendered page.
 */
export function enforceHomeMediaBudget(home: HomePageData, maxUses = 3): HomePageData {
  const uses: Record<MediaKind, Map<string, number>> = {
    image: new Map<string, number>(),
    video: new Map<string, number>(),
  };

  const reserve = (kind: MediaKind, value: string) => {
    const identity = mediaIdentity(value);
    if (!identity) return true;
    const current = uses[kind].get(identity) || 0;
    uses[kind].set(identity, current + 1);
    return current < maxUses;
  };

  const keepImage = (image: ImageData | null) => image && reserve("image", image.url) ? image : null;
  const keepAlternative = (kind: MediaKind, value: string, primary: string) => {
    if (!value) return "";
    if (mediaIdentity(value) === mediaIdentity(primary)) return value;
    return reserve(kind, value) ? value : "";
  };

  const heroVideo = reserve("video", home.hero.video) ? home.hero.video : "";
  const heroImage = heroVideo ? home.hero.image : keepImage(home.hero.image);
  const heroPoster = heroVideo && reserve("image", home.hero.poster) ? home.hero.poster : "";
  const hero = {
    ...home.hero,
    video: heroVideo,
    mobile_video: keepAlternative("video", home.hero.mobile_video, heroVideo),
    poster: heroPoster,
    image: heroImage,
    mobile_image: keepImage(home.hero.mobile_image),
  };

  const sanitizeItem = (item: HomeSectionItem): HomeSectionItem => {
    const video = reserve("video", item.video) ? item.video : "";
    return {
      ...item,
      video,
      mobile_video: keepAlternative("video", item.mobile_video, video),
      poster: video && reserve("image", item.poster) ? item.poster : "",
      image: video ? item.image : keepImage(item.image),
    };
  };

  const sections = home.sections.map((section): HomeSection => {
    // Hero is represented separately in the API and is not rendered again.
    if (section.key === "hero") return { ...section, media: { ...section.media } };
    const video = reserve("video", section.media.video) ? section.media.video : "";
    return {
      ...section,
      media: {
        ...section.media,
        video,
        mobile_video: keepAlternative("video", section.media.mobile_video, video),
        poster: video && reserve("image", section.media.poster) ? section.media.poster : "",
        image: video ? section.media.image : keepImage(section.media.image),
      },
      items: section.items.map(sanitizeItem),
    };
  });

  return { ...home, hero, sections };
}
