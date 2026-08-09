export interface ImageData {
  url: string;
  alt: string;
  width: number | null;
  height: number | null;
  variants?: Array<{ url: string; avif_url?: string; width: number }>;
}

export interface SeoData {
  title: string;
  description: string;
  keywords: string;
  robots: string;
  canonical_path: string;
  image: string;
  og_type: "website" | "article" | string;
  published_time: string;
  modified_time: string;
  schema: Record<string, unknown>;
}

export interface RelatedItem {
  id: number;
  name: string;
  slug: string;
}

export interface NavigationItem {
  label: string;
  url: string;
  new_tab: boolean;
}

export interface SiteSettings {
  site_name: string;
  tagline: string;
  contact_phone: string;
  whatsapp_number: string;
  email: string;
  address: string;
  footer_text: string;
  service_highlights: string[];
  contact_numbers: Array<{ label: string; phone: string; is_primary: boolean; whatsapp: boolean }>;
  social_links: Record<string, string>;
  default_image: ImageData | null;
  logo: ImageData | null;
  hero_image: ImageData | null;
  hero_mobile_image: ImageData | null;
  hero_settings: { focus_x: number; focus_y: number; overlay_opacity: number };
  colors: { primary: string; secondary: string; accent: string; background: string; text: string };
  seo_defaults: { title: string; description: string; keywords: string; twitter_handle: string };
  verification?: {
    meta_tags: Array<{ name: string; content: string }>;
    html_files: Array<{ name: string; content: string }>;
    dns_records: Array<{ type: "TXT" | "CNAME" | string; name: string; value: string }>;
    google_analytics_id: string;
    google_tag_manager_id: string;
  };
  business: {
    type: string;
    legal_name: string;
    opening_hours: string[];
    area_served: string[];
    latitude: string;
    longitude: string;
    address: {
      street_address: string;
      locality: string;
      region: string;
      postal_code: string;
      country: string;
    };
  };
  updated_at: string;
}

export interface Service {
  id: number;
  title: string;
  short_title: string;
  slug: string;
  description: string;
  benefits: string[];
  image: ImageData | null;
  category: RelatedItem | null;
  tags: RelatedItem[];
  primary_city: RelatedItem | null;
  primary_district: (RelatedItem & { city_slug: string }) | null;
  cities: RelatedItem[];
  url: string;
  display_order: number;
  created_at: string;
  updated_at: string;
  seo: SeoData;
}

export interface ServiceCategory {
  id: number;
  name: string;
  slug: string;
  description: string;
  service_count: number;
  url: string;
  created_at: string;
  updated_at: string;
  seo: SeoData;
}

export interface ProjectImage {
  id: number;
  title: string;
  image_type: string;
  image: ImageData | null;
}

export interface Project {
  id: number;
  title: string;
  slug: string;
  category: string;
  category_label: string;
  description: string;
  city: RelatedItem | null;
  district: RelatedItem | null;
  coverage_city: RelatedItem | null;
  coverage_district: RelatedItem | null;
  record_type: "portfolio" | "local_solution" | string;
  is_indexable: boolean;
  image: ImageData | null;
  gallery: ProjectImage[];
  url: string;
  created_at: string;
  updated_at: string;
  seo: SeoData;
}

export interface DistrictSummary extends RelatedItem {
  sort_order: number;
  url: string;
}

export interface DistrictListItem extends DistrictSummary {
  city: RelatedItem;
  created_at: string;
  updated_at: string;
}

export interface City {
  id: number;
  name: string;
  slug: string;
  region: string;
  short_description: string;
  content: string;
  hero_title: string;
  districts: DistrictSummary[];
  url: string;
  primary_color: string;
  secondary_color: string;
  accent_color: string;
  background_color: string;
  created_at: string;
  updated_at: string;
  seo: SeoData;
  projects?: Project[];
  services?: CityService[];
  articles?: Article[];
}

export interface HomeCity {
  id: number;
  name: string;
  slug: string;
  short_description: string;
  districts: DistrictSummary[];
  district_count: number;
  url: string;
  primary_color: string;
  secondary_color: string;
  accent_color: string;
  background_color: string;
}

export interface District {
  id: number;
  name: string;
  slug: string;
  city: RelatedItem;
  projects: Project[];
  services?: CityService[];
  articles?: Article[];
  url: string;
  created_at: string;
  updated_at: string;
  seo: SeoData;
}

export interface CityService {
  id: number;
  city: RelatedItem;
  district: RelatedItem | null;
  service: Service;
  hero_title: string;
  content: string;
  benefits: string[];
  url: string;
  created_at: string;
  updated_at: string;
  seo: SeoData;
}

export interface Category {
  id: number;
  name: string;
  slug: string;
  description: string;
  url: string;
  created_at: string;
  updated_at: string;
  seo: SeoData;
  articles?: PaginatedResponse<Article>;
}

export interface Tag {
  id: number;
  name: string;
  slug: string;
  url: string;
  created_at: string;
  updated_at: string;
  seo: SeoData;
  articles?: PaginatedResponse<Article>;
}

export interface Article {
  id: number;
  title: string;
  slug: string;
  excerpt: string;
  content: string;
  image: ImageData | null;
  category: Category | null;
  tags: Tag[];
  city: RelatedItem | null;
  district: RelatedItem | null;
  is_featured: boolean;
  reading_time_minutes: number;
  url: string;
  published_at: string | null;
  created_at: string;
  updated_at: string;
  seo: SeoData;
  related_articles?: Article[];
}

export interface Testimonial {
  id: number;
  name: string;
  city_name: string;
  rating: number;
  review: string;
  source: string;
  source_url: string;
  is_verified: boolean;
}

export interface ManagedPage {
  id: number;
  title: string;
  slug: string;
  menu_title: string;
  hero_title: string;
  intro_text: string;
  body: string;
  template_key: string;
  url: string;
  created_at: string;
  updated_at: string;
  seo: SeoData;
}

export interface HomePageData {
  site: SiteSettings;
  navigation: NavigationItem[];
  hero: {
    eyebrow: string;
    kicker: string;
    title: string;
    description: string;
    image: ImageData | null;
    mobile_image: ImageData | null;
    focus_x: number;
    focus_y: number;
    overlay_opacity: number;
    video: string;
    mobile_video: string;
    poster: string;
    primary_cta: { label: string; url: string };
    secondary_cta: { label: string; url: string };
  };
  sections: HomeSection[];
  services: Service[];
  projects: Project[];
  cities: HomeCity[];
  articles: Article[];
  testimonials: Testimonial[];
  counts: {
    services: number;
    projects: number;
    portfolio_projects: number;
    local_solutions: number;
    cities: number;
    districts: number;
  };
  seo: SeoData;
}

export interface HomeSectionItem {
  id: number;
  media_type: "text" | "image" | "video" | string;
  label: string;
  title: string;
  description: string;
  alt: string;
  image: ImageData | null;
  video: string;
  mobile_video: string;
  poster: string;
  link: { label: string; url: string };
  sort_order: number;
}

export interface HomeSection {
  key: string;
  eyebrow: string;
  kicker: string;
  title: string;
  description: string;
  supporting_text: string;
  primary_cta: { label: string; url: string };
  secondary_cta: { label: string; url: string };
  media: {
    image: ImageData | null;
    video: string;
    mobile_video: string;
    poster: string;
    alt: string;
    overlay_opacity: number;
  };
  theme: "dark" | "paper" | "media" | string;
  sort_order: number;
  is_visible: boolean;
  items: HomeSectionItem[];
  updated_at: string;
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface ContactFormData {
  name: string;
  phone: string;
  email: string;
  city: string;
  district: string;
  service: string;
  project_area?: string;
  budget?: string;
  preferred_contact_time?: string;
  message: string;
  privacy_consent: boolean;
  company: string;
  page_url: string;
}

export type QuoteRequestData = ContactFormData;

export interface ArchiveStats {
  services: number;
  cities: number;
  districts: number;
  articles: number;
  projects: number;
}

export interface CalculatorTool {
  slug: string;
  title: string;
  service: string;
  description: string;
  unit: string;
  min_rate: number;
  max_rate: number;
  tips: string[];
  keywords: string;
}

export interface ComparisonTool {
  slug: string;
  title: string;
  description: string;
  left: string;
  right: string;
  left_points: string[];
  right_points: string[];
  recommendation: string;
  keywords: string;
}

export interface ToolContent {
  calculators: CalculatorTool[];
  comparisons: ComparisonTool[];
  legal_pages: Record<string, LegalPage>;
}

export interface LegalPage {
  title: string;
  description: string;
  sections: Array<[string, string]>;
}

export interface PublicUrlItem {
  url: string;
  updated_at?: string;
  priority: number;
  change_frequency: "always" | "hourly" | "daily" | "weekly" | "monthly" | "yearly" | "never";
}

export interface SubmissionResponse {
  ok: boolean;
  reference: number;
  message: string;
}
