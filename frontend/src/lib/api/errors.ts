/** Error codes from the backend error envelope (guide §6.4) plus client-side ones. */
export type ApiErrorCode =
  | "VALIDATION_ERROR"
  | "AUTH_REQUIRED"
  | "AUTH_EXPIRED"
  | "INVALID_CREDENTIALS"
  | "FORBIDDEN"
  | "NOT_FOUND"
  | "TEAM_DETAIL_UNAVAILABLE"
  | "CONFLICT"
  | "RATE_LIMITED"
  | "FEEDBACK_DUPLICATE"
  | "UPSTREAM_UNAVAILABLE"
  | "INTERNAL_ERROR"
  | "NETWORK_ERROR"
  | "INVALID_RESPONSE"
  | (string & {});

const FALLBACK_MESSAGE = "일시적인 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.";

export class ApiError extends Error {
  readonly status: number;
  readonly code: ApiErrorCode;
  readonly details: Record<string, unknown>;
  /** Seconds from the Retry-After header (429). */
  readonly retryAfter: number | null;

  constructor(
    status: number,
    code: ApiErrorCode,
    message: string,
    details: Record<string, unknown> = {},
    retryAfter: number | null = null,
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
    this.retryAfter = retryAfter;
  }

  /** Per-field reasons from VALIDATION_ERROR (`details.fields`). */
  get fieldErrors(): Record<string, string> {
    const fields = this.details.fields;
    return fields && typeof fields === "object" ? (fields as Record<string, string>) : {};
  }
}

export function isApiError(error: unknown): error is ApiError {
  return error instanceof ApiError;
}

/** Converts a non-OK response into ApiError. Messages are Korean and safe to display. */
export async function toApiError(response: Response): Promise<ApiError> {
  const retryAfterHeader = response.headers.get("Retry-After");
  const retryAfter = retryAfterHeader ? Number.parseInt(retryAfterHeader, 10) || null : null;
  try {
    const body: unknown = await response.json();
    const error = (body as { error?: Record<string, unknown> } | null)?.error;
    if (error && typeof error.code === "string") {
      return new ApiError(
        response.status,
        error.code,
        typeof error.message === "string" ? error.message : FALLBACK_MESSAGE,
        (error.details as Record<string, unknown> | undefined) ?? {},
        retryAfter,
      );
    }
  } catch {
    // Non-JSON body (e.g. proxy error page): fall through to the generic error.
  }
  const code = response.status >= 500 ? "INTERNAL_ERROR" : "INVALID_RESPONSE";
  return new ApiError(response.status, code, FALLBACK_MESSAGE, {}, retryAfter);
}

export function networkError(): ApiError {
  return new ApiError(0, "NETWORK_ERROR", "네트워크 연결을 확인한 뒤 다시 시도해 주세요.");
}
