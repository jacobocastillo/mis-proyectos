"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { BarChart3, House, ListChecks, UserRound } from "lucide-react";

const NAV_ITEMS = [
  { href: "/", icon: House, label: "Inicio" },
  { href: "/habits", icon: ListChecks, label: "Hábitos" },
  { href: "/stats", icon: BarChart3, label: "Stats" },
  { href: "/profile", icon: UserRound, label: "Perfil" },
];

export function BottomNav() {
  const pathname = usePathname();

  // Esconder la nav en la pantalla de temporizador
  if (pathname === "/pomodoro") {
    return null;
  }

  return (
    <nav aria-label="Navegación principal" className="absolute bottom-0 left-0 right-0 bg-[#1d0b86] border-t border-white/15 grid grid-cols-4 z-20" style={{ paddingBottom: "env(safe-area-inset-bottom, 0px)", height: "calc(82px + env(safe-area-inset-bottom, 0px))" }}>
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
            className={`flex flex-col items-center justify-center gap-1 font-bold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/80 rounded-sm ${
              isActive ? "text-[#ffe536]" : "text-white/65 hover:text-white"
            }`}
          >
            <item.icon className="size-[21px]" aria-hidden="true" strokeWidth={2.2} />
            <span className="text-[11px]">{item.label}</span>
          </Link>
        );
      })}
    </nav>
  );
}
