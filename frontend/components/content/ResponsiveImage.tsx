import type { CSSProperties } from "react";

import { imageSourceSet, preferredImageUrl } from "@/lib/images";
import type { ImageData } from "@/types";

interface ResponsiveImageProps {
  image: ImageData;
  className?: string;
  priority?: boolean;
  sizes?: string;
}

export function ResponsiveImage({
  image,
  className,
  priority = false,
  sizes = "(max-width: 720px) 100vw, 50vw",
}: ResponsiveImageProps) {
  const style = image.width && image.height
    ? ({ aspectRatio: `${image.width} / ${image.height}` } as CSSProperties)
    : undefined;
  const webpSet = imageSourceSet(image, "webp");
  const avifSet = imageSourceSet(image, "avif");

  return (
    <picture className={`image-frame image-frame--loaded ${className || ""}`.trim()} style={style}>
      {avifSet ? <source type="image/avif" srcSet={avifSet} sizes={sizes} /> : null}
      {webpSet ? <source type="image/webp" srcSet={webpSet} sizes={sizes} /> : null}
      <img
        src={preferredImageUrl(image, 768, "webp")}
        srcSet={webpSet}
        sizes={sizes}
        alt={image.alt}
        loading={priority ? "eager" : "lazy"}
        fetchPriority={priority ? "high" : "auto"}
        decoding="async"
        width={image.width || undefined}
        height={image.height || undefined}
      />
    </picture>
  );
}
