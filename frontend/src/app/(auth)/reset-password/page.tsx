"use client";

import { useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
import toast from "react-hot-toast";
import { api, ApiError, ApiPaths } from "@/lib/api";

function ResetForm() {
  const router = useRouter();
  const params = useSearchParams();
  const token = params.get("token") || "";
  const [pw, setPw] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!token) return toast.error("Missing reset token");
    setLoading(true);
    try {
      await api(ApiPaths.resetPassword, {
        body: { token, new_password: pw },
        auth: false,
      });
      toast.success("Password updated. Please sign in.");
      router.push("/login");
    } catch (e) {
      const msg = e instanceof ApiError ? e.detail : "Reset failed";
      toast.error(msg);
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
      <h1 className="text-2xl font-bold">Choose a new password</h1>
      <form onSubmit={handleSubmit} className="mt-6 space-y-4">
        <div>
          <label className="label">New password</label>
          <input
            type="password"
            required
            minLength={8}
            value={pw}
            onChange={(e) => setPw(e.target.value)}
            className="input"
            placeholder="At least 8 characters"
          />
        </div>
        <button type="submit" disabled={loading} className="btn-primary w-full">
          {loading ? "Saving…" : "Update password"}
        </button>
      </form>
    </motion.div>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense>
      <ResetForm />
    </Suspense>
  );
}
