"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { LayoutDashboard, Menu, X, ShieldCheck } from "lucide-react";
import { cn } from "@/lib/utils";
import { useIsLoggedInOptimistic } from "@/lib/auth";

const NAV = [
  { href: "/#features", label: "Features" },
  { href: "/#how", label: "How it works" },
  { href: "/pricing", label: "Pricing" },
];

export default function MarketingHeader() {
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const isLoggedIn = useIsLoggedInOptimistic();

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    document.body.style.overflow = open ? "hidden" : "";
    return () => {
      document.body.style.overflow = "";
    };
  }, [open]);

  return (
    <header
      className={cn(
        "sticky top-0 z-40 w-full transition-all duration-300",
        scrolled
          ? "bg-white/70 backdrop-blur-lg border-b border-slate-200/60 shadow-sm"
          : "bg-transparent"
      )}
    >
      <div className="container mx-auto flex items-center justify-between py-4">
        <Link
          href="/"
          className="flex items-center gap-2 text-lg sm:text-xl font-bold tracking-tight text-brand-700"
          onClick={() => setOpen(false)}
        >
          <span className="relative flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-brand-500 to-fuchsia-500 text-white shadow-glow">
            <ShieldCheck className="h-4 w-4" />
            <span className="absolute inset-0 rounded-lg ring-2 ring-brand-400/40 animate-pulse-ring" />
          </span>
          DeepFake Detector
        </Link>

        <nav className="hidden md:flex items-center gap-1">
          {NAV.map((n) => (
            <Link
              key={n.href}
              href={n.href}
              className="px-3 py-2 text-sm text-slate-600 hover:text-slate-900 rounded-lg hover:bg-slate-100/70 transition"
            >
              {n.label}
            </Link>
          ))}
        </nav>

        <div className="hidden md:flex items-center gap-2">
          {isLoggedIn ? (
            <Link href="/dashboard" className="btn-primary text-sm">
              <LayoutDashboard className="h-4 w-4" />
              Dashboard
            </Link>
          ) : (
            <>
              <Link href="/login" className="btn-ghost text-sm">
                Sign in
              </Link>
              <Link href="/register" className="btn-primary text-sm">
                Get started
              </Link>
            </>
          )}
        </div>

        <button
          onClick={() => setOpen((v) => !v)}
          className="md:hidden inline-flex h-10 w-10 items-center justify-center rounded-lg border border-slate-200 bg-white/70 text-slate-700 active:scale-95 transition"
          aria-label={open ? "Close menu" : "Open menu"}
          aria-expanded={open}
        >
          {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </div>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.2 }}
            className="md:hidden border-t border-slate-200/70 bg-white/95 backdrop-blur-lg"
          >
            <div className="container mx-auto py-4 flex flex-col gap-1">
              {NAV.map((n) => (
                <Link
                  key={n.href}
                  href={n.href}
                  onClick={() => setOpen(false)}
                  className="px-3 py-3 text-base text-slate-700 rounded-lg hover:bg-slate-100"
                >
                  {n.label}
                </Link>
              ))}
              <div
                className={cn(
                  "mt-2 gap-2",
                  isLoggedIn ? "grid grid-cols-1" : "grid grid-cols-2"
                )}
              >
                {isLoggedIn ? (
                  <Link
                    href="/dashboard"
                    onClick={() => setOpen(false)}
                    className="btn-primary"
                  >
                    <LayoutDashboard className="h-4 w-4" />
                    Dashboard
                  </Link>
                ) : (
                  <>
                    <Link
                      href="/login"
                      onClick={() => setOpen(false)}
                      className="btn-secondary"
                    >
                      Sign in
                    </Link>
                    <Link
                      href="/register"
                      onClick={() => setOpen(false)}
                      className="btn-primary"
                    >
                      Get started
                    </Link>
                  </>
                )}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  );
}
