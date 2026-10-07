"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  Coffee,
  Flame,
  Hourglass,
  Plus,
  Settings,
  Snowflake,
  Sparkles,
  Target,
  Timer,
  TrendingUp,
  Trophy,
  icons,
} from "lucide-react";
import { fetchTodayHabits, toggleCheckin } from "@/services/checkins/checkinService";
import { fetchStatsSummary } from "@/services/stats/statsService";
import { fetchSharedGroups } from "@/services/social/socialService";
import { showAchievementToast } from "@/components/feedback/AchievementToast";
import { getSession } from "@/services/auth/authService";
import { getPendingOps } from "@/services/sync/syncQueue";
import { getHabitTargetSummary, SECTION_ICONS, VALIDATION_TYPE_LABELS } from "@/types/habits";
import type { TodayHabit } from "@/types/checkins";
import type { StatsSummary } from "@/types/stats";

import { Button } from "@/components/ui/button";
import { Mascot } from "@/components/Mascot";
import { StatCard } from "@/components/ui/StatCard";
import { HabitRow } from "@/components/ui/HabitRow";

const EMPTY_STATS: StatsSummary = {
  streak: 0,
  today_completed: 0,
  today_total: 0,
  completion_rate: 0,
  total_xp: 0,
  level: 1,
  validations_today: 0,
};

const POMODORO_THEMES = [
  { key: "fire", label: "Fuego", icon: Flame, tone: "text-[var(--yellow)]" },
  { key: "candle", label: "Vela", icon: Coffee, tone: "text-[var(--orange)]" },
  { key: "ice", label: "Hielo", icon: Snowflake, tone: "text-cyan-200" },
  { key: "hourglass", label: "Reloj", icon: Hourglass, tone: "text-violet-200" },
];

export default function DashboardHomePage() {
  const router = useRouter();
  const [stats, setStats] = useState<StatsSummary>(EMPTY_STATS);
  const [todayHabits, setTodayHabits] = useState<TodayHabit[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [updatingHabitId, setUpdatingHabitId] = useState<number | null>(null);
  const [pendingHabitIds, setPendingHabitIds] = useState<Set<number>>(new Set());
  const [sharedCatalogIds, setSharedCatalogIds] = useState<Set<number>>(new Set());

  function refreshPendingIds(habits?: TodayHabit[]) {
    const session = getSession();
    const userId = Number(session?.user.id ?? 0);
    if (userId <= 0) return;
    const today = new Date().toISOString().slice(0, 10);
    const ops = getPendingOps(userId);
    const ids = new Set(
      ops
        .filter((op) => op.kind === "toggle_checkin" && op.payload.date === today)
        .map((op) => op.payload.habit_id as number),
    );
    // Only mark habits that are currently checked (visible as pending)
    const checkedIds = new Set((habits ?? todayHabits).filter((h) => h.checked_today).map((h) => h.id));
    setPendingHabitIds(new Set([...ids].filter((id) => checkedIds.has(id))));
  }

  const fetchData = useCallback(async (showSpinner = false) => {
    if (showSpinner) setLoading(true);
    try {
      const [statsData, habitsData] = await Promise.all([fetchStatsSummary(), fetchTodayHabits()]);
      setStats(statsData);
      setTodayHabits(habitsData);
      setError("");
      refreshPendingIds(habitsData);

      // Groups fetch is non-blocking: badge failure must not break the page
      fetchSharedGroups()
        .then((groups) => {
          const ids = new Set<number>();
          for (const group of groups) {
            if (group.habit_id !== null && group.habit_id !== undefined) {
              ids.add(group.habit_id);
            }
          }
          setSharedCatalogIds(ids);
        })
        .catch(() => {/* no badge if groups can't load */});
    } catch (err) {
      setError(err instanceof Error && err.message.trim() ? err.message : "No se pudieron cargar tus datos reales.");
    } finally {
      if (showSpinner) setLoading(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    void fetchData(true);
  }, [fetchData]);

  async function handleToggleHabit(habitId: number) {
    setUpdatingHabitId(habitId);
    setError("");
    try {
      const result = await toggleCheckin({ habit_id: habitId });
      setTodayHabits((currentHabits) => {
        const updated = currentHabits.map((habit) =>
          habit.id === result.habit_id ? { ...habit, checked_today: result.checked } : habit,
        );
        refreshPendingIds(updated);
        return updated;
      });
      result.new_achievements?.forEach((achievement) => showAchievementToast(achievement));
      try {
        setStats(await fetchStatsSummary());
      } catch (err) {
        setError(err instanceof Error && err.message.trim() ? `${err.message} El check-in sí se guardó correctamente.` : "El check-in se guardó, pero no se pudieron refrescar las estadísticas.");
      }
    } catch (err) {
      setError(err instanceof Error && err.message.trim() ? err.message : "No se pudo actualizar el check-in.");
    } finally {
      setUpdatingHabitId(null);
    }
  }

  function handleHabitAction(habit: TodayHabit) {
    if (updatingHabitId !== null) return;
    if (habit.validation_type) {
      router.push(`/habits/validate?id=${habit.id}`);
      return;
    }
    void handleToggleHabit(habit.id);
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]" role="status" aria-label="Cargando datos">
        <div className="size-8 border-2 border-white border-t-transparent rounded-full animate-spin" aria-hidden="true" />
      </div>
    );
  }

  return (
    <div className="space-y-[24px]">
      {/* Top Header */}
      <div className="flex items-center justify-between gap-[14px]">
        <div>
          <h2 className="text-[30px] leading-[1.05] font-bold">Streak Up</h2>
          <p className="text-white/74 text-[15px]">Hoy es un gran día para avanzar</p>
        </div>
        <button onClick={() => router.push("/profile")} aria-label="Ir a perfil y configuración" className="w-[48px] h-[48px] rounded-[15px] bg-[var(--bg2)] text-white grid place-items-center cursor-pointer transition-transform active:scale-95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--yellow)]">
          <Settings className="size-6" aria-hidden="true" />
        </button>
      </div>

      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-100">
          {error}
        </div>
      )}

      {/* Hero Card */}
      <div className="bg-[var(--bg2)] border border-white/12 rounded-[24px] relative overflow-hidden text-center px-[22px] pt-[24px] pb-[22px]">
        <div className="mx-auto mb-3 size-11 rounded-[14px] bg-[var(--bg3)] text-[var(--yellow)] grid place-items-center">
          <Sparkles className="size-5" aria-hidden="true" />
        </div>
        
        <h1 className="text-[32px] leading-[1.08] tracking-[-0.6px] font-bold">
          Impulsa tu<br />
          <span className="text-[var(--yellow)]">productividad</span>
        </h1>

        <Mascot />

        <Button variant="sacro" size="sacro" onClick={() => router.push("/pomodoro")}>
          Inicia una sesión
        </Button>
      </div>

      {/* Mensaje del día */}
      {stats.feedback?.message && (
        <div className="rounded-[18px] border border-white/12 bg-[var(--bg2)] px-5 py-4 flex gap-3 items-start">
          <Sparkles className="size-5 shrink-0 mt-[1px] text-[var(--yellow)]" aria-hidden="true" />
          <p className="text-white/90 text-[14px] leading-[1.6]">{stats.feedback.message}</p>
        </div>
      )}

      {/* Stats Grid */}
      <div className="grid grid-cols-2 gap-[14px]">
        <StatCard icon={Flame} label="Racha" value={`${stats.streak} días`} />
        <StatCard icon={Target} label="Hoy" value={`${stats.today_completed}/${stats.today_total}`} />
        <StatCard icon={Trophy} label="XP" value={stats.total_xp} />
        <StatCard icon={TrendingUp} label="Tasa" value={`${stats.completion_rate}%`} />
      </div>

      {/* Pomodoro Modes */}
      <div>
        <div className="flex items-center justify-between mt-[24px] mb-[12px]">
          <h3 className="text-[18px] font-bold">Modo Pomodoro</h3>
          <button onClick={() => router.push("/pomodoro")} aria-label="Ir al temporizador Pomodoro" className="w-[48px] h-[48px] rounded-[15px] bg-[var(--bg2)] text-[var(--yellow)] grid place-items-center cursor-pointer transition-transform active:scale-95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--yellow)]">
            <Timer className="size-5" aria-hidden="true" />
          </button>
        </div>
        <div className="grid grid-cols-2 gap-[12px]">
          {POMODORO_THEMES.map((theme) => (
            <Link key={theme.key} href={`/pomodoro?theme=${theme.key}`}>
              <div className="p-[16px] rounded-[20px] text-center border border-white/12 bg-[var(--bg2)] cursor-pointer min-h-[104px] hover:bg-[var(--bg3)] transition-colors">
                <span className={`mx-auto mb-2 size-12 rounded-[15px] bg-[var(--bg3)] grid place-items-center ${theme.tone}`}>
                  <theme.icon className="size-6" aria-hidden="true" />
                </span>
                <b className="text-[16px] font-bold">{theme.label}</b>
              </div>
            </Link>
          ))}
        </div>
      </div>

      {/* Habits List */}
      <div>
        <div className="flex items-center justify-between mt-[24px] mb-[12px]">
          <h3 className="text-[18px] font-bold">Hoy</h3>
          <button onClick={() => router.push("/habits/new")} aria-label="Crear nuevo hábito" className="w-[48px] h-[48px] rounded-[15px] bg-[var(--bg2)] text-[24px] grid place-items-center cursor-pointer transition-transform active:scale-95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--yellow)]">
            <Plus className="size-6 text-white" aria-hidden="true" />
          </button>
        </div>

        {todayHabits.length === 0 ? (
          <div className="text-center p-8 bg-[var(--bg2)] rounded-[24px] border border-white/20">
            <p className="text-white/80 mb-4">No tienes hábitos diarios aún.</p>
            <Button variant="sacro-ghost" onClick={() => router.push("/habits/new")}>
              Crear hábito
            </Button>
          </div>
        ) : (
          <div>
            {todayHabits.map((habit) => {
              let IconComp = icons.Circle;
              const targetSummary = getHabitTargetSummary(habit);
              const validationLabel = VALIDATION_TYPE_LABELS[habit.validation_type ?? "foto"];
              const subtitle = targetSummary ? `${validationLabel} · ${targetSummary}` : validationLabel;

              if (habit.icon && icons[habit.icon as keyof typeof icons]) {
                IconComp = icons[habit.icon as keyof typeof icons] as never;
              } else {
                const sectionKey = SECTION_ICONS[habit.section];
                if (sectionKey && icons[sectionKey as keyof typeof icons]) {
                  IconComp = icons[sectionKey as keyof typeof icons] as never;
                }
              }

              const isShared =
                habit.catalog_habit_id != null &&
                sharedCatalogIds.has(habit.catalog_habit_id);

              return (
                <div key={habit.id} className={`${updatingHabitId === habit.id ? "opacity-50 pointer-events-none" : ""}`}>
                  <HabitRow
                    icon={<IconComp className="size-[34px]" />}
                    name={habit.name}
                    subtitle={subtitle}
                    checked={habit.checked_today}
                    pending={pendingHabitIds.has(habit.id)}
                    onToggle={() => handleHabitAction(habit)}
                    badge={
                      isShared ? (
                        <span className="px-[6px] py-[1px] rounded-full text-[10px] font-bold bg-[#36d98f]/20 text-[#36d98f] shrink-0">
                          Compartido
                        </span>
                      ) : undefined
                    }
                  />
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
