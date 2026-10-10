"use client";

import Link from "next/link";
import { useState, useEffect, memo } from "react";
import {
  Flame,
  TrendingUp,
  Trophy,
  Calendar,
  Zap,
  BarChart3,
  Clock3,
  CheckCircle2,
  XCircle,
  Hourglass,
  ListChecks,
  Sparkles,
  Target,
  icons,
} from "lucide-react";
import { fetchHabitHistory } from "@/services/history/historyService";
import { fetchDetailedStats } from "@/services/stats/statsService";
import { getStatsViewState } from "@/services/stats/statsViewState";
import { getSession } from "@/services/auth/authService";
import { getPendingOpsCount } from "@/services/sync/syncQueue";
import { StatCard } from "@/components/ui/StatCard";
import type { HabitHistoryEvent, HabitHistoryStatus } from "@/types/history";
import { getCachedApiData, hasFreshApiData } from "@/services/api/queryCache";
import { API_ENDPOINTS } from "@/services/api/endpoints";

/* ── Types ────────────────────────────────────── */

interface Summary {
  streak: number;
  completion_rate: number;
  total_completed: number;
  total_habits: number;
}

interface WeekDay {
  date: string;
  label: string;
  completed: number;
  total: number;
}

interface HabitStat {
  id: number;
  name: string;
  icon: string;
  completed: number;
  total: number;
  rate: number;
}

interface CalendarDay {
  date: string;
  count: number;
  intensity: number; // 0-3
}

interface Records {
  longest_streak: number;
  best_day: number;
  current_streak: number;
}

interface StatsData {
  summary: Summary;
  weekly_history: WeekDay[];
  per_habit: HabitStat[];
  calendar: CalendarDay[];
  records: Records;
}

/* ── Completion Ring ──────────────────────────── */

const CompletionRing = memo(function CompletionRing({ rate }: { rate: number }) {
  const radius = 56;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - rate / 100);

  return (
    <div className="relative size-36 mx-auto">
      <svg
        className="w-full h-full -rotate-90"
        viewBox="0 0 128 128"
        role="img"
        aria-label={`Tasa de completado: ${rate}%`}
      >
        <circle
          cx="64"
          cy="64"
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeWidth="8"
          className="text-white/10"
        />
        <circle
          cx="64"
          cy="64"
          r={radius}
          fill="none"
          stroke="url(#ringGrad)"
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className="transition-all duration-1000 ease-out drop-shadow-[0_0_12px_rgba(36,207,255,0.6)]"
        />
        <defs>
          <linearGradient id="ringGrad" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="var(--purple)" />
            <stop offset="100%" stopColor="var(--purple2)" />
          </linearGradient>
        </defs>
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center" aria-hidden="true">
        <span className="text-[32px] font-bold text-white leading-none">{rate}%</span>
        <span className="text-[11px] text-white/74 uppercase font-bold tracking-wider mt-1">Completado</span>
      </div>
    </div>
  );
});

/* ── Weekly Bar Chart ─────────────────────────── */

const WeeklyChart = memo(function WeeklyChart({ data }: { data: WeekDay[] }) {
  const maxVal = Math.max(...data.map((d) => d.total), 1);

  return (
    <div className="flex items-end justify-between gap-2 h-[128px]">
      {data.map((day) => {
        const pct = maxVal > 0 ? (day.completed / maxVal) * 100 : 0;
        const isToday = day.date === new Date().toISOString().split("T")[0];
        
        return (
          <div key={day.date} className="flex-1 flex flex-col items-center gap-1">
            <span className="text-[10px] text-white/55 font-bold">
              {day.completed}
            </span>
            <div className="w-full h-24 bg-[var(--bg1)] rounded-lg relative overflow-hidden border border-white/10">
              <div
                className={`absolute bottom-0 left-0 right-0 rounded-lg transition-all duration-700 ease-out ${
                  isToday ? "bg-[var(--purple2)]" : "bg-[var(--purple)]"
                }`}
                style={{ height: `${Math.max(pct, 8)}%` }}
              />
            </div>
            <span
              className={`text-[10px] font-bold ${
                isToday ? "text-[var(--yellow)] drop-shadow-[0_0_5px_rgba(255,229,54,0.6)]" : "text-white/55"
              }`}
            >
              {day.label}
            </span>
          </div>
        );
      })}
    </div>
  );
});

/* ── Streak Calendar (30‑day heatmap) ──────── */

const StreakCalendar = memo(function StreakCalendar({ data }: { data: CalendarDay[] }) {
  const intensityColors = [
    "bg-[var(--bg1)] border border-white/10",
    "bg-[var(--bg2)] border border-white/10",
    "bg-[var(--purple)] border border-[var(--purple2)]",
    "bg-[var(--purple2)] border border-[var(--yellow)]",
  ];

  return (
    <div className="grid grid-cols-10 gap-1.5">
      {data.map((day) => (
        <div
          key={day.date}
          title={`${day.date}: ${day.count} completados`}
          className={`aspect-square rounded-[6px] ${
            intensityColors[day.intensity]
          } transition-colors`}
        />
      ))}
    </div>
  );
});

const HISTORY_STATUS_LABELS: Record<HabitHistoryStatus, string> = {
  completed: "Completado",
  approved: "Aprobado",
  rejected: "Rechazado",
  pending: "Pendiente",
};

function HistoryStatusIcon({ status }: { status: HabitHistoryStatus }) {
  if (status === "rejected") {
    return <XCircle className="size-4 text-red-300" />;
  }
  if (status === "pending") {
    return <Hourglass className="size-4 text-yellow-200" />;
  }
  return <CheckCircle2 className="size-4 text-emerald-300" />;
}

function formatHistoryDate(value: string | null): string {
  if (!value) {
    return "Sin fecha";
  }
  const date = new Date(`${value}T00:00:00`);
  return new Intl.DateTimeFormat("es", {
    day: "numeric",
    month: "short",
  }).format(date);
}

const RecentHistory = memo(function RecentHistory({ events }: { events: HabitHistoryEvent[] }) {
  if (events.length === 0) {
    return (
      <div className="p-[20px] rounded-[24px] bg-[var(--bg2)] border border-white/20 text-center">
        <p className="text-[14px] text-white/74">Aún no hay eventos de historial.</p>
      </div>
    );
  }

  return (
    <div className="p-[20px] rounded-[24px] bg-[var(--bg2)] border border-white/20 space-y-[16px]">
      <div className="flex items-center gap-[8px]">
        <Clock3 className="size-5 text-[var(--yellow)] drop-shadow-[0_0_8px_rgba(255,229,54,0.5)]" />
        <h3 className="text-[18px] font-bold">Historial reciente</h3>
      </div>
      <div className="space-y-[10px]">
        {events.map((event) => (
          <div key={event.id} className="rounded-[18px] bg-[var(--bg1)] border border-white/10 p-[14px] space-y-2">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="text-[15px] font-bold truncate">{event.habit_name ?? "Hábito"}</p>
                <p className="text-[12px] text-white/55">
                  {event.category_name ?? "Sin categoría"} · {formatHistoryDate(event.event_date)}
                </p>
              </div>
              <span className="shrink-0 inline-flex items-center gap-1 rounded-full bg-[var(--bg3)] px-2.5 py-1 text-[11px] font-bold text-white/84">
                <HistoryStatusIcon status={event.status} />
                {HISTORY_STATUS_LABELS[event.status]}
              </span>
            </div>
            <div className="flex flex-wrap gap-2 text-[11px]">
              {event.validation_type ? (
                <span className="rounded-full bg-[var(--purple)]/20 text-white px-2.5 py-1">
                  {event.validation_type}
                </span>
              ) : null}
              <span className="rounded-full bg-[var(--yellow)]/15 text-[var(--yellow)] px-2.5 py-1 font-bold">
                {event.xp_awarded} XP
              </span>
            </div>
            {event.reason ? (
              <p className="text-[12px] text-white/65 line-clamp-2">{event.reason}</p>
            ) : null}
          </div>
        ))}
      </div>
    </div>
  );
});

/* ── Main Page ────────────────────────────────── */

export default function StatsPage() {
  const [stats, setStats] = useState<StatsData | null>(() => getCachedApiData<StatsData>(API_ENDPOINTS.stats.detailed));
  const [historyEvents, setHistoryEvents] = useState<HabitHistoryEvent[]>(() => getCachedApiData<{items: HabitHistoryEvent[]}>(`${API_ENDPOINTS.checkins.history}?limit=20`)?.items ?? []);
  const [loading, setLoading] = useState(() => getCachedApiData(API_ENDPOINTS.stats.detailed) === null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [offlinePendingCount, setOfflinePendingCount] = useState(0);

  async function fetchStats() {
    try {
      const data = await fetchDetailedStats();
      setStats(data);
      setErrorMessage(null);
      try {
        const history = await fetchHabitHistory({ limit: 20 });
        setHistoryEvents(history.items);
      } catch {
        if (!stats) setHistoryEvents([]);
      }
    } catch (error) {
      // Keep the last successful result visible while reporting the refresh error.
      setErrorMessage(
        error instanceof Error && error.message.trim()
          ? error.message
          : "No se pudieron cargar tus estadísticas reales. Intenta de nuevo en unos momentos.",
      );
      const session = getSession();
      const userId = Number(session?.user.id ?? 0);
      setOfflinePendingCount(userId > 0 ? getPendingOpsCount(userId) : 0);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void fetchStats();
    const onFocus = () => {
      if (!hasFreshApiData(API_ENDPOINTS.stats.detailed)) void fetchStats();
    };
    window.addEventListener("focus", onFocus);
    return () => window.removeEventListener("focus", onFocus);
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="size-8 border-2 border-white border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  const viewState = getStatsViewState(stats, stats ? null : errorMessage);

  if (viewState.kind === "empty" || viewState.kind === "error") {
    return (
      <div className="space-y-[24px]">
        <div>
          <h2 className="text-[30px] leading-[1.05] font-bold">Estadísticas</h2>
          <p className="text-white/74 text-[15px]">Tu progreso en detalle</p>
        </div>

        <div className="p-[24px] rounded-[24px] bg-[var(--bg2)] border border-white/20 text-center space-y-4">
          <div className="space-y-2">
            <h2 className="text-[18px] font-bold text-white">{viewState.title}</h2>
            <p className="text-[14px] text-white/74">{viewState.message}</p>
            {offlinePendingCount > 0 ? (
              <p className="text-[13px] text-yellow-300 font-medium">
                <Hourglass className="inline size-4 mr-1 text-[var(--yellow)]" aria-hidden="true" /> {offlinePendingCount} cambio{offlinePendingCount === 1 ? "" : "s"} pendiente{offlinePendingCount === 1 ? "" : "s"} de sincronización
              </p>
            ) : null}
          </div>

          {viewState.kind === "empty" ? (
            <Link
              href="/habits/new"
              className="inline-flex h-[48px] items-center justify-center rounded-[20px] bg-[var(--purple)] px-[20px] text-[15px] font-bold text-white transition-transform active:scale-95"
            >
              Agregar hábito del catálogo
            </Link>
          ) : (
            <button
              type="button"
              onClick={() => {
                setLoading(true);
                void fetchStats();
              }}
              className="inline-flex h-[48px] items-center justify-center rounded-[20px] bg-[var(--purple)] px-[20px] text-[15px] font-bold text-white transition-transform active:scale-95"
            >
              Reintentar
            </button>
          )}
        </div>
      </div>
    );
  }

  if (!stats) {
    return null;
  }

  const summary = stats.summary;
  const weekly = stats.weekly_history;
  const perHabit = stats.per_habit;
  const calendar = stats.calendar;
  const records = stats.records;

  return (
    <div className="space-y-[24px]">
      {errorMessage && <p role="alert" className="rounded-xl border border-amber-200/40 bg-amber-950/30 px-4 py-3 text-sm text-white">{errorMessage} Se muestran los datos disponibles.</p>}
      {/* Header */}
      <div>
        <h2 className="text-[30px] leading-[1.05] font-bold">Estadísticas</h2>
        <p className="text-white/74 text-[15px]">Tu progreso en detalle</p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 gap-[14px]">
        <StatCard icon={Flame} label="Racha" value={`${summary.streak} días`} />
        <StatCard icon={Target} label="Tasa" value={`${summary.completion_rate}%`} />
      </div>

      <div className="grid grid-cols-2 gap-[14px]">
        <StatCard icon={ListChecks} label="Total Hábitos" value={summary.total_habits} />
        <StatCard icon={Sparkles} label="Total Check-ins" value={summary.total_completed} />
      </div>

      {/* Completion Ring + Weekly Chart */}
      <div className="space-y-[14px]">
        {/* Weekly Bar Chart */}
        <div className="p-[20px] rounded-[24px] bg-[var(--bg2)] border border-white/20 space-y-[16px]">
          <div className="flex items-center gap-[8px]">
            <BarChart3 className="size-5 text-[var(--yellow)] drop-shadow-[0_0_8px_rgba(255,229,54,0.5)]" />
            <h3 className="text-[18px] font-bold">Actividad semanal</h3>
          </div>
          <WeeklyChart data={weekly} />
        </div>

        {/* Completion Ring */}
        <div className="p-[20px] rounded-[24px] bg-[var(--bg2)] border border-white/20 space-y-[16px]">
          <h3 className="text-[18px] font-bold text-center">Tasa de completado</h3>
          <CompletionRing rate={summary.completion_rate} />
          <p className="text-[13px] text-white/74 text-center font-medium">
            Últimos 7 días
          </p>
        </div>
      </div>

      {/* Per-habit Breakdown */}
      {perHabit.length > 0 ? (
        <div className="p-[20px] rounded-[24px] bg-[var(--bg2)] border border-white/20 space-y-[20px]">
          <h3 className="text-[18px] font-bold">Desglose por hábito</h3>
          <div className="space-y-[16px]">
            {perHabit.map((h) => {
              const IconComp = icons[h.icon as keyof typeof icons] || icons.Circle;
              return (
              <div key={h.id} className="space-y-[8px]">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-[10px]">
                    <span className="w-[36px] h-[36px] rounded-[12px] bg-[var(--bg3)] grid place-items-center text-white">
                      <IconComp className="size-5" />
                    </span>
                    <span className="text-[15px] font-bold">
                      {h.name}
                    </span>
                  </div>
                  <span className="text-[13px] text-white/74 font-bold">
                    {h.completed}/{h.total} d
                  </span>
                </div>
                <div className="h-[10px] rounded-full bg-[var(--bg1)] overflow-hidden border border-white/10">
                  <div
                    className="h-full rounded-full bg-[var(--purple2)] transition-all duration-700 ease-out"
                    style={{ width: `${h.rate}%` }}
                  />
                </div>
              </div>
            )})}
          </div>
        </div>
      ) : null}

      {/* 30-day Calendar */}
      <div className="p-[20px] rounded-[24px] bg-[var(--bg2)] border border-white/20 space-y-[16px]">
        <div className="flex items-center gap-[8px]">
          <Calendar className="size-5 text-[var(--yellow)] drop-shadow-[0_0_8px_rgba(255,229,54,0.5)]" />
          <h3 className="text-[18px] font-bold">Últimos 30 días</h3>
        </div>
        <StreakCalendar data={calendar} />
        <div className="flex items-center justify-end gap-[6px] pt-2">
          <span className="text-[11px] text-white/55 font-bold">Menos</span>
          <div className="flex gap-[4px]">
            <div className="size-[14px] rounded-[4px] bg-[var(--bg1)] border border-white/10" />
            <div className="size-[14px] rounded-[4px] bg-[var(--purple)]/30 border border-[var(--purple)]/20" />
            <div className="size-[14px] rounded-[4px] bg-[var(--purple)]/60 border border-[var(--purple)]/40" />
            <div className="size-[14px] rounded-[4px] bg-[var(--purple)] border border-[var(--purple2)] shadow-[0_0_8px_rgba(157,85,255,0.8)]" />
          </div>
          <span className="text-[11px] text-white/55 font-bold">Más</span>
        </div>
      </div>

      <RecentHistory events={historyEvents} />

      {/* Records */}
      <div className="p-0 overflow-hidden rounded-[24px] bg-[var(--bg2)] border border-white/20 divide-y divide-white/10">
        <div className="flex items-center gap-[8px] p-[20px] bg-[var(--bg3)]">
          <Trophy className="size-5 text-[var(--yellow)] drop-shadow-[0_0_8px_rgba(255,229,54,0.5)]" />
          <h3 className="text-[18px] font-bold">Récords personales</h3>
        </div>
        
        <div className="flex items-center gap-[14px] p-[20px]">
          <div className="w-[46px] h-[46px] rounded-[14px] bg-orange-500/20 text-orange-400 grid place-items-center">
            <Flame className="size-6 drop-shadow-[0_0_8px_rgba(255,150,0,0.5)]" />
          </div>
          <div className="flex-1">
            <p className="text-[16px] font-bold leading-tight">Racha más larga</p>
            <p className="text-[13px] text-white/74">Tu mejor marca</p>
          </div>
          <span className="text-[24px] font-black tracking-tight">
            {records.longest_streak} <span className="text-[14px] font-normal text-white/74">días</span>
          </span>
        </div>

        <div className="flex items-center gap-[14px] p-[20px]">
          <div className="w-[46px] h-[46px] rounded-[14px] bg-[var(--purple)]/20 text-[var(--purple2)] grid place-items-center">
            <Zap className="size-6 drop-shadow-[0_0_8px_rgba(157,85,255,0.5)]" />
          </div>
          <div className="flex-1">
            <p className="text-[16px] font-bold leading-tight">Mejor día</p>
            <p className="text-[13px] text-white/74">Más hábitos en un día</p>
          </div>
          <span className="text-[24px] font-black tracking-tight">{records.best_day}</span>
        </div>

        <div className="flex items-center gap-[14px] p-[20px]">
          <div className="w-[46px] h-[46px] rounded-[14px] bg-[#36d98f]/20 text-[#36d98f] grid place-items-center">
            <TrendingUp className="size-6 drop-shadow-[0_0_8px_rgba(54,217,143,0.5)]" />
          </div>
          <div className="flex-1">
            <p className="text-[16px] font-bold leading-tight">Racha actual</p>
            <p className="text-[13px] text-white/74">Días consecutivos</p>
          </div>
          <span className="text-[24px] font-black tracking-tight">
            {records.current_streak} <span className="text-[14px] font-normal text-white/74">días</span>
          </span>
        </div>
      </div>
    </div>
  );
}
