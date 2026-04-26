"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import toast from "react-hot-toast";
import Link from "next/link";
import { api, ApiPaths } from "@/lib/api";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      await api(ApiPaths.forgotPassword, { body: { email }, auth: false });
      setSent(true);
      toast.success("If the account exists, a reset link was emailed.");
    } catch {
      toast.error("Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="card w-full max-w-md p-8"
    >
      <h1 className="text-2xl font-bold">Reset your password</h1>
      <p className="text-slate-500 text-sm mt-1">
        We'll email you a link to reset your password.
      </p>
      {sent ? (
        <div className="mt-6 rounded-xl bg-emerald-50 border border-emerald-200 p-4 text-emerald-800 text-sm">
          If the email is registered, a reset link has been sent.
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="mt-6 space-y-4">
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
          <button type="submit" disabled={loading} className="btn-primary w-full">
            {loading ? "Sending…" : "Send reset link"}
          </button>
        </form>
      )}
      <div className="mt-4 text-sm text-center">
        <Link href="/login" className="text-brand-600 hover:underline">
          ← Back to sign in
        </Link>
      </div>
    </motion.div>
  );
}
