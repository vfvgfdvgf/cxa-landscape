export interface MarketIntent {
  label: string;
  href: string;
  note: string;
}

export const SERVICE_MARKET_INTENTS: MarketIntent[] = [
  { label: "تنسيق حدائق الرياض", href: "/services/?q=%D8%AA%D9%86%D8%B3%D9%8A%D9%82%20%D8%AD%D8%AF%D8%A7%D8%A6%D9%82", note: "تصميم وتنفيذ وصيانة للمنازل والمشاريع" },
  { label: "تصميم حدائق فلل", href: "/services/villa-landscape/", note: "توزيع الزراعة والممرات والجلسات والظل" },
  { label: "حديقة منزلية صغيرة", href: "/blog/small-home-garden-design-saudi/", note: "حلول للمساحات المحدودة بدون ازدحام" },
  { label: "تركيب عشب صناعي", href: "/services/artificial-grass/", note: "اختيار النوع وتجهيز القاعدة والتصريف" },
  { label: "زراعة ثيل طبيعي", href: "/services/natural-turf/", note: "تجهيز التربة والري وبرنامج العناية" },
  { label: "تركيب شبكات ري", href: "/services/irrigation-design/", note: "تصميم المناطق والضغط والتغطية" },
  { label: "شبكات ري ذكية", href: "/services/smart-irrigation-controller/", note: "تحكم وجدولة تقلل الهدر" },
  { label: "صيانة حدائق", href: "/services/monthly-garden-maintenance/", note: "قص وتقليم وتسميد ومتابعة دورية" },
  { label: "نقل وزراعة نخيل", href: "/services/palm-transplanting/", note: "فحص الجذور والتجهيز والتثبيت" },
  { label: "توريد نخيل", href: "/services/arabian-date-palm-supply/", note: "اختيار النوع والمقاس المناسب للموقع" },
  { label: "جلسات خارجية", href: "/services/outdoor-seating/", note: "تنسيق الظل والزرع والحركة حول الجلسة" },
  { label: "برجولات ومظلات", href: "/services/pergola-installation/", note: "حلول ظل متكاملة مع تصميم الحديقة" },
];

export const ARTICLE_MARKET_INTENTS: MarketIntent[] = [
  { label: "كم تكلفة تنسيق الحديقة؟", href: "/blog/garden-landscaping-cost-saudi-guide/", note: "العوامل التي تغيّر السعر قبل طلب العرض" },
  { label: "سعر متر العشب الصناعي", href: "/blog/artificial-grass-price-factors-saudi/", note: "السماكة والكثافة والتجهيز والتركيب" },
  { label: "طبيعي أم صناعي؟", href: "/blog/natural-vs-artificial-grass/", note: "مقارنة الاستخدام والصيانة والتكلفة" },
  { label: "أفضل نباتات للحر", href: "/blog/best-outdoor-plants-hot-climate/", note: "اختيارات أقرب للمناخ السعودي" },
  { label: "أفضل أشجار ظل", href: "/blog/best-shade-trees-saudi-gardens/", note: "الحجم والجذور وموقع الزراعة" },
  { label: "كيف تختار شبكة ري؟", href: "/blog/choose-garden-irrigation-system/", note: "التنقيط والرش وتقسيم المناطق" },
  { label: "تصميم حديقة صغيرة", href: "/blog/small-home-garden-design-saudi/", note: "توزيع عملي للممر والجلسة والزراعة" },
  { label: "كيف تقلل استهلاك الماء؟", href: "/blog/reduce-garden-water-use/", note: "جدولة الري واختيار النباتات وتحسين التربة" },
  { label: "صيانة الحديقة بالصيف", href: "/blog/prepare-gardens-before-summer/", note: "ري وتقليم وتسميد قبل موجات الحرارة" },
  { label: "اختيار شركة لاندسكيب", href: "/blog/choose-landscape-contractor-checklist/", note: "كيف تقارن النطاق والمواصفات والضمان" },
];
