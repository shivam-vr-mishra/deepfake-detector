"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import { useEffect } from "react";
import {
  LayoutDashboard,
  Upload,
  History,
  CreditCard,
  LogOut,
  ShieldCheck,
  X,
} from "lucide-react";
import { useAuth } from "@/lib/auth";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/dashboard/upload", label: "New scan", icon: Upload },
  { href: "/dashboard/history", label: "History", icon: History },
  { href: "/dashboard/subscription", label: "Subscription", icon: CreditCard },
];

function NavList({
  pathname,
  onNavigate,
}: {
  pathname: string;
  onNavigate?: () => void;
}) {
  return (
    <nav className="flex-1 px-3 space-y-1">
      {NAV.map(({ href, label, icon: Icon }) => {
        const active = pathname === href;
        return (
          <Link
            key={href}
            href={href}
            onClick={onNavigate}
            className={cn(
              "relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all duration-200",
              active
                ? "bg-gradient-to-r from-brand-50 to-brand-100/60 text-brand-700"
                : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
            )}
          >
            {active && (
              <motion.span
                layoutId="sidebar-active"
                className="absolute left-0 top-1/2 -translate-y-1/2 h-6 w-1 rounded-r-full bg-brand-600"
                transition={{ type: "spring", stiffness: 400, damping: 30 }}
              />
            )}
            <Icon className="w-4 h-4" />
            {label}
          </Link>
        );
      })}
    </nav>
  );
}

function Brand() {
  return (
    <div className="px-6 py-5">
      <Link
        href="/"
        className="flex items-center gap-2 text-lg font-bold tracking-tight text-brand-700"
      >
        <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-brand-500 to-fuchsia-500 text-white shadow-glow">
          <ShieldCheck className="h-4 w-4" />
        </span>
        DeepFake Detector
      </Link>
      <div className="mt-1 ml-10 flex items-center gap-1.5 text-[11px] text-emerald-600">
        <ShieldCheck className="w-3 h-3" /> ClamAV protected
      </div>
    </div>
  );
}

export default function Sidebar({
  mobileOpen = false,
  onClose,
}: {
  mobileOpen?: boolean;
  onClose?: () => void;
}) {
  const pathname = usePathname();
  const { logout } = useAuth();

  useEffect(() => {
    document.body.style.overflow = mobileOpen ? "hidden" : "";
    return () => {
      document.body.style.overflow = "";
    };
  }, [mobileOpen]);

  return (
    <>
      <aside className="w-64 shrink-0 bg-white/70 backdrop-blur border-r border-slate-200 min-h-screen sticky top-0 hidden md:flex md:flex-col">
        <Brand />
        <NavList pathname={pathname} />
        <div className="p-3 border-t border-slate-100">
          <button
            onClick={logout}
            className="w-full flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-slate-600 hover:bg-slate-50 hover:text-rose-600 transition"
          >
            <LogOut className="w-4 h-4" />
            Sign out
          </button>
        </div>
      </aside>

      <AnimatePresence>
        {mobileOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              onClick={onClose}
              className="md:hidden fixed inset-0 z-40 bg-slate-900/50 backdrop-blur-sm"
            />
            <motion.aside
              initial={{ x: "-100%" }}
              animate={{ x: 0 }}
              exit={{ x: "-100%" }}
              transition={{ type: "spring", stiffness: 320, damping: 32 }}
              className="md:hidden fixed inset-y-0 left-0 z-50 w-72 max-w-[85%] bg-white border-r border-slate-200 flex flex-col shadow-2xl"
            >
              <div className="flex items-center justify-between pr-4">
                <Brand />
                <button
                  onClick={onClose}
                  aria-label="Close menu"
                  className="inline-flex h-9 w-9 items-center justify-center rounded-lg hover:bg-slate-100 text-slate-600"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>
              <NavList pathname={pathname} onNavigate={onClose} />
              <div className="p-3 border-t border-slate-100 safe-bottom">
                <button
                  onClick={() => {
                    logout();
                    onClose?.();
                  }}
                  className="w-full flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-slate-600 hover:bg-slate-50 hover:text-rose-600 transition"
                >
                  <LogOut className="w-4 h-4" />
                  Sign out
                </button>
              </div>
            </motion.aside>
          </>
        )}
      </AnimatePresence>
    </>
  );
}
