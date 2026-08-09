import { imageSourceSet, preferredImageUrl } from "@/lib/images";
import type { ImageData } from "@/types";

export function HeroImage({
  image,
  mobileImage,
  focusX = 50,
  focusY = 50,
}: {
  image: ImageData;
  mobileImage?: ImageData | null;
  focusX?: number;
  focusY?: number;
}) {
  const desktopAvif = imageSourceSet(image, "avif");
  const desktopWebp = imageSourceSet(image, "webp");
  const mobileAvif = mobileImage ? imageSourceSet(mobileImage, "avif") : undefined;
  const mobileWebp = mobileImage ? imageSourceSet(mobileImage, "webp") : undefined;

  const desktopHasAvif = Boolean(desktopAvif);
  const mobileHasAvif = Boolean(mobileAvif || (!mobileImage && desktopAvif));
  const desktopPreload = preferredImageUrl(image, 1200, desktopHasAvif ? "avif" : "webp");
  const mobilePreload = mobileImage
    ? preferredImageUrl(mobileImage, 768, mobileHasAvif ? "avif" : "webp")
    : desktopPreload;

  return (
    <>
      <link rel="preload" as="image" type={mobileHasAvif ? "image/avif" : "image/webp"} href={mobilePreload} media="(max-width: 720px)" fetchPriority="high" />
      <link rel="preload" as="image" type={desktopHasAvif ? "image/avif" : "image/webp"} href={desktopPreload} media="(min-width: 721px)" fetchPriority="high" />
      <picture className="hero-picture hero-picture--loaded">
      {mobileImage && mobileAvif ? <source media="(max-width: 720px)" type="image/avif" srcSet={mobileAvif} sizes="100vw" /> : null}
      {mobileImage ? <source media="(max-width: 720px)" type="image/webp" srcSet={mobileWebp || preferredImageUrl(mobileImage, 768, "webp")} sizes="100vw" /> : null}
      {desktopAvif ? <source type="image/avif" srcSet={desktopAvif} sizes="100vw" /> : null}
      {desktopWebp ? <source type="image/webp" srcSet={desktopWebp} sizes="100vw" /> : null}
      <img
        src={preferredImageUrl(image, 1200, "webp")}
        srcSet={desktopWebp}
        sizes="100vw"
        alt={image.alt}
        loading="eager"
        fetchPriority="high"
        decoding="async"
        width={image.width || undefined}
        height={image.height || undefined}
        style={{ objectPosition: `${focusX}% ${focusY}%` }}
      />
      </picture>
    </>
  );
}
