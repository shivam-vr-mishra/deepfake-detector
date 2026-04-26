"use client";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const TOKEN_KEY = "df_token";
const REFRESH_KEY = "df_refresh";

// ---------------------------------------------------------------------------
// Token storage
// ---------------------------------------------------------------------------

export function setTokens(access: string, refresh: string) {
  if (typeof window === "undefined") return;
  if (!access || !refresh) return;
  localStorage.setItem(TOKEN_KEY, access);
  localStorage.setItem(REFRESH_KEY, refresh);
}

export function clearTokens() {
  if (typeof window === "undefined") return;
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  const v = localStorage.getItem(TOKEN_KEY);
  return v && v !== "undefined" && v !== "null" ? v : null;
}

export function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  const v = localStorage.getItem(REFRESH_KEY);
  return v && v !== "undefined" && v !== "null" ? v : null;
}

// ---------------------------------------------------------------------------
// Errors
// ---------------------------------------------------------------------------

export class ApiError extends Error {
  status: number;
  detail: string;
  constructor(status: number, detail: string) {
    super(detail);
    this.status = status;
    this.detail = detail;
  }
}

// ---------------------------------------------------------------------------
// Token refresh (deduplicated — concurrent 401s share a single refresh call)
// ---------------------------------------------------------------------------

let inflightRefresh: Promise<boolean> | null = null;

/**
 * Hooks for the AuthProvider to react to token refresh outcomes without
 * api.ts needing to know about React. The provider calls
 * ``onAuthStateChange(...)`` once during mount.
 */
let onAuthFailed: (() => void) | null = null;
let onAuthRefreshed: (() => void) | null = null;
export function registerAuthHandlers(handlers: {
  onAuthFailed?: () => void;
  onAuthRefreshed?: () => void;
}) {
  onAuthFailed = handlers.onAuthFailed ?? null;
  onAuthRefreshed = handlers.onAuthRefreshed ?? null;
}

export async function refreshTokens(): Promise<boolean> {
  if (inflightRefresh) return inflightRefresh;

  inflightRefresh = (async () => {
    const refreshToken = getRefreshToken();
    if (!refreshToken) return false;
    try {
      const res = await fetch(`${API_URL}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
      if (!res.ok) {
        clearTokens();
        onAuthFailed?.();
        return false;
      }
      const data = (await res.json()) as {
        access_token?: string;
        refresh_token?: string;
      };
      if (!data.access_token || !data.refresh_token) {
        clearTokens();
        onAuthFailed?.();
        return false;
      }
      setTokens(data.access_token, data.refresh_token);
      onAuthRefreshed?.();
      return true;
    } catch {
      // Network error — keep existing tokens; caller will see the original failure.
      return false;
    } finally {
      // Release the lock on next tick so any awaiting callers get the result first.
      setTimeout(() => {
        inflightRefresh = null;
      }, 0);
    }
  })();

  return inflightRefresh;
}

// ---------------------------------------------------------------------------
// Core fetch wrapper
// ---------------------------------------------------------------------------

interface RequestOptions {
  method?: string;
  body?: unknown;
  formData?: FormData;
  auth?: boolean;
  /** Internal: set to true to skip the auto-refresh-and-retry path. */
  _retry?: boolean;
}

async function rawRequest<T>(
  path: string,
  opts: RequestOptions
): Promise<T> {
  const headers: Record<string, string> = {};
  if (opts.body) headers["Content-Type"] = "application/json";

  if (opts.auth !== false) {
    const t = getToken();
    if (t) headers["Authorization"] = `Bearer ${t}`;
  }

  const res = await fetch(`${API_URL}${path}`, {
    method: opts.method ?? (opts.body || opts.formData ? "POST" : "GET"),
    headers,
    body: opts.formData ?? (opts.body ? JSON.stringify(opts.body) : undefined),
  });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const j = await res.json();
      detail = j.detail ?? detail;
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, detail);
  }

  if (res.status === 204) return undefined as T;
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) return (await res.json()) as T;
  return (await res.blob()) as T;
}

export async function api<T = unknown>(
  path: string,
  opts: RequestOptions = {}
): Promise<T> {
  try {
    return await rawRequest<T>(path, opts);
  } catch (err) {
    // Auto-refresh ONCE on 401 for authenticated requests, then retry.
    const is401 = err instanceof ApiError && err.status === 401;
    const canRetry =
      is401 && opts.auth !== false && !opts._retry && !!getRefreshToken();
    if (!canRetry) throw err;

    const ok = await refreshTokens();
    if (!ok) throw err;

    return rawRequest<T>(path, { ...opts, _retry: true });
  }
}

// ---------------------------------------------------------------------------
// API path constants
// ---------------------------------------------------------------------------

export const ApiPaths = {
  // Auth
  register: "/auth/register",
  login: "/auth/login",
  refresh: "/auth/refresh",
  forgotPassword: "/auth/forgot-password",
  resetPassword: "/auth/reset-password",
  verifyEmail: "/auth/verify-email",
  resendVerification: "/auth/resend-verification",
  me: "/auth/me",
  logout: "/auth/logout",

  // Detection
  image: "/detect/image",
  video: "/detect/video",
  audio: "/detect/audio",
  text: "/detect/text",
  url: "/detect/url",
  scan: (id: string) => `/detect/${id}`,

  // History / reports
  history: "/history",
  report: (id: string) => `/report/${id}`,

  // Subscription
  subscription: "/subscription",
  plans: "/subscription/plans",
  order: "/subscription/order",
  verify: "/subscription/verify",

  // Pay-per-scan credits
  credits: "/subscription/credits",
  creditsOrder: "/subscription/credits/order",
  creditsVerify: "/subscription/credits/verify",
};

export { API_URL };
