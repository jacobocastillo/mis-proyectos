"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import type { ReactNode } from "react";
import { hasSavedSession } from "@/services/auth/authService";
import { NetworkStatusBanner } from "@/components/feedback/NetworkStatusBanner";
import { AchievementToast } from "@/components/feedback/AchievementToast";
import { BottomNav } from "@/components/layout/BottomNav";

export default function DashboardLayout({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [sessionReady, setSessionReady] = useState(false);

  useEffect(() => {
    // Middleware is the primary guard on the web. This client check keeps
    // offline/mobile shells honest when request-time protection is unavailable.
    if (!hasSavedSession()) {
      router.replace("/login");
    } else {
      setSessionReady(true);
    }
  }, [router]);

  if (!sessionReady) {
    return (
      <div className="absolute inset-0 flex items-center justify-center">
        <div className="size-8 border-2 border-white border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <>
      {/* Skip to main content — keyboard and AT users */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-[100] focus:rounded-lg focus:bg-white focus:px-4 focus:py-2 focus:text-sm focus:font-bold focus:text-[#1c0f3d]"
      >
        Saltar al contenido principal
      </a>

      {/* Red online/offline indicator — visible on all pages */}
      <NetworkStatusBanner />

      {/* Achievement unlock toast — shown whenever any page triggers it */}
      <AchievementToast />

      {/* Main content - handles the scrolling area like the .screen class in HTML */}
      <main id="main-content" tabIndex={-1} aria-label="Contenido principal" className="absolute inset-0 overflow-y-auto overflow-x-hidden pt-7 px-[22px] pb-[100px] z-10 animate-[enter_0.28s_ease_both]">
        {children}
      </main>

      {/* Bottom Navigation Bar */}
      <BottomNav />
    </>
  );
}
