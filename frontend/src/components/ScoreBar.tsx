"use client";

import { motion } from "framer-motion";
import { scoreBg, scoreColor } from "@/lib/utils";

export default function ScoreBar({
  score,
  label,
  confidence,
}: {
  score: number | null | undefined;
  label?: string | null;
  confidence?: string | null;
}) {
  const pct = score == null ? 0 : Math.round(score * 100);
  return (
    <div className="space-y-2">
      <div className="flex items-baseline justify-between">
        <div className={`text-3xl font-bold ${scoreColor(score)}`}>
          {score == null ? "—" : `${pct}%`}
        </div>
        <div className="text-right">
          <div className="text-sm font-medium text-slate-700">{label ?? "—"}</div>
          {confidence && (
            <div className="text-xs text-slate-500 capitalize">
              {confidence} confidence
            </div>
          )}
        </div>
      </div>
      <div className="h-3 w-full bg-slate-100 rounded-full overflow-hidden">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.8, ease: "easeOut" }}
          className={`h-full rounded-full ${scoreBg(score)}`}
        />
      </div>
    </div>
  );
}
