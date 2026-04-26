"use client";

import { useState } from "react";
import Sidebar from "@/components/Sidebar";
import MobileTopBar from "@/components/MobileTopBar";
import AuthGuard from "@/components/AuthGuard";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <AuthGuard>
      <div className="flex bg-slate-50 min-h-screen">
        <Sidebar
          mobileOpen={mobileOpen}
          onClose={() => setMobileOpen(false)}
        />
        <div className="flex-1 min-w-0 flex flex-col">
          <MobileTopBar onOpen={() => setMobileOpen(true)} />
          <main className="flex-1 min-w-0">{children}</main>
        </div>
      </div>
    </AuthGuard>
  );
}
