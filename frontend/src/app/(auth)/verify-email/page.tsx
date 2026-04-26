"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { motion } from "framer-motion";
import toast from "react-hot-toast";
import { CheckCircle2, Loader2, MailWarning, XCircle } from "lucide-react";

import { ApiError, ApiPaths, api } from "@/lib/api";

type Status = "verifying" | "success" | "error" | "missing";

function VerifyEmailInner() {
  const params = useSearchParams();
  const token = params.get("token") || "";

  const [status, setStatus] = useState<Status>(token ? "verifying" : "missing");
  const [errorMsg, setErrorMsg] = useState<string>("");

  const [resendEmail, setResendEmail] = useState("");
  const [resending, setResending] = useState(false);

  // Guard against React 18 strict-mode double effect: we only want to call
  // /verify-email once per token. POSTing a single-use token twice will
  // succeed both times (it's idempotent on our backend), but skipping the
  // second call avoids confusing logs.
  const fired = useRef(false);

  useEffect(() => {
    if (!token || fired.current) return;
    fired.current = true;
    (async () => {
      try {
        await api(ApiPaths.verifyEmail, {
          body: { token },
          auth: false,
        });
        setStatus("success");
      } catch (e) {
        const detail =
          e instanceof ApiError
            ? e.detail
            : "We couldn't verify this link. It may have expired.";
        setErrorMsg(detail);
        setStatus("error");
      }
    })();
  }, [token]);

  async function handleResend(e: React.FormEvent) {
    e.preventDefault();
    if (!resendEmail) return;
    setResending(true);
    try {
      await api(ApiPaths.resendVerification, {
        body: { email: resendEmail.toLowerCase() },
        auth: false,
      });
      toast.success("If that account exists, a new link is on its way");
    } catch (err) {
      const msg =
        err instanceof ApiError ? err.detail : "Could not resend the email";
      toast.error(msg);
    } finally {
      setResending(false);
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="card w-full max-w-md p-8 text-center"
    >
      {status === "verifying" && (
        <>
          <div className="mx-auto w-14 h-14 rounded-2xl bg-slate-100 text-slate-600 flex items-center justify-center">
            <Loader2 className="w-7 h-7 animate-spin" />
          </div>
          <h1 className="mt-5 text-2xl font-bold">Verifying your email…</h1>
          <p className="mt-2 text-slate-600 text-sm">
            One moment while we confirm your link.
          </p>
        </>
      )}

      {status === "success" && (
        <>
          <div className="mx-auto w-14 h-14 rounded-2xl bg-gradient-to-br from-emerald-500 to-teal-500 text-white flex items-center justify-center shadow-glow">
            <CheckCircle2 className="w-7 h-7" />
          </div>
          <h1 className="mt-5 text-2xl font-bold">Email verified</h1>
          <p className="mt-2 text-slate-600 text-sm">
            Your account is now active. You can sign in and start scanning.
          </p>
          <Link href="/login" className="btn-primary w-full mt-6">
            Continue to sign in
          </Link>
        </>
      )}

      {(status === "error" || status === "missing") && (
        <>
          <div className="mx-auto w-14 h-14 rounded-2xl bg-rose-100 text-rose-600 flex items-center justify-center">
            {status === "error" ? (
              <XCircle className="w-7 h-7" />
            ) : (
              <MailWarning className="w-7 h-7" />
            )}
          </div>
          <h1 className="mt-5 text-2xl font-bold">
            {status === "error"
              ? "Link invalid or expired"
              : "Verify your email"}
          </h1>
          <p className="mt-2 text-slate-600 text-sm">
            {status === "error"
              ? errorMsg
              : "Enter your email below and we'll send a fresh verification link."}
          </p>

          <form onSubmit={handleResend} className="mt-6 space-y-3 text-left">
            <div>
              <label className="label">Email</label>
              <input
                type="email"
                required
                value={resendEmail}
                onChange={(e) => setResendEmail(e.target.value)}
                className="input"
                placeholder="you@example.com"
              />
            </div>
            <button
              type="submit"
              disabled={resending}
              className="btn-primary w-full"
            >
              {resending ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Sending…
                </>
              ) : (
                "Send a new verification link"
              )}
            </button>
          </form>

          <div className="mt-4 text-sm text-slate-500">
            Already verified?{" "}
            <Link href="/login" className="text-brand-600 hover:underline">
              Sign in
            </Link>
          </div>
        </>
      )}
    </motion.div>
  );
}

export default function VerifyEmailPage() {
  return (
    <Suspense>
      <VerifyEmailInner />
    </Suspense>
  );
}
