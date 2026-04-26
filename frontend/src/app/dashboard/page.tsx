"use client";

import useSWR from "swr";
import Link from "next/link";
import { motion } from "framer-motion";
import {
  Activity,
  Upload,
  BarChart3,
  Sparkles,
  Coins,
} from "lucide-react";
import { api, ApiPaths } from "@/lib/api";
import { Scan, Subscription } from "@/lib/types";
import { formatDate, scoreColor } from "@/lib/utils";

const fetcher = <T,>(path: string): Promise<T> => api<T>(path);

const cardVariant = {
  hidden: { opacity: 0, y: 12 },
  show: { opacity: 1, y: 0 },
};

export default function DashboardPage() {
  const { data: sub } = useSWR<Subscription>(ApiPaths.subscription, fetcher);
  const { data: history } = useSWR<Scan[]>(`${ApiPaths.history}?limit=5`, fetcher);

  const usagePct = sub
    ? Math.min(100, (sub.used_today / sub.daily_limit) * 100)
    : 0;

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-6xl mx-auto w-full">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-6 sm:mb-8">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">
            Dashboard
          </h1>
          <p className="text-slate-500 text-sm mt-1">
            Welcome back. Here's an overview of your account.
          </p>
        </div>
        <Link
          href="/dashboard/upload"
          className="btn-primary w-full sm:w-auto group"
        >
          <Upload className="w-4 h-4 transition-transform group-hover:-translate-y-0.5" />
          New scan
        </Link>
      </div>

      <motion.div
        initial="hidden"
        animate="show"
        variants={{ show: { transition: { staggerChildren: 0.06 } } }}
        className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 mb-6 sm:mb-8"
      >
        <motion.div
          variants={cardVariant}
          className="card card-hover p-4 sm:p-5 relative overflow-hidden"
        >
          <div className="text-xs uppercase tracking-wider text-slate-500 flex items-center gap-1">
            <Sparkles className="w-3.5 h-3.5 text-brand-600" /> Plan
          </div>
          <div className="mt-1 text-2xl font-bold capitalize">
            {sub?.plan ?? "—"}
          </div>
          <div className="text-xs text-slate-500 mt-1">
            {sub ? `${sub.daily_limit}/day · max ${sub.max_file_mb}MB` : ""}
          </div>
          <div className="absolute -top-6 -right-6 h-20 w-20 rounded-full bg-brand-100/60 blur-2xl" />
        </motion.div>

        <motion.div
          variants={cardVariant}
          className="card card-hover p-4 sm:p-5"
        >
          <div className="text-xs uppercase tracking-wider text-slate-500">
            Used today
          </div>
          <div className="mt-1 text-2xl font-bold">
            {sub ? `${sub.used_today} / ${sub.daily_limit}` : "—"}
          </div>
          <div className="h-2 w-full bg-slate-100 rounded-full mt-2 overflow-hidden">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${usagePct}%` }}
              transition={{ duration: 0.9, ease: "easeOut" }}
              className="h-full bg-gradient-to-r from-brand-500 to-fuchsia-500"
            />
          </div>
        </motion.div>

        <motion.div
          variants={cardVariant}
          className="card card-hover p-4 sm:p-5 relative overflow-hidden group"
        >
          <div className="text-xs uppercase tracking-wider text-slate-500 flex items-center gap-1">
            <Coins className="w-3.5 h-3.5 text-amber-500" /> Credits
          </div>
          <div className="mt-1 text-2xl font-bold tabular-nums">
            {sub?.credits_balance ?? 0}
          </div>
          <Link
            href="/dashboard/subscription"
            className="text-xs text-brand-600 hover:underline mt-1 inline-block"
          >
            Buy more →
          </Link>
          <div className="absolute -top-6 -right-6 h-20 w-20 rounded-full bg-amber-100/60 blur-2xl group-hover:bg-amber-200/70 transition" />
        </motion.div>

        <motion.div
          variants={cardVariant}
          className="card card-hover p-4 sm:p-5"
        >
          <div className="text-xs uppercase tracking-wider text-slate-500 flex items-center gap-1">
            <Activity className="w-3.5 h-3.5 text-brand-600" /> Recent scans
          </div>
          <div className="mt-1 text-2xl font-bold">{history?.length ?? 0}</div>
          <div className="text-xs text-slate-500 mt-1">Last 5 scans</div>
        </motion.div>
      </motion.div>

      <div className="card p-4 sm:p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-semibold flex items-center gap-2">
            <BarChart3 className="w-4 h-4 text-brand-600" /> Recent scans
          </h2>
          <Link
            href="/dashboard/history"
            className="text-sm text-brand-600 hover:underline"
          >
            View all →
          </Link>
        </div>
        <div className="overflow-x-auto -mx-4 sm:mx-0 px-4 sm:px-0">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="text-left text-slate-500 text-xs uppercase">
                <th className="py-2 pr-4 whitespace-nowrap">When</th>
                <th className="py-2 pr-4 whitespace-nowrap">Type</th>
                <th className="py-2 pr-4 whitespace-nowrap">Status</th>
                <th className="py-2 pr-4 whitespace-nowrap">Score</th>
                <th className="py-2 pr-4 whitespace-nowrap">Label</th>
              </tr>
            </thead>
            <tbody>
              {(history ?? []).map((s, i) => (
                <motion.tr
                  key={s.id}
                  initial={{ opacity: 0, y: 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: Math.min(i * 0.04, 0.3) }}
                  className="border-t border-slate-100"
                >
                  <td className="py-2 pr-4 text-slate-600 whitespace-nowrap">
                    {formatDate(s.created_at)}
                  </td>
                  <td className="py-2 pr-4 capitalize">{s.scan_type}</td>
                  <td className="py-2 pr-4 capitalize text-slate-600">
                    {s.status}
                  </td>
                  <td
                    className={`py-2 pr-4 font-semibold ${scoreColor(s.score)}`}
                  >
                    {s.score == null ? "—" : `${(s.score * 100).toFixed(1)}%`}
                  </td>
                  <td className="py-2 pr-4">{s.label ?? "—"}</td>
                </motion.tr>
              ))}
              {!history?.length && (
                <tr>
                  <td colSpan={5} className="py-10 text-center text-slate-400">
                    No scans yet. Upload your first one!
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
