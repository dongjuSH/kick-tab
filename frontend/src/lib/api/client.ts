import { ApiError, networkError, toApiError } from "./errors";

export const CSRF_HEADER = "X-KickTab-Client";
const CSRF_VALUE = "web";
const UNSAFE_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);

/** Success envelope: { data, meta } (guide §6.4). */
export interface ApiEnvelope<T, M = Record<string, unknown>> {
  data: T;
  meta: M;
}

type QueryValue = string | number | boolean | null | undefined | readonly (string | number)[];

export interface ApiRequestOptions {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  query?: Record<string, QueryValue>;
  body?: unknown;
  signal?: AbortSignal;
  headers?: HeadersInit;
}

/**
 * Called once when a request fails with 401 AUTH_EXPIRED. Return true if the session was
 * refreshed and the request should be retried. Chat 02 registers the refresh logic
 * (single shared POST /api/v1/auth/refresh); until then nothing is retried.
 */
type UnauthorizedHandler = (error: ApiError) => Promise<boolean>;
let unauthorizedHandler: UnauthorizedHandler | null = null;

export function setUnauthorizedHandler(handler: UnauthorizedHandler | null): void {
  unauthorizedHandler = handler;
}

/**
 * Browser: same-origin `/api/v1/...` (proxied by next.config rewrites).
 * Server components: BACKEND_ORIGIN directly (server-only env, never NEXT_PUBLIC_).
 */
function baseUrl(): string {
  if (typeof window !== "undefined") return "";
  return (process.env.BACKEND_ORIGIN ?? "http://localhost:8000").replace(/\/+$/, "");
}

function buildUrl(path: string, query?: ApiRequestOptions["query"]): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(query ?? {})) {
    if (value === null || value === undefined || value === "") continue;
    if (Array.isArray(value)) {
      if (value.length) search.set(key, value.join(","));
    } else {
      search.set(key, String(value));
    }
  }
  const qs = search.toString();
  return `${baseUrl()}/api/v1${path}${qs ? `?${qs}` : ""}`;
}

/** Fetches `/api/v1{path}` and returns the `{ data, meta }` envelope or throws ApiError. */
export async function apiFetch<T, M = Record<string, unknown>>(
  path: string,
  options: ApiRequestOptions = {},
): Promise<ApiEnvelope<T, M>> {
  const method = options.method ?? "GET";
  const headers = new Headers(options.headers);
  headers.set("Accept", "application/json");
  if (UNSAFE_METHODS.has(method)) headers.set(CSRF_HEADER, CSRF_VALUE);
  if (options.body !== undefined) headers.set("Content-Type", "application/json");

  const send = () =>
    fetch(buildUrl(path, options.query), {
      method,
      headers,
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
      signal: options.signal,
      credentials: "same-origin",
    });

  let response: Response;
  try {
    response = await send();
    if (response.status === 401 && unauthorizedHandler) {
      const error = await toApiError(response.clone());
      if (error.code === "AUTH_EXPIRED" && (await unauthorizedHandler(error))) {
        response = await send();
      }
    }
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw networkError();
  }

  if (!response.ok) throw await toApiError(response);
  try {
    return (await response.json()) as ApiEnvelope<T, M>;
  } catch {
    throw new ApiError(response.status, "INVALID_RESPONSE", "응답을 해석하지 못했습니다.");
  }
}
