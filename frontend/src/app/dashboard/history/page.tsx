"use client";

import useSWR from "swr";
import { motion } from "framer-motion";
import { Download, FileSearch } from "lucide-react";
import toast from "react-hot-toast";
import { api, ApiPaths } from "@/lib/api";
import { Scan } from "@/lib/types";
import { formatBytes, formatDate, scoreColor } from "@/lib/utils";

const fetcher = <T,>(path: string): Promise<T> => api<T>(path);

export default function HistoryPage() {
  const { data, isLoading } = useSWR<Scan[]>(
    `${ApiPaths.history}?limit=200`,
    fetcher
  );

  async function downloadReport(id: string) {
    try {
      const blob = (await api<Blob>(ApiPaths.report(id))) as Blob;
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `scan-${id}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      toast.error("Could not download report");
    }
  }

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto w-full">
      <h1 className="text-2xl sm:text-3xl font-bold tracking-tight mb-1">
        Scan history
      </h1>
      <p className="text-slate-500 text-sm mb-5 sm:mb-6">
        All your past scans, sorted by most recent.
      </p>

      <div className="hidden md:block card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="bg-slate-50">
              <tr className="text-left text-slate-500 text-xs uppercase">
                <th className="py-3 px-4">When</th>
                <th className="py-3 px-4">Type</th>
                <th className="py-3 px-4">Source</th>
                <th className="py-3 px-4">Size</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Score</th>
                <th className="py-3 px-4">Label</th>
                <th className="py-3 px-4 text-right">Report</th>
              </tr>
            </thead>
            <tbody>
              {isLoading && (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-slate-400">
                    Loading…
                  </td>
                </tr>
              )}
              {!isLoading && (data ?? []).length === 0 && (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-slate-400">
                    <FileSearch className="w-8 h-8 mx-auto mb-2 text-slate-300" />
                    No scans yet.
                  </td>
                </tr>
              )}
              {(data ?? []).map((s, i) => (
                <motion.tr
                  key={s.id}
                  initial={{ opacity: 0, y: 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: Math.min(i * 0.02, 0.4) }}
                  className="border-t border-slate-100 hover:bg-slate-50/60"
                >
                  <td className="py-3 px-4 text-slate-600 whitespace-nowrap">
                    {formatDate(s.created_at)}
                  </td>
                  <td className="py-3 px-4 capitalize">{s.scan_type}</td>
                  <td className="py-3 px-4 truncate max-w-xs">
                    {s.original_filename ?? s.source_url ?? "—"}
                  </td>
                  <td className="py-3 px-4 whitespace-nowrap">
                    {formatBytes(s.file_size)}
                  </td>
                  <td className="py-3 px-4 capitalize text-slate-600">
                    {s.status}
                  </td>
                  <td
                    className={`py-3 px-4 font-semibold ${scoreColor(s.score)}`}
                  >
                    {s.score == null ? "—" : `${(s.score * 100).toFixed(1)}%`}
                  </td>
                  <td className="py-3 px-4">{s.label ?? "—"}</td>
                  <td className="py-3 px-4 text-right">
                    {s.status === "completed" && (
                      <button
                        onClick={() => downloadReport(s.id)}
                        className="inline-flex items-center gap-1 text-brand-600 hover:underline text-xs"
                      >
                        <Download className="w-3.5 h-3.5" /> PDF
                      </button>
                    )}
                  </td>
                </motion.tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Mobile card list */}
      <div className="md:hidden space-y-3">
        {isLoading && (
          <div className="card p-6 text-center text-slate-400 text-sm">
            Loading…
          </div>
        )}
        {!isLoading && (data ?? []).length === 0 && (
          <div className="card p-8 text-center text-slate-400">
            <FileSearch className="w-8 h-8 mx-auto mb-2 text-slate-300" />
            <div className="text-sm">No scans yet.</div>
          </div>
        )}
        {(data ?? []).map((s, i) => (
          <motion.div
            key={s.id}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: Math.min(i * 0.03, 0.4) }}
            className="card p-4"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="text-xs uppercase tracking-wide text-slate-500 mb-1">
                  {s.scan_type}
                </div>
                <div className="text-sm font-medium truncate">
                  {s.original_filename ?? s.source_url ?? "—"}
                </div>
                <div className="text-xs text-slate-500 mt-0.5">
                  {formatDate(s.created_at)}
                </div>
              </div>
              <div className="text-right shrink-0">
                <div
                  className={`text-lg font-bold ${scoreColor(s.score)}`}
                >
                  {s.score == null
                    ? "—"
                    : `${(s.score * 100).toFixed(0)}%`}
                </div>
                <div className="text-[11px] text-slate-500 capitalize">
                  {s.status}
                </div>
              </div>
            </div>
            <div className="flex items-center justify-between mt-3 pt-3 border-t border-slate-100">
              <span className="text-xs text-slate-500">
                {formatBytes(s.file_size)}
                {s.label ? ` · ${s.label}` : ""}
              </span>
              {s.status === "completed" && (
                <button
                  onClick={() => downloadReport(s.id)}
                  className="inline-flex items-center gap-1 text-brand-600 text-xs font-medium"
                >
                  <Download className="w-3.5 h-3.5" /> PDF
                </button>
              )}
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
