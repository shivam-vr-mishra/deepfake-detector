import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatBytes(bytes: number | null | undefined): string {
  if (!bytes && bytes !== 0) return "—";
  const units = ["B", "KB", "MB", "GB"];
  let i = 0;
  let n = bytes;
  while (n >= 1024 && i < units.length - 1) {
    n /= 1024;
    i++;
  }
  return `${n.toFixed(n >= 100 || i === 0 ? 0 : 1)} ${units[i]}`;
}

export function formatDate(d: string | Date | null | undefined): string {
  if (!d) return "—";
  const date = typeof d === "string" ? new Date(d) : d;
  return date.toLocaleString();
}

export function scoreColor(score: number | null | undefined): string {
  if (score == null) return "text-slate-400";
  if (score >= 0.75) return "text-rose-600";
  if (score >= 0.5) return "text-amber-600";
  if (score >= 0.25) return "text-emerald-600";
  return "text-emerald-700";
}

export function scoreBg(score: number | null | undefined): string {
  if (score == null) return "bg-slate-200";
  if (score >= 0.75) return "bg-rose-500";
  if (score >= 0.5) return "bg-amber-500";
  if (score >= 0.25) return "bg-emerald-500";
  return "bg-emerald-600";
}
