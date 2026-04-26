"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import {
  ImageIcon,
  Video,
  Mic,
  FileText,
  Link2,
  ShieldCheck,
  Zap,
  LockKeyhole,
  Upload,
  ScanLine,
  FileCheck2,
  Sparkles,
  ArrowRight,
  LayoutDashboard,
} from "lucide-react";
import AnimatedBackground from "@/components/AnimatedBackground";
import MarketingHeader from "@/components/MarketingHeader";
import { useIsLoggedInOptimistic } from "@/lib/auth";

const FEATURES = [
  {
    icon: ImageIcon,
    label: "Images",
    desc: "Detect GAN/diffusion-generated photos with frame analysis.",
    color: "from-rose-500 to-orange-500",
  },
  {
    icon: Video,
    label: "Videos",
    desc: "Frame-level deepfake analysis & temporal consistency.",
    color: "from-fuchsia-500 to-pink-500",
  },
  {
    icon: Mic,
    label: "Audio",
    desc: "Spot synthesized voices & TTS clones in seconds.",
    color: "from-violet-500 to-brand-500",
  },
  {
    icon: FileText,
    label: "Text",
    desc: "Identify AI-generated writing across LLM families.",
    color: "from-brand-500 to-blue-500",
  },
  {
    icon: Link2,
    label: "URLs",
    desc: "Analyze social posts, articles and shared media.",
    color: "from-accent-500 to-emerald-500",
  },
];

const SECURITY = [
  {
    icon: ShieldCheck,
    title: "ClamAV Virus Scanning",
    desc: "Every upload is scanned before any AI model touches it.",
  },
  {
    icon: LockKeyhole,
    title: "Isolated Storage",
    desc: "Files stored as UUIDs in a private MinIO bucket — never executed.",
  },
  {
    icon: Zap,
    title: "Async Processing",
    desc: "Heavy work queued through Redis + Celery for instant API responses.",
  },
];

const STEPS = [
  {
    icon: Upload,
    title: "Upload",
    desc: "Drop an image, video, audio file, paste text, or share a URL.",
  },
  {
    icon: ScanLine,
    title: "Analyze",
    desc: "Our models score the content for AI manipulation in seconds.",
  },
  {
    icon: FileCheck2,
    title: "Report",
    desc: "Get a downloadable PDF report with confidence and explanation.",
  },
];

const STATS = [
  { value: "99.2%", label: "Detection accuracy" },
  { value: "<3s", label: "Avg. response time" },
  { value: "5", label: "Content modalities" },
  { value: "256-bit", label: "Encryption" },
];

const containerStagger = {
  hidden: {},
  show: { transition: { staggerChildren: 0.08 } },
};
const item = {
  hidden: { opacity: 0, y: 16 },
  show: { opacity: 1, y: 0, transition: { duration: 0.5, ease: "easeOut" as const } },
};

export default function Home() {
  const isLoggedIn = useIsLoggedInOptimistic();

  return (
    <main className="relative min-h-screen">
      <AnimatedBackground />
      <MarketingHeader />

      <section className="container mx-auto pt-12 sm:pt-20 pb-16 sm:pb-24 text-center">
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="inline-flex items-center gap-2 rounded-full border border-brand-200/70 bg-white/70 backdrop-blur px-4 py-1.5 text-xs sm:text-sm font-medium text-brand-700 shadow-sm"
        >
          <Sparkles className="h-3.5 w-3.5" />
          Pay-per-scan: $0.50 / scan · 1 free scan every day
        </motion.div>

        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="mt-6 text-4xl sm:text-6xl md:text-7xl font-bold tracking-tight text-slate-900 text-balance"
        >
          Detect <span className="gradient-text">AI-generated</span>
          <br className="hidden sm:block" /> content in seconds.
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15, duration: 0.6 }}
          className="mt-5 sm:mt-6 text-base sm:text-lg text-slate-600 max-w-2xl mx-auto px-2 text-balance"
        >
          A production-grade SaaS that screens images, videos, audio, text and URLs
          for AI manipulation — protected by enterprise-grade security: ClamAV virus
          scanning, file sandboxing, and rate limiting.
        </motion.p>

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="mt-8 sm:mt-10 flex flex-col sm:flex-row items-center justify-center gap-3"
        >
          {isLoggedIn ? (
            <Link
              href="/dashboard"
              className="btn-primary px-6 py-3 text-base w-full sm:w-auto group"
            >
              <LayoutDashboard className="h-4 w-4" />
              Go to dashboard
              <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
            </Link>
          ) : (
            <>
              <Link
                href="/register"
                className="btn-primary px-6 py-3 text-base w-full sm:w-auto group"
              >
                Start free
                <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
              </Link>
              <Link
                href="/login"
                className="btn-secondary px-6 py-3 text-base w-full sm:w-auto"
              >
                Sign in
              </Link>
            </>
          )}
        </motion.div>

        <motion.div
          variants={containerStagger}
          initial="hidden"
          animate="show"
          className="mt-12 sm:mt-16 grid grid-cols-2 md:grid-cols-4 gap-3 sm:gap-4 max-w-3xl mx-auto"
        >
          {STATS.map((s) => (
            <motion.div
              key={s.label}
              variants={item}
              className="card p-3 sm:p-4 text-left"
            >
              <div className="text-xl sm:text-2xl font-bold text-slate-900">
                {s.value}
              </div>
              <div className="text-[11px] sm:text-xs text-slate-500 mt-1">
                {s.label}
              </div>
            </motion.div>
          ))}
        </motion.div>
      </section>

      <section id="features" className="container mx-auto pb-16 sm:pb-24 scroll-mt-20">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.4 }}
          transition={{ duration: 0.5 }}
          className="text-center mb-10 sm:mb-14"
        >
          <h2 className="text-3xl sm:text-4xl font-bold tracking-tight">
            One platform, every modality
          </h2>
          <p className="mt-3 text-slate-600 max-w-xl mx-auto">
            Whatever the format, we'll tell you whether it was made by a human or
            an algorithm.
          </p>
        </motion.div>

        <motion.div
          variants={containerStagger}
          initial="hidden"
          whileInView="show"
          viewport={{ once: true, amount: 0.2 }}
          className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3 sm:gap-4"
        >
          {FEATURES.map(({ icon: Icon, label, desc, color }) => (
            <motion.div
              key={label}
              variants={item}
              whileHover={{ y: -6 }}
              className="card card-hover p-5 text-left group relative overflow-hidden"
            >
              <div
                className={`inline-flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br ${color} text-white shadow-sm`}
              >
                <Icon className="h-5 w-5" />
              </div>
              <div className="mt-3 font-semibold">{label}</div>
              <p className="text-sm text-slate-500 mt-1">{desc}</p>
              <div className="absolute -bottom-12 -right-12 h-24 w-24 rounded-full bg-brand-200/30 blur-2xl opacity-0 group-hover:opacity-100 transition" />
            </motion.div>
          ))}
        </motion.div>
      </section>

      <section id="how" className="container mx-auto pb-16 sm:pb-24 scroll-mt-20">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.4 }}
          transition={{ duration: 0.5 }}
          className="text-center mb-10 sm:mb-14"
        >
          <h2 className="text-3xl sm:text-4xl font-bold tracking-tight">
            How it works
          </h2>
          <p className="mt-3 text-slate-600">Three steps. No setup.</p>
        </motion.div>

        <div className="grid sm:grid-cols-3 gap-4 sm:gap-6 relative">
          <div
            aria-hidden
            className="hidden sm:block absolute top-10 left-[16%] right-[16%] h-px bg-gradient-to-r from-transparent via-brand-300 to-transparent"
          />
          {STEPS.map(({ icon: Icon, title, desc }, i) => (
            <motion.div
              key={title}
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.3 }}
              transition={{ delay: i * 0.1, duration: 0.5 }}
              className="card p-6 text-center relative"
            >
              <div className="relative mx-auto h-14 w-14 rounded-2xl bg-gradient-to-br from-brand-500 to-fuchsia-500 text-white flex items-center justify-center shadow-glow">
                <Icon className="h-6 w-6" />
                <span className="absolute -top-2 -right-2 h-6 w-6 rounded-full bg-white text-brand-700 text-xs font-bold flex items-center justify-center border border-brand-200 shadow-sm">
                  {i + 1}
                </span>
              </div>
              <h3 className="mt-4 font-semibold text-lg">{title}</h3>
              <p className="mt-1 text-sm text-slate-600">{desc}</p>
            </motion.div>
          ))}
        </div>
      </section>

      <section className="container mx-auto pb-16 sm:pb-24">
        <motion.h2
          initial={{ opacity: 0, y: 12 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.4 }}
          className="text-3xl sm:text-4xl font-bold text-center mb-10 sm:mb-12 tracking-tight"
        >
          Built with security at the core
        </motion.h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 sm:gap-6">
          {SECURITY.map(({ icon: Icon, title, desc }, i) => (
            <motion.div
              key={title}
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.3 }}
              transition={{ delay: i * 0.08, duration: 0.5 }}
              whileHover={{ y: -4 }}
              className="card p-6 card-hover"
            >
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-brand-100 to-brand-200 flex items-center justify-center text-brand-700">
                <Icon className="w-6 h-6" />
              </div>
              <h3 className="mt-4 font-semibold text-lg">{title}</h3>
              <p className="mt-2 text-slate-600 text-sm">{desc}</p>
            </motion.div>
          ))}
        </div>
      </section>

      <section className="container mx-auto pb-20">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.3 }}
          className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-brand-600 via-brand-700 to-fuchsia-700 px-6 py-12 sm:px-12 sm:py-16 text-center text-white shadow-glow-lg"
        >
          <div className="absolute inset-0 bg-grid opacity-15" />
          <div className="absolute -top-20 -left-20 h-60 w-60 rounded-full bg-white/10 blur-3xl animate-blob" />
          <div className="absolute -bottom-20 -right-20 h-60 w-60 rounded-full bg-fuchsia-300/20 blur-3xl animate-blob" />
          <div className="relative">
            <h2 className="text-3xl sm:text-4xl font-bold tracking-tight text-balance">
              Stop guessing. Start verifying.
            </h2>
            <p className="mt-3 text-brand-100 max-w-xl mx-auto">
              Get 1 free scan every day. Beyond that, pay a flat $0.50 per scan —
              no monthly commitment.
            </p>
            <div className="mt-7 flex flex-col sm:flex-row items-center justify-center gap-3">
              {isLoggedIn ? (
                <Link
                  href="/dashboard"
                  className="inline-flex items-center justify-center gap-2 rounded-xl bg-white text-brand-700 hover:bg-brand-50 font-semibold px-6 py-3 transition hover:-translate-y-0.5 shadow-sm w-full sm:w-auto"
                >
                  <LayoutDashboard className="h-4 w-4" />
                  Open dashboard
                  <ArrowRight className="h-4 w-4" />
                </Link>
              ) : (
                <Link
                  href="/register"
                  className="inline-flex items-center justify-center gap-2 rounded-xl bg-white text-brand-700 hover:bg-brand-50 font-semibold px-6 py-3 transition hover:-translate-y-0.5 shadow-sm w-full sm:w-auto"
                >
                  Create free account
                  <ArrowRight className="h-4 w-4" />
                </Link>
              )}
              <Link
                href="/pricing"
                className="inline-flex items-center justify-center gap-2 rounded-xl border border-white/30 hover:bg-white/10 text-white font-semibold px-6 py-3 transition w-full sm:w-auto"
              >
                See pricing
              </Link>
            </div>
          </div>
        </motion.div>
      </section>

      <footer className="border-t border-slate-200/60 bg-white/40 backdrop-blur">
        <div className="container mx-auto py-6 sm:py-8 flex flex-col sm:flex-row items-center justify-between gap-3 text-sm text-slate-500">
          <div>© {new Date().getFullYear()} DeepFake Detector. All rights reserved.</div>
          <div className="flex items-center gap-4">
            <Link href="/pricing" className="hover:text-slate-900 transition">
              Pricing
            </Link>
            {isLoggedIn ? (
              <Link
                href="/dashboard"
                className="hover:text-slate-900 transition"
              >
                Dashboard
              </Link>
            ) : (
              <>
                <Link
                  href="/login"
                  className="hover:text-slate-900 transition"
                >
                  Sign in
                </Link>
                <Link
                  href="/register"
                  className="hover:text-slate-900 transition"
                >
                  Get started
                </Link>
              </>
            )}
          </div>
        </div>
      </footer>
    </main>
  );
}
