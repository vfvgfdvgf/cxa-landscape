import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "نخيل نجد",
    short_name: "نخيل نجد",
    description: "توريد وزراعة النخيل وتنفيذ اللاندسكيب وشبكات الري والشبوك في السعودية.",
    start_url: "/",
    display: "standalone",
    background_color: "#f4f1e9",
    theme_color: "#173d31",
    lang: "ar",
    dir: "rtl",
    icons: [{ src: "/images/favicon.svg", sizes: "any", type: "image/svg+xml" }],
  };
}
