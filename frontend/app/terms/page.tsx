import type { Metadata } from "next";

import { LegalContent } from "@/components/content/LegalContent";
import { detailApi } from "@/lib/page-data";
import { staticMetadata } from "@/lib/metadata";
import type { ToolContent } from "@/types";

export const dynamic = "force-dynamic";

export const metadata: Metadata = staticMetadata("الشروط والأحكام", "شروط استخدام الموقع وطلبات الخدمة وعروض الأسعار.", "/terms/");
export default async function TermsPage() { const tools = await detailApi<ToolContent>("tools/", 3600, ["tools"]); return <LegalContent page={tools.legal_pages.terms} />; }
