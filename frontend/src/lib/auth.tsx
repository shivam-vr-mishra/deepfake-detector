"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { useRouter } from "next/navigation";

import {
  api,
  ApiError,
  ApiPaths,
  clearTokens,
  getRefreshToken,
  getToken,
  registerAuthHandlers,
  setTokens,
} from "@/lib/api";
import type { User } from "@/lib/types";

export interface RegisterResult {
  user: User;
  /** When true, the backend has emailed a verification link — do not log in. */
  verification_required: boolean;
  message: string;
}

interface AuthState {
  user: User | null;
  /** True while the initial session check is in flight. */
  loading: boolean;
  /** True iff a non-null user is loaded. */
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (
    email: string,
    password: string,
    fullName?: string
  ) => Promise<RegisterResult>;
  logout: () => void;
  /** Force a re-fetch of /auth/me using current tokens. */
  reloadUser: () => Promise<void>;
}

const AuthContext = createContext<AuthState | undefined>(undefined);

interface TokenPair {
  access_token: string;
  refresh_token: string;
}

/**
 * Decode the ``exp`` (UNIX seconds) claim out of a JWT without verifying
 * the signature — purely so we can decide locally whether the access
 * token is already expired and skip a guaranteed-failing /auth/me call.
 */
function jwtExpSeconds(token: string): number | null {
  try {
    const part = token.split(".")[1];
    if (!part) return null;
    const padded = part.replace(/-/g, "+").replace(/_/g, "/");
    const decoded = atob(padded);
    const json = JSON.parse(decoded) as { exp?: number };
    return typeof json.exp === "number" ? json.exp : null;
  } catch {
    return null;
  }
}

function isExpired(token: string, skewSeconds = 5): boolean {
  const exp = jwtExpSeconds(token);
  if (!exp) return false;
  return Math.floor(Date.now() / 1000) >= exp - skewSeconds;
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const mounted = useRef(true);

  // ---- Stable handlers ---------------------------------------------------
  const reloadUser = useCallback(async () => {
    try {
      const me = await api<User>(ApiPaths.me);
      if (mounted.current) setUser(me);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        clearTokens();
        if (mounted.current) setUser(null);
      } else {
        // Network error: keep the previous user so the UI doesn't flap.
        // The guarded API will retry naturally.
        // eslint-disable-next-line no-console
        console.warn("auth.reloadUser failed", err);
      }
    }
  }, []);

  const logout = useCallback(() => {
    clearTokens();
    setUser(null);
    // Best-effort server notify — fire-and-forget.
    void api(ApiPaths.logout, { method: "POST" }).catch(() => undefined);
    router.replace("/login");
  }, [router]);

  const login = useCallback(
    async (email: string, password: string) => {
      const tokens = await api<TokenPair>(ApiPaths.login, {
        body: { email, password },
        auth: false,
      });
      setTokens(tokens.access_token, tokens.refresh_token);
      const me = await api<User>(ApiPaths.me);
      if (mounted.current) setUser(me);
    },
    []
  );

  const register = useCallback(
    async (
      email: string,
      password: string,
      fullName?: string
    ): Promise<RegisterResult> => {
      const result = await api<RegisterResult>(ApiPaths.register, {
        body: { email, password, full_name: fullName },
        auth: false,
      });
      // If the backend skipped verification (verification_required=false), we
      // auto-login as a convenience; otherwise the caller must show the
      // "check your email" UX.
      if (!result.verification_required) {
        try {
          await login(email, password);
        } catch {
          /* If auto-login fails (rare), the caller can still navigate to
             /login manually using the returned message. */
        }
      }
      return result;
    },
    [login]
  );

  // ---- Initial session bootstrap ----------------------------------------
  useEffect(() => {
    mounted.current = true;

    let cancelled = false;
    (async () => {
      const access = getToken();
      const refresh = getRefreshToken();

      if (!access && !refresh) {
        if (!cancelled) setLoading(false);
        return;
      }

      // If access is expired but we have refresh, try to renew up front
      // so /auth/me succeeds on the first try.
      if (access && isExpired(access) && refresh) {
        try {
          const tokens = await fetchRefresh(refresh);
          if (tokens) setTokens(tokens.access_token, tokens.refresh_token);
        } catch {
          /* fall through to /auth/me which will trigger the api retry path */
        }
      }

      try {
        const me = await api<User>(ApiPaths.me);
        if (!cancelled) setUser(me);
      } catch (err) {
        if (err instanceof ApiError && err.status === 401) {
          clearTokens();
          if (!cancelled) setUser(null);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
      mounted.current = false;
    };
  }, []);

  // ---- Cross-tab sync via the storage event -----------------------------
  useEffect(() => {
    function onStorage(e: StorageEvent) {
      if (e.key === "df_token" || e.key === "df_refresh") {
        // Another tab logged in/out. Reflect that here.
        if (!getToken()) {
          setUser(null);
        } else {
          void reloadUser();
        }
      }
    }
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, [reloadUser]);

  // ---- Bridge api.ts events into the provider --------------------------
  useEffect(() => {
    registerAuthHandlers({
      onAuthFailed: () => setUser(null),
      onAuthRefreshed: () => void reloadUser(),
    });
    return () => registerAuthHandlers({});
  }, [reloadUser]);

  const value = useMemo<AuthState>(
    () => ({
      user,
      loading,
      isAuthenticated: !!user,
      login,
      register,
      logout,
      reloadUser,
    }),
    [user, loading, login, register, logout, reloadUser]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used inside <AuthProvider>");
  }
  return ctx;
}

/**
 * Returns ``true`` if the user is *probably* logged in. Useful for marketing
 * pages where we want to swap "Sign in / Get started" for "Dashboard" without
 * waiting for the full /auth/me bootstrap to finish.
 *
 * Behaviour:
 *   - First render (SSR & initial hydration): ``false`` (avoids hydration
 *     mismatch — server doesn't know about localStorage).
 *   - Right after mount: ``true`` if a token exists in localStorage.
 *   - Once /auth/me completes: reflects the real ``isAuthenticated``.
 */
export function useIsLoggedInOptimistic(): boolean {
  const { isAuthenticated, loading } = useAuth();
  const [hasToken, setHasToken] = useState(false);
  useEffect(() => {
    setHasToken(!!getToken());
  }, []);
  return isAuthenticated || (loading && hasToken);
}

// ---------------------------------------------------------------------------
// Internal helper — calls /auth/refresh directly without going through api()
// (so it can run during the initial bootstrap, before context is mounted).
// ---------------------------------------------------------------------------

async function fetchRefresh(
  refreshToken: string
): Promise<TokenPair | null> {
  const baseUrl =
    process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const res = await fetch(`${baseUrl}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
  if (!res.ok) return null;
  return (await res.json()) as TokenPair;
}
