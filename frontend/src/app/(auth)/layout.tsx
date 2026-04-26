import Link from "next/link";
import { ShieldCheck } from "lucide-react";
import AnimatedBackground from "@/components/AnimatedBackground";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <main className="relative min-h-screen flex flex-col">
      <AnimatedBackground variant="auth" />
      <header className="container mx-auto py-5 sm:py-6">
        <Link
          href="/"
          className="inline-flex items-center gap-2 text-lg sm:text-xl font-bold tracking-tight text-brand-700"
        >
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-brand-500 to-fuchsia-500 text-white shadow-glow">
            <ShieldCheck className="h-4 w-4" />
          </span>
          DeepFake Detector
        </Link>
      </header>
      <div className="flex-1 flex items-center justify-center px-4 pb-12 sm:pb-16">
        {children}
      </div>
    </main>
  );
}
