"use client";

import Link from "next/link";
import { Menu, ShieldCheck } from "lucide-react";

export default function MobileTopBar({ onOpen }: { onOpen: () => void }) {
  return (
    <div className="md:hidden sticky top-0 z-30 flex items-center justify-between border-b border-slate-200 bg-white/80 backdrop-blur-lg px-4 py-3">
      <button
        onClick={onOpen}
        aria-label="Open menu"
        className="inline-flex h-10 w-10 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-700 active:scale-95 transition"
      >
        <Menu className="h-5 w-5" />
      </button>
      <Link
        href="/"
        className="flex items-center gap-2 text-base font-bold tracking-tight text-brand-700"
      >
        <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-br from-brand-500 to-fuchsia-500 text-white">
          <ShieldCheck className="h-3.5 w-3.5" />
        </span>
        DeepFake Detector
      </Link>
      <div className="w-10" aria-hidden />
    </div>
  );
}
