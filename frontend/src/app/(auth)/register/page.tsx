"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { motion } from "framer-motion";
import toast from "react-hot-toast";
import { MailCheck, Loader2 } from "lucide-react";

import { ApiError, ApiPaths, api } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export default function RegisterPage() {
  const router = useRouter();
  const { register, isAuthenticated, loading: authLoading } = useAuth();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  // After a successful register that requires verification, we flip to a
  // "check your email" screen instead of redirecting to /dashboard.
  const [verifySent, setVerifySent] = useState<{
    email: string;
    message: string;
  } | null>(null);
  const [resending, setResending] = useState(false);

  useEffect(() => {
    if (!authLoading && isAuthenticated) {
      router.replace("/dashboard");
    }
  }, [authLoading, isAuthenticated, router]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      const result = await register(email, password, fullName || undefined);
      if (result.verification_required) {
        setVerifySent({ email: email.toLowerCase(), message: result.message });
        toast.success("Verification email sent");
      } else {
        toast.success("Account created!");
        router.push("/dashboard");
      }
    } catch (e) {
      const msg = e instanceof ApiError ? e.detail : "Registration failed";
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  }

  async function handleResend() {
    if (!verifySent) return;
    setResending(true);
    try {
      await api(ApiPaths.resendVerification, {
        body: { email: verifySent.email },
        auth: false,
      });
      toast.success("Verification email sent again");
    } catch (e) {
      const msg =
        e instanceof ApiError ? e.detail : "Could not resend the email";
      toast.error(msg);
    } finally {
      setResending(false);
    }
  }

  if (verifySent) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="card w-full max-w-md p-8 text-center"
      >
        <div className="mx-auto w-14 h-14 rounded-2xl bg-gradient-to-br from-brand-500 to-fuchsia-500 text-white flex items-center justify-center shadow-glow">
          <MailCheck className="w-7 h-7" />
        </div>
        <h1 className="mt-5 text-2xl font-bold">Check your inbox</h1>
        <p className="mt-2 text-slate-600 text-sm">
          We sent a verification link to{" "}
          <span className="font-semibold text-slate-900">
            {verifySent.email}
          </span>
          . Click it to activate your account, then come back to sign in.
        </p>
        <p className="mt-3 text-xs text-slate-500">{verifySent.message}</p>

        <div className="mt-6 space-y-2">
          <button
            type="button"
            onClick={handleResend}
            disabled={resending}
            className="btn-secondary w-full"
          >
            {resending ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Resending…
              </>
            ) : (
              "Resend verification email"
            )}
          </button>
          <Link href="/login" className="btn-primary w-full">
            Go to sign in
          </Link>
        </div>

        <p className="mt-6 text-xs text-slate-500">
          Didn&apos;t get it? Check your spam folder, or{" "}
          <button
            type="button"
            onClick={() => setVerifySent(null)}
            className="text-brand-600 hover:underline"
          >
            try a different email
          </button>
          .
        </p>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="card w-full max-w-md p-8"
    >
      <h1 className="text-2xl font-bold">Create your account</h1>
      <p className="text-slate-500 text-sm mt-1">
        Free plan — no credit card required. We&apos;ll email you a link to
        verify your address.
      </p>
      <form onSubmit={handleSubmit} className="mt-6 space-y-4">
        <div>
          <label className="label">Full name</label>
          <input
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            className="input"
            placeholder="Jane Doe"
          />
        </div>
        <div>
          <label className="label">Email</label>
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="input"
            placeholder="you@example.com"
          />
        </div>
        <div>
          <label className="label">Password</label>
          <input
            type="password"
            required
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="input"
            placeholder="At least 8 characters"
          />
        </div>
        <button type="submit" disabled={loading} className="btn-primary w-full">
          {loading ? "Creating account…" : "Create account"}
        </button>
      </form>
      <div className="mt-4 text-sm text-center">
        Already have an account?{" "}
        <Link href="/login" className="text-brand-600 hover:underline">
          Sign in
        </Link>
      </div>
    </motion.div>
  );
}
