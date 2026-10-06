export function StatCard({ emoji, label, value }: { emoji: string; label: string; value: React.ReactNode }) {
  return (
    <div className="p-[18px] min-h-[118px] flex flex-col justify-between bg-white/14 border border-white/20 rounded-[28px] shadow-[0_22px_55px_rgba(18,5,72,0.32)] backdrop-blur-[18px]">
      <div className="w-[50px] h-[50px] rounded-[18px] bg-white/18 grid place-items-center text-[30px]" aria-hidden="true">
        {emoji}
      </div>
      <div>
        <p className="text-white/74 text-[13px]">{label}</p>
        <strong className="text-[28px] leading-none">{value}</strong>
      </div>
    </div>
  );
}
