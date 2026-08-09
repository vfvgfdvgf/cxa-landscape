import "server-only";

import { notFound } from "next/navigation";

import { ApiError, djangoApi, optionalApi } from "@/lib/django-api";
import type { ManagedPage } from "@/types";

export function getManagedPage(identifier: string): Promise<ManagedPage | null> {
  return optionalApi<ManagedPage>(`pages/${encodeURIComponent(identifier)}/`, {
    revalidate: 300,
    tags: ["pages", `page-${identifier}`],
  });
}

export async function detailApi<T>(path: string, revalidate: number, tags: string[] = []): Promise<T> {
  try {
    return await djangoApi<T>(path, { revalidate, tags });
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) notFound();
    throw error;
  }
}

export function pageNumber(value?: string | string[]): number {
  const raw = Array.isArray(value) ? value[0] : value;
  const parsed = Number(raw || "1");
  return Number.isInteger(parsed) && parsed > 0 ? parsed : 1;
}

export function normalizeRouteParam(value: string): string {
  try {
    return decodeURIComponent(value);
  } catch {
    return value;
  }
}
