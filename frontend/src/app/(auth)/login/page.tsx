"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { motion } from "framer-motion";
import toast from "react-hot-toast";
import { MailWarning, Loader2 } from "lucide-react";

import { ApiError, ApiPaths, api } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const { login, isAuthenticated, loading: authLoading } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [unverified, setUnverified] = useState<string | null>(null);
  const [resending, setResending] = useState(false);

  // If already signed in, skip the login screen on direct navigation.
  useEffect(() => {
    if (!authLoading && isAuthenticated) {
      router.replace("/dashboard");
    }
  }, [authLoading, isAuthenticated, router]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setUnverified(null);
    try {
      await login(email, password);
      toast.success("Welcome back");
      router.push("/dashboard");
    } catch (e) {
      if (
        e instanceof ApiError &&
        e.status === 403 &&
        /not verified/i.test(e.detail)
      ) {
        // Surface a focused "verify your email" panel instead of a toast.
        setUnverified(email.toLowerCase());
      } else {
        const msg = e instanceof ApiError ? e.detail : "Login failed";
        toast.error(msg);
      }
    } finally {
      setLoading(false);
    }
  }

  async function handleResend() {
    if (!unverified) return;
    setResending(true);
    try {
      await api(ApiPaths.resendVerification, {
        body: { email: unverified },
        auth: false,
      });
      toast.success("Verification email sent");
    } catch (e) {
      const msg =
        e instanceof ApiError ? e.detail : "Could not resend the email";
      toast.error(msg);
    } finally {
      setResending(false);
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="card w-full max-w-md p-8"
    >
      <h1 className="text-2xl font-bold">Welcome back</h1>
      <p className="text-slate-500 text-sm mt-1">
        Sign in to your DeepFake Detector account.
      </p>

      {unverified && (
        <div
          role="alert"
          className="mt-5 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900"
        >
          <div className="flex items-start gap-2">
            <MailWarning className="w-4 h-4 mt-0.5 shrink-0 text-amber-600" />
            <div className="flex-1">
              <p className="font-semibold">Please verify your email</p>
              <p className="mt-1 text-amber-800/90">
                We sent a verification link to{" "}
                <span className="font-medium">{unverified}</span>. Click it to
                activate your account, then sign in here.
              </p>
              <button
                type="button"
                onClick={handleResend}
                disabled={resending}
                className="mt-3 inline-flex items-center gap-2 rounded-lg bg-amber-600 hover:bg-amber-700 text-white px-3 py-1.5 text-xs font-medium disabled:opacity-60"
              >
                {resending ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    Sending…
                  </>
                ) : (
                  "Resend verification email"
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      <form onSubmit={handleSubmit} className="mt-6 space-y-4">
        <div>
          <label className="label">Email</label>
          <input
            type="email"
            required
            value={email}
            onChange={(e) => {
              setEmail(e.target.value);
              if (unverified) setUnverified(null);
            }}
            className="input"
            placeholder="you@example.com"
          />
        </div>
        <div>
          <label className="label">Password</label>
          <input
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="input"
            placeholder="••••••••"
          />
        </div>
        <button type="submit" disabled={loading} className="btn-primary w-full">
          {loading ? "Signing in…" : "Sign in"}
        </button>
      </form>
      <div className="mt-4 flex items-center justify-between text-sm">
        <Link href="/forgot-password" className="text-brand-600 hover:underline">
          Forgot password?
        </Link>
        <Link href="/register" className="text-slate-600 hover:underline">
          Create account →
        </Link>
      </div>
    </motion.div>
  );
}
