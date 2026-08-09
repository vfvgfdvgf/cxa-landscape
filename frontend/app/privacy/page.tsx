import type { Metadata } from "next";

import { LegalContent } from "@/components/content/LegalContent";
import { detailApi } from "@/lib/page-data";
import { staticMetadata } from "@/lib/metadata";
import type { ToolContent } from "@/types";

export const dynamic = "force-dynamic";

export const metadata: Metadata = staticMetadata("سياسة الخصوصية", "كيفية جمع واستخدام وحماية بيانات طلبات التواصل.", "/privacy/");
export default async function PrivacyPage() { const tools = await detailApi<ToolContent>("tools/", 3600, ["tools"]); return <LegalContent page={tools.legal_pages.privacy} />; }
