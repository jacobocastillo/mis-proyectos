"use client";

import { Check, Circle, Eye, Hourglass } from "lucide-react";
import type { ReactNode } from "react";

interface HabitRowProps {
  icon: ReactNode;
  name: string;
  subtitle: string;
  checked: boolean;
  onToggle: () => void;
  onView?: () => void;
  pending?: boolean;
  badge?: ReactNode;
}

export function HabitRow({ icon, name, subtitle, checked, onToggle, onView, pending, badge }: HabitRowProps) {
  return (
    <div className="flex items-center gap-[14px] mb-[12px] p-[16px] rounded-[20px] bg-[var(--bg2)] border border-white/12">
      <div className="w-[52px] h-[52px] rounded-[16px] bg-[var(--bg3)] grid place-items-center text-[var(--yellow)]">
        {icon}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-[6px] flex-wrap">
          <h3 className="text-[18px] font-bold leading-tight">{name}</h3>
          {badge}
        </div>
        <p className="text-white/74 text-[13px]">
          {pending ? <Hourglass className="inline size-3.5 text-[var(--yellow)] mr-1" aria-label="Pendiente de sincronización" /> : null}
          {subtitle}
        </p>
      </div>
      <div className="flex gap-[8px]">
        {onView && (
          <button
            onClick={onView}
            aria-label={`Ver detalles de ${name}`}
            className="w-[40px] h-[40px] rounded-full bg-[var(--bg3)] text-white grid place-items-center cursor-pointer transition-transform active:scale-95 hover:brightness-110 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/80"
          >
            <Eye className="size-5" aria-hidden="true" />
          </button>
        )}
        <button
          onClick={onToggle}
          aria-label={checked ? `Desmarcar ${name}` : `Marcar ${name} como completado`}
          aria-pressed={checked}
          className={`w-[40px] h-[40px] rounded-full grid place-items-center cursor-pointer transition-all active:scale-95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/80 ${
            checked ? "bg-[#36d98f] text-white" : "bg-[var(--bg3)] text-white hover:brightness-110"
          }`}
        >
          {checked ? <Check className="size-5" aria-hidden="true" /> :           <Circle className="size-5" aria-hidden="true" />}
        </button>
      </div>
    </div>
  );
}
