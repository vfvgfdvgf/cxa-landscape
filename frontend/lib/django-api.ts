import "server-only";

function resolveApiUrl(): string {
  const explicit = process.env.DJANGO_API_URL?.trim();
  if (explicit) return explicit.replace(/\/$/, "");
  const privateHost = process.env.DJANGO_API_HOST?.trim();
  if (privateHost) {
    const privatePort = process.env.DJANGO_API_PORT?.trim() || "10000";
    return `http://${privateHost}:${privatePort}`;
  }
  return "https://nakheel-najd.onrender.com";
}

const API_URL = resolveApiUrl();
const TRANSIENT_STATUSES = new Set([502, 503, 504]);

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

interface RequestOptions {
  revalidate?: number;
  tags?: string[];
  method?: "GET" | "POST";
  body?: unknown;
  authenticated?: boolean;
  submissionClient?: string;
}

function responseDetail(payload: unknown): string | null {
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) return null;
  const fields = payload as Record<string, unknown>;
  if (typeof fields.detail === "string") return fields.detail;
  for (const value of Object.values(fields)) {
    if (typeof value === "string") return value;
    if (Array.isArray(value) && typeof value[0] === "string") return value[0];
  }
  return null;
}

async function requestOnce<T>(path: string, options: RequestOptions): Promise<T> {
  const method = options.method || "GET";
  const headers: HeadersInit = { Accept: "application/json" };
  if (options.body !== undefined) headers["Content-Type"] = "application/json";
  if (options.authenticated) {
    const secret = process.env.DJANGO_API_SECRET || process.env.FRONTEND_API_SECRET;
    if (!secret) throw new ApiError("إعداد الاتصال الآمن غير مكتمل.", 500);
    headers["X-Frontend-Secret"] = secret;
  }
  if (options.submissionClient) {
    headers["X-Submission-Client"] = options.submissionClient;
  }

  const response = await fetch(`${API_URL}/api/v1/${path.replace(/^\//, "")}`, {
    method,
    headers,
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
    signal: AbortSignal.timeout(12000),
    ...(method === "GET"
      ? { next: { revalidate: options.revalidate ?? 300, tags: options.tags } }
      : { cache: "no-store" as const }),
  });

  if (!response.ok) {
    let detail = "تعذر تحميل البيانات المطلوبة.";
    try {
      const payload: unknown = await response.json();
      detail = responseDetail(payload) || detail;
    } catch {
      // The public error stays intentionally generic for non-JSON upstream errors.
    }
    throw new ApiError(detail, response.status);
  }
  return (await response.json()) as T;
}

export async function djangoApi<T>(path: string, options: RequestOptions = {}): Promise<T> {
  try {
    return await requestOnce<T>(path, options);
  } catch (error) {
    const transient =
      (error instanceof ApiError && TRANSIENT_STATUSES.has(error.status)) ||
      (error instanceof Error && (error.name === "TimeoutError" || error.name === "TypeError"));
    if (!transient || options.method === "POST") throw error;
    return requestOnce<T>(path, options);
  }
}

export async function optionalApi<T>(path: string, options: RequestOptions = {}): Promise<T | null> {
  try {
    return await djangoApi<T>(path, options);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return null;
    const message = error instanceof Error ? error.message : "Unknown upstream error";
    process.stderr.write(`[django-api] ${path}: ${message}\n`);
    return null;
  }
}

export function withQuery(path: string, values: Record<string, string | number | undefined>): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(values)) {
    if (value !== undefined && value !== "") params.set(key, String(value));
  }
  const query = params.toString();
  return query ? `${path}?${query}` : path;
}
