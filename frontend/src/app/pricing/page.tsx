"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { Check, Sparkles, Coins } from "lucide-react";
import AnimatedBackground from "@/components/AnimatedBackground";
import MarketingHeader from "@/components/MarketingHeader";
import { cn } from "@/lib/utils";
import { useIsLoggedInOptimistic } from "@/lib/auth";

export default function PricingPage() {
  const isLoggedIn = useIsLoggedInOptimistic();

  const PLANS = [
    {
      name: "Free trial",
      price: "$0",
      desc: "For trying things out.",
      features: [
        "1 scan / day",
        "10 MB max file size",
        "Image · Audio · Text · URL",
        "PDF reports",
      ],
      cta: isLoggedIn ? "Open dashboard" : "Get started",
      href: isLoggedIn ? "/dashboard" : "/register",
    },
    {
      name: "Pay-as-you-go",
      price: "$0.50",
      priceSuffix: " / scan",
      desc: "Top up credits — no monthly commitment.",
      features: [
        "1 credit = 1 scan",
        "Flat $0.50 per credit · global rate",
        "Credits never expire",
        "All detection modules",
        "Up to 200 MB per file",
      ],
      cta: "Buy credits",
      href: isLoggedIn ? "/dashboard/subscription" : "/register",
      highlight: true,
    },
    {
      name: "Enterprise",
      price: "Custom",
      desc: "For organizations & high volume.",
      features: [
        "Volume discount on credits",
        "Up to 2 GB per file",
        "Dedicated workers",
        "SSO & audit log access",
        "Priority support",
      ],
      cta: "Talk to sales",
      href: "mailto:sales@deepfake-detector.app",
    },
  ];

  return (
    <main className="relative min-h-screen">
      <AnimatedBackground />
      <MarketingHeader />

      <section className="container mx-auto py-12 sm:py-16 text-center">
        <motion.h1
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-3xl sm:text-4xl md:text-5xl font-bold tracking-tight text-balance"
        >
          Simple, <span className="gradient-text">transparent</span> pricing
        </motion.h1>
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.1 }}
          className="mt-3 text-slate-600 max-w-xl mx-auto"
        >
          Pay <span className="font-semibold text-slate-900">only for what you scan</span>.
          Start free with 1 daily scan, then top up at a flat $0.50 per scan —
          no monthly commitment.
        </motion.p>

        <div className="mt-10 sm:mt-12 grid grid-cols-1 md:grid-cols-3 gap-4 sm:gap-6 max-w-5xl mx-auto">
          {PLANS.map((p, i) => (
            <motion.div
              key={p.name}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.08 }}
              whileHover={{ y: -6 }}
              className={cn(
                "card p-6 text-left flex flex-col relative overflow-hidden transition-all",
                p.highlight && "ring-2 ring-brand-500 shadow-glow md:-translate-y-2"
              )}
            >
              {p.highlight && (
                <div className="absolute top-3 right-3 inline-flex items-center gap-1 rounded-full bg-gradient-to-r from-brand-600 to-fuchsia-600 text-white text-[10px] font-semibold uppercase tracking-wide px-2 py-1">
                  <Sparkles className="w-3 h-3" /> Popular
                </div>
              )}
              <div className="text-sm font-semibold text-brand-600">
                {p.name}
              </div>
              <div className="mt-2 text-3xl sm:text-4xl font-bold tabular-nums">
                {p.price}
                {("priceSuffix" in p) && p.priceSuffix && (
                  <span className="text-sm font-medium text-slate-500">
                    {p.priceSuffix}
                  </span>
                )}
              </div>
              <p className="text-slate-500 text-sm mt-1">{p.desc}</p>
              <ul className="mt-5 space-y-2 text-sm text-slate-600 flex-1">
                {p.features.map((f) => (
                  <li key={f} className="flex items-start gap-2">
                    <Check className="w-4 h-4 text-emerald-600 mt-0.5 shrink-0" />
                    <span>{f}</span>
                  </li>
                ))}
              </ul>
              <Link href={p.href} className="btn-primary w-full mt-6">
                {p.highlight && <Coins className="h-4 w-4" />}
                {p.cta}
              </Link>
            </motion.div>
          ))}
        </div>

        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="mt-8 text-xs text-slate-500"
        >
          Prices exclusive of taxes where applicable. Pay securely via Razorpay.
        </motion.p>
      </section>

      <footer className="border-t border-slate-200/60 bg-white/40 backdrop-blur mt-10">
        <div className="container mx-auto py-6 text-center text-sm text-slate-500">
          © {new Date().getFullYear()} DeepFake Detector. All rights reserved.
        </div>
      </footer>
    </main>
  );
}
