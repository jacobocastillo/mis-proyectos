"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_ITEMS = [
  { href: "/", emoji: "🏠", label: "Inicio" },
  { href: "/habits", emoji: "✅", label: "Hábitos" },
  { href: "/stats", emoji: "📊", label: "Stats" },
  { href: "/profile", emoji: "👤", label: "Perfil" },
];

export function BottomNav() {
  const pathname = usePathname();

  // Esconder la nav en la pantalla de temporizador
  if (pathname === "/pomodoro") {
    return null;
  }

  return (
    <nav aria-label="Navegación principal" className="absolute bottom-0 left-0 right-0 bg-[#1c0f3d]/80 backdrop-blur-xl border-t border-white/20 grid grid-cols-4 z-20" style={{ paddingBottom: "env(safe-area-inset-bottom, 0px)", height: "calc(82px + env(safe-area-inset-bottom, 0px))" }}>
      {NAV_ITEMS.map((item) => {
        const isActive =
          item.href === "/"
            ? pathname === "/"
            : pathname.startsWith(item.href);

        return (
          <Link
            key={item.href}
            href={item.href}
            aria-current={isActive ? "page" : undefined}
            className={`flex flex-col items-center justify-center font-extrabold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/80 rounded-sm ${
              isActive ? "text-white" : "text-white/60"
            }`}
          >
            <span className="block text-[27px] mb-1 leading-none" aria-hidden="true">
              {item.emoji}
            </span>
            <span className="text-xs">{item.label}</span>
          </Link>
        );
      })}
    </nav>
  );
}
