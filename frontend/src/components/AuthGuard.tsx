"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";

export default function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { isAuthenticated, loading } = useAuth();

  useEffect(() => {
    if (!loading && !isAuthenticated) {
      router.replace("/login");
    }
  }, [loading, isAuthenticated, router]);

  if (loading || !isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center text-slate-400">
        <div className="flex items-center gap-3">
          <div className="w-4 h-4 rounded-full border-2 border-slate-300 border-t-brand-600 animate-spin" />
          <span>Loading…</span>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
