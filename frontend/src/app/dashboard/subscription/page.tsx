"use client";

import { useMemo, useState } from "react";
import useSWR from "swr";
import Script from "next/script";
import { motion } from "framer-motion";
import {
  Check,
  Sparkles,
  Coins,
  Zap,
  Globe2,
  Loader2,
} from "lucide-react";
import toast from "react-hot-toast";
import { api, ApiError, ApiPaths } from "@/lib/api";
import {
  CreditOrderResponse,
  CreditWallet,
  Plan,
  Subscription,
} from "@/lib/types";
import { cn } from "@/lib/utils";

const fetcher = <T,>(path: string): Promise<T> => api<T>(path);

declare global {
  interface Window {
    Razorpay?: any;
  }
}

const BUNDLES = [10, 50, 100, 500, 1000];

export default function SubscriptionPage() {
  const { data: sub, mutate: refreshSub } = useSWR<Subscription>(
    ApiPaths.subscription,
    fetcher
  );
  const { data: wallet, mutate: refreshWallet } = useSWR<CreditWallet>(
    ApiPaths.credits,
    fetcher
  );
  const { data: plans } = useSWR<Plan[]>(ApiPaths.plans, fetcher);

  const [credits, setCredits] = useState<number>(100);
  const [buying, setBuying] = useState(false);

  const perCredit = useMemo(
    () => wallet?.credit_price_usd ?? 0.5,
    [wallet]
  );

  const total = useMemo(() => credits * perCredit, [credits, perCredit]);

  async function buyCredits() {
    if (!wallet) return;
    if (credits < wallet.min_purchase) {
      toast.error(`Minimum purchase is ${wallet.min_purchase} credits`);
      return;
    }
    if (credits > wallet.max_purchase) {
      toast.error(`Maximum purchase is ${wallet.max_purchase} credits`);
      return;
    }

    setBuying(true);
    try {
      const order = await api<CreditOrderResponse>(ApiPaths.creditsOrder, {
        body: { credits },
      });

      if (!window.Razorpay) {
        toast.error("Razorpay script not loaded yet — please retry.");
        return;
      }

      const rz = new window.Razorpay({
        key: order.razorpay_key_id,
        amount: order.amount,
        currency: order.currency,
        name: "DeepFake Detector",
        description: `${order.credits} scan credits`,
        order_id: order.order_id,
        handler: async (resp: any) => {
          try {
            await api(ApiPaths.creditsVerify, {
              body: {
                razorpay_order_id: resp.razorpay_order_id,
                razorpay_payment_id: resp.razorpay_payment_id,
                razorpay_signature: resp.razorpay_signature,
                credits: order.credits,
              },
            });
            toast.success(`+${order.credits} credits added to your wallet`);
            refreshWallet();
            refreshSub();
          } catch {
            toast.error("Verification failed");
          }
        },
        theme: { color: "#4f46e5" },
        modal: {
          ondismiss: () => setBuying(false),
        },
      });
      rz.open();
    } catch (e) {
      const msg =
        e instanceof ApiError ? e.detail : "Could not start checkout";
      toast.error(msg);
    } finally {
      setBuying(false);
    }
  }

  async function upgrade(plan: Plan) {
    if (plan.plan === "free") return;
    try {
      const order = await api<any>(ApiPaths.order, {
        body: { plan: plan.plan },
      });

      const rz = new window.Razorpay({
        key: order.razorpay_key_id,
        amount: order.amount,
        currency: order.currency,
        name: "DeepFake Detector",
        description: `Upgrade to ${plan.plan}`,
        order_id: order.order_id,
        handler: async (resp: any) => {
          try {
            await api(ApiPaths.verify, {
              body: {
                razorpay_order_id: resp.razorpay_order_id,
                razorpay_payment_id: resp.razorpay_payment_id,
                razorpay_signature: resp.razorpay_signature,
                plan: plan.plan,
              },
            });
            toast.success(`Upgraded to ${plan.plan}!`);
            refreshSub();
          } catch {
            toast.error("Verification failed");
          }
        },
        theme: { color: "#4f46e5" },
      });
      if (!window.Razorpay) {
        toast.error("Razorpay script not loaded");
        return;
      }
      rz.open();
    } catch (e) {
      const msg = e instanceof ApiError ? e.detail : "Could not start checkout";
      toast.error(msg);
    }
  }

  const remainingFree = sub
    ? Math.max(sub.daily_limit - sub.used_today, 0)
    : 0;

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-5xl mx-auto w-full">
      <Script src="https://checkout.razorpay.com/v1/checkout.js" />

      <h1 className="text-2xl sm:text-3xl font-bold tracking-tight mb-1">
        Subscription
      </h1>
      <p className="text-slate-500 text-sm mb-5 sm:mb-6">
        Pay only for what you scan — top up credits anytime.
      </p>

      {/* Wallet hero */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-brand-600 via-brand-700 to-fuchsia-700 text-white p-5 sm:p-7 mb-6 sm:mb-8 shadow-glow-lg"
      >
        <div className="absolute inset-0 bg-grid opacity-15" />
        <div className="absolute -top-12 -right-12 h-44 w-44 rounded-full bg-white/10 blur-3xl animate-blob" />
        <div className="absolute -bottom-12 -left-12 h-44 w-44 rounded-full bg-fuchsia-300/20 blur-3xl animate-blob" />

        <div className="relative grid sm:grid-cols-3 gap-4 sm:gap-6">
          <div>
            <div className="flex items-center gap-2 text-xs uppercase tracking-wider text-brand-100">
              <Coins className="h-4 w-4" /> Credit balance
            </div>
            <div className="mt-1 text-4xl sm:text-5xl font-extrabold tabular-nums">
              {wallet?.balance ?? "—"}
            </div>
            <div className="text-xs text-brand-100 mt-1">
              1 credit = 1 scan
            </div>
          </div>

          <div>
            <div className="text-xs uppercase tracking-wider text-brand-100">
              Free today
            </div>
            <div className="mt-1 text-2xl sm:text-3xl font-bold">
              {sub ? `${remainingFree}/${sub.daily_limit}` : "—"}
            </div>
            <div className="text-xs text-brand-100 mt-1 capitalize">
              {sub?.plan ?? "—"} plan · resets at midnight
            </div>
          </div>

          <div>
            <div className="text-xs uppercase tracking-wider text-brand-100">
              Pay-per-scan
            </div>
            <div className="mt-1 text-2xl sm:text-3xl font-bold flex items-baseline gap-1">
              <span>${(wallet?.credit_price_usd ?? 0.5).toFixed(2)}</span>
              <span className="text-sm font-medium opacity-80">/ scan</span>
            </div>
            <div className="text-xs text-brand-100 mt-1">
              Flat global rate · no expiry
            </div>
          </div>
        </div>
      </motion.div>

      {/* Buy credits */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.05 }}
        className="card p-5 sm:p-6 mb-6 sm:mb-8"
      >
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-5">
          <div>
            <h2 className="text-lg sm:text-xl font-semibold flex items-center gap-2">
              <Zap className="h-5 w-5 text-brand-600" /> Buy scan credits
            </h2>
            <p className="text-sm text-slate-500 mt-0.5">
              ${perCredit.toFixed(2)} per credit · no expiry · use across all
              detection modules.
            </p>
          </div>
        </div>

        <div className="flex flex-wrap gap-2 mb-4">
          {BUNDLES.map((b) => (
            <button
              key={b}
              onClick={() => setCredits(b)}
              className={cn(
                "px-3 sm:px-4 py-2 rounded-xl text-sm font-medium border transition",
                credits === b
                  ? "border-brand-500 bg-brand-50 text-brand-700"
                  : "border-slate-200 hover:border-brand-300 text-slate-600"
              )}
            >
              {b} credits
            </button>
          ))}
        </div>

        <div className="grid sm:grid-cols-[1fr_auto] gap-3 sm:gap-4 sm:items-end">
          <div>
            <label className="label">
              Or enter a custom amount
              {wallet && (
                <span className="ml-1 text-xs text-slate-400 font-normal">
                  (min {wallet.min_purchase}, max{" "}
                  {wallet.max_purchase.toLocaleString()})
                </span>
              )}
            </label>
            <div className="relative">
              <input
                type="number"
                min={wallet?.min_purchase ?? 10}
                max={wallet?.max_purchase ?? 100000}
                value={credits}
                onChange={(e) =>
                  setCredits(Math.max(0, Number(e.target.value) || 0))
                }
                className="input pr-20"
              />
              <span className="absolute right-3 top-1/2 -translate-y-1/2 text-sm text-slate-400">
                credits
              </span>
            </div>
          </div>

          <div className="rounded-xl border border-slate-200 bg-slate-50/60 p-3 sm:p-4 sm:min-w-[14rem]">
            <div className="text-xs uppercase tracking-wider text-slate-500">
              You pay
            </div>
            <motion.div
              key={total}
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.2 }}
              className="text-2xl sm:text-3xl font-bold tabular-nums"
            >
              ${total.toFixed(2)}
            </motion.div>
            <div className="text-xs text-slate-500 mt-0.5">
              ${perCredit.toFixed(2)} × {credits.toLocaleString()} credits
            </div>
          </div>
        </div>

        <button
          onClick={buyCredits}
          disabled={buying || credits < (wallet?.min_purchase ?? 10)}
          className="btn-primary w-full mt-5"
        >
          {buying ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" /> Opening checkout…
            </>
          ) : (
            <>
              <Coins className="h-4 w-4" /> Buy {credits.toLocaleString()}{" "}
              credits
            </>
          )}
        </button>

        <div className="mt-3 flex items-center gap-2 text-xs text-slate-500">
          <Globe2 className="h-3.5 w-3.5" /> Secure checkout via Razorpay · USD
          billing.
        </div>
      </motion.div>

      {/* Heavy users — monthly plans */}
      <div className="mb-3">
        <h3 className="text-base sm:text-lg font-semibold">
          Heavy user? Try a monthly plan
        </h3>
        <p className="text-sm text-slate-500">
          Unlimited daily quotas — credits not required at this volume.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 sm:gap-6">
        {(plans ?? []).map((p, i) => {
          const current = sub?.plan === p.plan;
          const featured = p.plan === "pro";
          return (
            <motion.div
              key={p.plan}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.06 }}
              whileHover={{ y: -4 }}
              className={cn(
                "card p-5 sm:p-6 flex flex-col relative overflow-hidden transition-all",
                current && "ring-2 ring-brand-500 shadow-glow",
                featured && !current && "border-brand-300"
              )}
            >
              {featured && !current && (
                <div className="absolute top-3 right-3 inline-flex items-center gap-1 rounded-full bg-gradient-to-r from-brand-600 to-fuchsia-600 text-white text-[10px] font-semibold uppercase tracking-wide px-2 py-1">
                  <Sparkles className="w-3 h-3" /> Popular
                </div>
              )}
              <div className="capitalize text-sm font-semibold text-brand-600">
                {p.plan}
              </div>
              <div className="mt-2 text-3xl font-bold">
                {p.price_inr === 0 ? "Free" : `₹${p.price_inr}`}
                {p.price_inr > 0 && (
                  <span className="text-sm font-medium text-slate-500">
                    {" "}
                    /month
                  </span>
                )}
              </div>
              <ul className="mt-5 space-y-2 text-sm text-slate-600 flex-1">
                <li className="flex items-center gap-2">
                  <Check className="w-4 h-4 text-emerald-600 shrink-0" />
                  {p.daily_limit} {p.plan === "free" ? "scan" : "scans"} / day
                </li>
                <li className="flex items-center gap-2">
                  <Check className="w-4 h-4 text-emerald-600 shrink-0" />
                  Up to {p.max_file_mb} MB per file
                </li>
                <li className="flex items-center gap-2">
                  <Check className="w-4 h-4 text-emerald-600 shrink-0" />
                  Pay-per-scan after limit
                </li>
                <li className="flex items-center gap-2">
                  <Check className="w-4 h-4 text-emerald-600 shrink-0" />
                  ClamAV virus scanning · PDF reports
                </li>
              </ul>
              <button
                onClick={() => upgrade(p)}
                disabled={current || p.plan === "free"}
                className="btn-primary w-full mt-6 disabled:bg-slate-300 disabled:hover:shadow-sm"
              >
                {current
                  ? "Current plan"
                  : p.plan === "free"
                  ? "Free forever"
                  : "Upgrade"}
              </button>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
