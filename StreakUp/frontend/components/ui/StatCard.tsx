import type { LucideIcon } from "lucide-react";

export function StatCard({ icon: Icon, label, value }: { icon: LucideIcon; label: string; value: React.ReactNode }) {
  return (
    <div className="p-[18px] min-h-[118px] flex flex-col justify-between bg-[var(--bg2)] border border-white/12 rounded-[22px]">
      <div className="w-[42px] h-[42px] rounded-[14px] bg-[var(--bg3)] grid place-items-center text-[var(--yellow)]" aria-hidden="true">
        <Icon className="size-5" strokeWidth={2.2} />
      </div>
      <div>
        <p className="text-white/70 text-[12px] font-medium">{label}</p>
        <strong className="text-[25px] leading-none mt-1 block">{value}</strong>
      </div>
    </div>
  );
}
