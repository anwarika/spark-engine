/**
 * Typed error classes for the Spark SDK.
 *
 * All errors extend SparkError so you can catch broadly or specifically:
 *
 *   try {
 *     await spark.generate({ prompt });
 *   } catch (e) {
 *     if (e instanceof SparkRateLimitError) {
 *       // retry after e.retryAfter seconds
 *     } else if (e instanceof SparkAuthError) {
 *       // re-auth the user
 *     } else if (e instanceof SparkError) {
 *       // generic Spark problem
 *     }
 *   }
 */

export class SparkError extends Error {
  constructor(
    public readonly status: number,
    public readonly detail: string,
  ) {
    super(`Spark API error ${status}: ${detail}`);
    this.name = "SparkError";
  }
}

/** Returned when the API key is missing, invalid, or revoked (401 / 403). */
export class SparkAuthError extends SparkError {
  constructor(detail: string, status = 401) {
    super(status, detail);
    this.name = "SparkAuthError";
  }
}

/** Returned when an API key lacks a required scope (403). */
export class SparkPermissionError extends SparkError {
  constructor(
    public readonly missingScope: string,
    detail: string,
  ) {
    super(403, detail);
    this.name = "SparkPermissionError";
  }
}

/** Returned when a rate limit is exceeded (429). */
export class SparkRateLimitError extends SparkError {
  /** Seconds until the client can retry. */
  public readonly retryAfter: number;

  constructor(detail: string, retryAfter: number) {
    super(429, detail);
    this.name = "SparkRateLimitError";
    this.retryAfter = retryAfter;
  }
}

/** Returned when the LLM or compiler fails to produce a valid component (422). */
export class SparkGenerationError extends SparkError {
  constructor(detail: string) {
    super(422, detail);
    this.name = "SparkGenerationError";
  }
}

/** Returned when a request exceeds the client-side timeout. */
export class SparkTimeoutError extends SparkError {
  constructor(public readonly timeoutMs: number) {
    super(408, `Request timed out after ${timeoutMs}ms`);
    this.name = "SparkTimeoutError";
  }
}

/**
 * Map an HTTP status + detail string to the most specific SparkError subclass.
 * Used internally by SparkClient.
 */
export function classifyError(
  status: number,
  detail: string,
  headers?: Headers,
): SparkError {
  if (status === 401) return new SparkAuthError(detail, 401);
  if (status === 403) {
    const scopeMatch = detail.match(/scope[:\s]+['"]?(\w+)/i);
    return new SparkPermissionError(scopeMatch?.[1] ?? "unknown", detail);
  }
  if (status === 429) {
    const retryAfter = headers
      ? parseInt(headers.get("Retry-After") ?? "60", 10)
      : 60;
    return new SparkRateLimitError(detail, retryAfter);
  }
  if (status === 422) return new SparkGenerationError(detail);
  return new SparkError(status, detail);
}
