"use client";

import { useState, useEffect, useMemo } from "react";
import type { FormEvent } from "react";
import { useTheme } from "next-themes";
import { useRouter } from "next/navigation";
import {
  Settings,
  Target,
  Star,
  Flame,
  Trophy,
  Calendar,
  Zap,
  Award,
  Rocket,
  Sparkles,
  Bell,
  Moon,
  Sun,
  Monitor,
  Globe,
  ChevronRight,
  ImageIcon,
  LogOut,
  Trash2,
  Edit3,
  Save,
  X,
  Mail,
  Users,
} from "lucide-react";
import { fetchProfileStats, fetchXpInfo, fetchDetailedStats } from "@/services/stats/statsService";
import { getSession, clearSession } from "@/services/auth/authService";
import { clearAccountLocalData, deleteAccount } from "@/services/auth/accountService";
import { fetchCurrentUser, updateProfile } from "@/services/auth/profileService";
import { fetchAchievements } from "@/services/achievements/achievementService";
import type { AchievementItem } from "@/services/achievements/achievementService";
import { fetchHabits } from "@/services/habits/habitService";
import {
  applyReminderSchedule,
  areNativeRemindersAvailable,
  getReminderPermissionStatus,
  loadReminderPreferences,
  requestReminderPermission,
} from "@/services/reminders/reminderService";
import type {
  ReminderPermissionState,
  ReminderPreferences,
  ReminderScheduleStatus,
} from "@/services/reminders/reminderService";
import { cn } from "@/lib/utils";
import { ConfirmDeleteAccountModal } from "@/components/feedback/ConfirmDeleteAccountModal";
import type { AuthUser } from "@/types/auth";
import { WEEKDAY_LABELS } from "@/types/habits";
import type { ProfileStats, XpInfo } from "@/types/stats";

// Icon mapping for achievement keys coming from the backend
const ACHIEVEMENT_ICON_MAP: Record<string, typeof Zap> = {
  first_validation: ImageIcon,
  streak_7: Flame,
  completions_30: Trophy,
};

const REMINDER_DAYS = Object.entries(WEEKDAY_LABELS).map(([value, label]) => ({
  value: Number(value),
  label,
}));

function getAchievementIcon(key: string): typeof Zap {
  return ACHIEVEMENT_ICON_MAP[key] ?? Award;
}

function getReminderStatusMessage(
  status: ReminderScheduleStatus | "",
  scheduledCount: number,
): string {
  if (status === "scheduled") {
    return scheduledCount === 1
      ? "Recordatorio programado para 1 día."
      : `Recordatorios programados para ${scheduledCount} días.`;
  }

  if (status === "disabled") {
    return "Recordatorios desactivados.";
  }

  if (status === "permission_denied") {
    return "Permiso de notificaciones denegado. Puedes activarlo desde ajustes del sistema.";
  }

  if (status === "unavailable") {
    return "Los recordatorios locales solo están disponibles en la app móvil.";
  }

  if (status === "no_matching_habits") {
    return "No hay hábitos activos para los días seleccionados.";
  }

  return "";
}

function getPermissionLabel(permission: ReminderPermissionState): string {
  if (permission === "granted") {
    return "Permiso concedido";
  }

  if (permission === "denied") {
    return "Permiso denegado";
  }

  if (permission === "prompt" || permission === "prompt-with-rationale") {
    return "Permiso pendiente";
  }

  return "No disponible";
}

export default function ProfilePage() {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [stats, setStats] = useState<ProfileStats>({
    streak: 0, today_completed: 0, today_total: 0, completion_rate: 0,
    habits_count: 0, total_xp: 0, level: 1, validations_today: 0,
  });
  const [xpInfo, setXpInfo] = useState<XpInfo>({
    total_xp: 0, level: 1, xp_in_level: 0, xp_for_next_level: 250, progress_pct: 0,
  });
  const [records, setRecords] = useState({
    longest_streak: 0, best_day: 0, current_streak: 0, active_days: 0,
  });
  const [validationStats, setValidationStats] = useState({
    total_successful: 0, total_attempts: 0, success_rate: 0,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [achievements, setAchievements] = useState<AchievementItem[]>([]);
  const [isEditingProfile, setIsEditingProfile] = useState(false);
  const [editUsername, setEditUsername] = useState("");
  const [profileError, setProfileError] = useState("");
  const [isSavingProfile, setIsSavingProfile] = useState(false);
  const [reminderPreferences, setReminderPreferences] = useState<ReminderPreferences>(() =>
    loadReminderPreferences(),
  );
  const [reminderPermission, setReminderPermission] =
    useState<ReminderPermissionState>("unavailable");
  const [reminderStatus, setReminderStatus] = useState<ReminderScheduleStatus | "">("");
  const [reminderMessage, setReminderMessage] = useState("");
  const [isSavingReminders, setIsSavingReminders] = useState(false);

  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  const router = useRouter();
  const nativeRemindersAvailable = areNativeRemindersAvailable();

  useEffect(() => {
    setMounted(true);
    setReminderPreferences(loadReminderPreferences());
    getReminderPermissionStatus()
      .then(setReminderPermission)
      .catch(() => setReminderPermission("unavailable"));
  }, []);

  useEffect(() => {
    async function fetchData() {
      const session = getSession();
      if (session?.user) {
        setUser(session.user);
      }

      try {
        const [currentUser, profileStats, xp, detailed, achievementList] = await Promise.all([
          fetchCurrentUser(),
          fetchProfileStats(),
          fetchXpInfo(),
          fetchDetailedStats(),
          fetchAchievements(),
        ]);

        setUser(currentUser);
        setEditUsername(currentUser.username);
        setStats(profileStats);
        setXpInfo(xp);
        setRecords(detailed.records);
        setValidationStats(detailed.validations);
        setAchievements(achievementList);
        setError("");
      } catch (err) {
        setError(err instanceof Error ? err.message : "No se pudieron cargar los datos del perfil.");
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  const unlockedCount = useMemo(() => {
    return achievements.filter((a) => a.earned).length;
  }, [achievements]);

  const startEditingProfile = () => {
    setEditUsername(user?.username ?? "");
    setProfileError("");
    setIsEditingProfile(true);
  };

  const cancelEditingProfile = () => {
    setEditUsername(user?.username ?? "");
    setProfileError("");
    setIsEditingProfile(false);
  };

  const toggleReminderDay = (day: number) => {
    setReminderPreferences((current) => {
      const isSelected = current.days.includes(day);
      const nextDays = isSelected
        ? current.days.filter((selectedDay) => selectedDay !== day)
        : current.days.concat(day);

      if (nextDays.length === 0) {
        return current;
      }

      return {
        ...current,
        days: nextDays.sort((left, right) => left - right),
      };
    });
    setReminderStatus("");
    setReminderMessage("");
  };

  const updateReminderPreferences = (nextPreferences: Partial<ReminderPreferences>) => {
    setReminderPreferences((current) => ({
      ...current,
      ...nextPreferences,
    }));
    setReminderStatus("");
    setReminderMessage("");
  };

  async function handleReminderPermissionRequest() {
    const permission = await requestReminderPermission();
    setReminderPermission(permission);
  }

  async function handleReminderSubmit() {
    setIsSavingReminders(true);
    setReminderMessage("");

    try {
      const habits = reminderPreferences.enabled ? await fetchHabits() : [];
      const result = await applyReminderSchedule(reminderPreferences, habits);
      setReminderPermission(result.permission);
      setReminderStatus(result.status);
      setReminderMessage(getReminderStatusMessage(result.status, result.scheduledCount));
    } catch (err) {
      setReminderMessage(err instanceof Error ? err.message : "No se pudieron guardar los recordatorios.");
    } finally {
      setIsSavingReminders(false);
    }
  }

  async function handleProfileSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const username = editUsername.trim();

    if (username.length < 3) {
      setProfileError("El nombre debe tener al menos 3 caracteres.");
      return;
    }

    setIsSavingProfile(true);
    setProfileError("");

    try {
      const updatedUser = await updateProfile({ username });
      setUser(updatedUser);
      setEditUsername(updatedUser.username);
      setIsEditingProfile(false);
    } catch (err) {
      setProfileError(err instanceof Error ? err.message : "No se pudo actualizar el perfil.");
    } finally {
      setIsSavingProfile(false);
    }
  }

  if (loading || !mounted) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="size-8 border-2 border-white border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  const handleLogout = () => {
    clearSession();
    router.push("/login");
  };

  async function handleDeleteAccount() {
    await deleteAccount();
    clearAccountLocalData();
    clearSession();
    router.push("/login");
  }

  if (error) {
    return (
      <div className="space-y-[24px]">
        <div className="flex items-center justify-between gap-[14px]">
          <div>
            <h2 className="text-[30px] leading-[1.05] font-bold">Perfil</h2>
            <p className="text-white/74 text-[15px]">Tu progreso y logros</p>
          </div>
        </div>

        <div className="p-[24px] rounded-[24px] bg-white/10 border border-white/20 text-center space-y-4">
          <div className="space-y-2">
            <h2 className="text-[18px] font-bold text-white">Perfil no disponible</h2>
            <p className="text-[14px] text-white/74">{error}</p>
          </div>
          <button
            onClick={() => window.location.reload()}
            className="inline-flex h-[48px] items-center justify-center rounded-[20px] bg-[var(--purple)] px-[20px] text-[15px] font-bold text-white transition-transform active:scale-95"
          >
            Reintentar
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-[24px] pb-[80px]">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-[30px] leading-[1.05] font-bold">Perfil</h2>
          <p className="text-white/74 text-[15px]">Tu progreso y logros</p>
        </div>
        <button
          onClick={startEditingProfile}
          className="w-[48px] h-[48px] rounded-full bg-white/18 text-white grid place-items-center cursor-pointer transition-transform active:scale-95 hover:bg-white/25"
          aria-label="Editar perfil"
        >
          <Settings className="size-6 text-white" />
        </button>
      </div>

      {/* User Card */}
      <div className="p-[20px] rounded-[24px] bg-white/13 border border-white/20 flex items-center gap-[16px]">
          <div className="w-[64px] h-[64px] rounded-[20px] bg-gradient-to-br from-orange-400 to-pink-500 flex items-center justify-center text-2xl shadow-inner border border-white/20 shrink-0">
            <Rocket className="size-8 text-white drop-shadow-[0_0_8px_rgba(255,255,255,0.6)]" />
          </div>
          <div className="flex-1 min-w-0">
            {isEditingProfile ? (
              <form onSubmit={handleProfileSubmit} className="space-y-[12px]">
                <div className="space-y-[6px]">
                  <label className="text-[11px] font-bold uppercase tracking-[0.08em] text-white/55">
                    Nombre
                  </label>
                  <input
                    value={editUsername}
                    onChange={(event) => setEditUsername(event.target.value)}
                    disabled={isSavingProfile}
                    className="h-[44px] w-full rounded-[14px] border border-white/15 bg-white/10 px-[12px] text-[15px] font-bold text-white outline-none transition-colors placeholder:text-white/35 focus:border-[var(--purple2)] disabled:opacity-60"
                    maxLength={80}
                  />
                </div>

                <div className="flex items-center gap-[8px] text-[13px] text-white/65">
                  <Mail className="size-4 shrink-0" />
                  <span className="truncate">{user?.email ?? ""}</span>
                </div>

                {profileError ? (
                  <p className="text-[12px] font-bold text-red-300">{profileError}</p>
                ) : null}

                <div className="flex flex-wrap gap-[8px]">
                  <button
                    type="submit"
                    disabled={isSavingProfile}
                    className="inline-flex h-[40px] items-center justify-center gap-[8px] rounded-[14px] bg-[var(--purple)] px-[14px] text-[13px] font-bold text-white transition-transform active:scale-95 disabled:opacity-60"
                  >
                    <Save className="size-4" />
                    {isSavingProfile ? "Guardando" : "Guardar"}
                  </button>
                  <button
                    type="button"
                    onClick={cancelEditingProfile}
                    disabled={isSavingProfile}
                    className="inline-flex h-[40px] items-center justify-center gap-[8px] rounded-[14px] bg-white/10 px-[14px] text-[13px] font-bold text-white transition-transform active:scale-95 disabled:opacity-60"
                  >
                    <X className="size-4" />
                    Cancelar
                  </button>
                </div>
              </form>
            ) : (
              <>
                <div className="flex items-start justify-between gap-2 mb-1">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-[20px] truncate">{user?.username ?? "Usuario"}</span>
                      <span className="text-[11px] font-bold bg-[var(--purple)]/30 text-[var(--purple2)] px-[8px] py-[2px] rounded-full border border-[var(--purple)]/50 shrink-0">
                        <Trophy className="size-3 inline mr-1" /> Nivel {xpInfo.level}
                      </span>
                    </div>
                    <p className="text-[13px] text-white/60 font-medium truncate">{user?.email ?? ""}</p>
                  </div>
                  <button
                    type="button"
                    onClick={startEditingProfile}
                    className="size-[36px] rounded-[12px] bg-white/10 text-white/80 grid place-items-center transition-colors hover:bg-white/18 shrink-0"
                    aria-label="Editar perfil"
                  >
                    <Edit3 className="size-4" />
                  </button>
                </div>
                <p className="text-[13px] text-white/74 font-medium mb-3">
                  Racha actual: {records.current_streak} días <Flame className="size-3 inline text-[var(--yellow)]" />
                </p>
                {/* XP Bar */}
                <div>
                  <div className="flex justify-between text-[11px] text-white/74 font-bold mb-1">
                    <span>Experiencia</span>
                    <span>{xpInfo.xp_in_level} / {xpInfo.xp_for_next_level} XP</span>
                  </div>
                  <div className="h-[8px] rounded-full bg-white/10 overflow-hidden shadow-inner border border-white/5">
                    <div
                      className="h-full rounded-full bg-gradient-to-r from-[var(--purple)] to-[var(--purple2)] transition-all duration-500 shadow-[0_0_12px_rgba(157,85,255,0.6)]"
                      style={{ width: `${xpInfo.progress_pct}%` }}
                    />
                  </div>
                </div>
              </>
            )}
              </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 gap-[14px]">
        <div className="p-[16px] rounded-[20px] bg-white/13 border border-white/20 text-center space-y-1">
          <Target className="size-5 text-[var(--purple2)] drop-shadow-[0_0_8px_rgba(157,85,255,0.5)] mx-auto" />
          <p className="text-[24px] font-bold">{stats.habits_count}</p>
          <p className="text-[12px] text-white/74">Hábitos creados</p>
        </div>
        <div className="p-[16px] rounded-[20px] bg-white/13 border border-white/20 text-center space-y-1">
          <Star className="size-5 text-[var(--yellow)] drop-shadow-[0_0_8px_rgba(255,229,54,0.5)] mx-auto" />
          <p className="text-[24px] font-bold">{records.active_days}</p>
          <p className="text-[12px] text-white/74">Días activos</p>
        </div>
        <div className="p-[16px] rounded-[20px] bg-white/13 border border-white/20 text-center space-y-1">
          <Flame className="size-5 text-orange-400 drop-shadow-[0_0_8px_rgba(255,150,0,0.5)] mx-auto" />
          <p className="text-[24px] font-bold">{records.longest_streak}</p>
          <p className="text-[12px] text-white/74">Racha más larga</p>
        </div>
        <div className="p-[16px] rounded-[20px] bg-white/13 border border-white/20 text-center space-y-1">
          <Trophy className="size-5 text-[#36d98f] drop-shadow-[0_0_8px_rgba(54,217,143,0.5)] mx-auto" />
          <p className="text-[24px] font-bold">{unlockedCount}/{achievements.length}</p>
          <p className="text-[12px] text-white/74">Total logros</p>
        </div>
      </div>

      <button
        type="button"
        onClick={() => router.push("/social")}
        className="w-full rounded-[24px] bg-white/13 border border-white/20 p-[20px] flex items-center justify-between text-left transition-colors hover:bg-white/18"
      >
        <div className="flex items-center gap-[14px]">
          <div className="w-[44px] h-[44px] rounded-[14px] bg-[#36d98f]/20 text-[#36d98f] grid place-items-center">
            <Users className="size-5" />
          </div>
          <div>
            <p className="text-[16px] font-bold text-white">Rachas compartidas</p>
            <p className="text-[12px] text-white/74">Grupos privados por invitación</p>
          </div>
        </div>
        <ChevronRight className="size-5 text-white/40" />
      </button>

      {/* Logros */}
      <div className="p-[20px] rounded-[24px] bg-white/13 border border-white/20 space-y-[16px]">
        <div className="flex items-center justify-between">
          <h3 className="text-[18px] font-bold">Logros</h3>
          <span className="text-[13px] text-white/74 font-bold">{unlockedCount} de {achievements.length}</span>
        </div>

        {achievements.length === 0 ? (
          <p className="text-[13px] text-white/55 text-center py-4 font-bold">
            Cargando logros...
          </p>
        ) : (
          <div className="grid grid-cols-3 gap-[10px]">
            {achievements.map((ach) => {
              const IconComp = getAchievementIcon(ach.key);
              return (
                <div
                  key={ach.key}
                  className={cn(
                    "flex flex-col items-center gap-[6px] p-[12px] rounded-[16px] transition-all relative border",
                    ach.earned
                      ? "bg-gradient-to-br from-[var(--purple)] to-[var(--purple2)] border-[var(--purple2)] shadow-[0_0_12px_rgba(157,85,255,0.4)]"
                      : "bg-white/5 border-white/5 opacity-50"
                  )}
                  title={ach.description ?? ach.name}
                >
                  <span className="text-[24px] leading-none drop-shadow-[0_0_5px_rgba(255,255,255,0.5)]">{ach.emoji}</span>
                  <IconComp className="size-4" />
                  <span className="text-[10px] font-bold text-center leading-tight">
                    {ach.name}
                  </span>
                  {ach.earned && ach.xp_bonus > 0 && (
                    <span className="text-[9px] font-black text-[var(--yellow)] drop-shadow-[0_0_5px_rgba(255,229,54,0.5)]">
                      +{ach.xp_bonus} XP
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Récords */}
      <div className="space-y-[12px]">
        <h3 className="text-[18px] font-bold px-1">Récords Históricos</h3>
        <div className="p-0 overflow-hidden rounded-[24px] bg-white/13 border border-white/20 divide-y divide-white/10">
          <div className="flex items-center gap-[14px] p-[20px]">
            <div className="w-[40px] h-[40px] rounded-[12px] bg-orange-500/20 text-orange-400 grid place-items-center">
              <Flame className="size-5 drop-shadow-[0_0_8px_rgba(255,150,0,0.5)]" />
            </div>
            <div className="flex-1">
              <p className="text-[15px] font-bold leading-tight">Racha más larga</p>
              <p className="text-[12px] text-white/74">Tu mejor marca</p>
            </div>
            <span className="text-[20px] font-black">{records.longest_streak} <span className="text-[12px] font-normal text-white/74">d</span></span>
          </div>
          
          <div className="flex items-center gap-[14px] p-[20px]">
            <div className="w-[40px] h-[40px] rounded-[12px] bg-[#36d98f]/20 text-[#36d98f] grid place-items-center">
              <Calendar className="size-5 drop-shadow-[0_0_8px_rgba(54,217,143,0.5)]" />
            </div>
            <div className="flex-1">
              <p className="text-[15px] font-bold leading-tight">Días activos</p>
              <p className="text-[12px] text-white/74">Total histórico</p>
            </div>
            <span className="text-[20px] font-black">{records.active_days}</span>
          </div>
          
          <div className="flex items-center gap-[14px] p-[20px]">
            <div className="w-[40px] h-[40px] rounded-[12px] bg-[var(--purple)]/20 text-[var(--purple2)] grid place-items-center">
              <Zap className="size-5 drop-shadow-[0_0_8px_rgba(157,85,255,0.5)]" />
            </div>
            <div className="flex-1">
              <p className="text-[15px] font-bold leading-tight">Mejor día</p>
              <p className="text-[12px] text-white/74">Más hábitos en un día</p>
            </div>
            <span className="text-[20px] font-black">{records.best_day}</span>
          </div>
          
          <div className="flex items-center gap-[14px] p-[20px]">
            <div className="w-[40px] h-[40px] rounded-[12px] bg-emerald-400/20 text-emerald-400 grid place-items-center">
              <ImageIcon className="size-5 drop-shadow-[0_0_8px_rgba(52,211,153,0.5)]" />
            </div>
            <div className="flex-1">
              <p className="text-[15px] font-bold leading-tight">Validaciones exitosas</p>
              <p className="text-[12px] text-white/74">
                {validationStats.success_rate}% tasa de éxito
              </p>
            </div>
            <span className="text-[20px] font-black">{validationStats.total_successful}</span>
          </div>
        </div>
      </div>

      {/* XP Total */}
      <div className="p-[20px] rounded-[24px] bg-white/13 border border-white/20 flex items-center gap-[16px]">
        <div className="w-[56px] h-[56px] rounded-[16px] bg-gradient-to-br from-[var(--yellow)] to-orange-500 flex items-center justify-center border border-white/20">
          <Sparkles className="size-6 text-orange-950" />
        </div>
        <div className="flex-1">
          <p className="text-[16px] font-bold text-white">XP Total</p>
          <p className="text-[13px] text-white/74 font-bold">Nivel {xpInfo.level}</p>
        </div>
        <span className="text-[28px] font-black drop-shadow-[0_0_12px_rgba(255,255,255,0.4)]">{xpInfo.total_xp}</span>
      </div>

      {/* Settings */}
      <div className="p-0 overflow-hidden rounded-[24px] bg-white/13 border border-white/20 divide-y divide-white/10">
        <div className="p-[20px] bg-white/5 space-y-[16px]">
          <div className="flex items-center justify-between gap-[16px]">
            <div className="flex items-center gap-[12px] min-w-0">
              <Bell className="size-5 text-white/74 shrink-0" />
              <div className="min-w-0">
                <span className="block text-[15px] font-bold text-white">Recordatorios</span>
                <span className="block text-[12px] font-bold text-white/55">
                  {getPermissionLabel(reminderPermission)}
                </span>
              </div>
            </div>
            <button
              type="button"
              onClick={() => updateReminderPreferences({ enabled: !reminderPreferences.enabled })}
              disabled={!nativeRemindersAvailable || isSavingReminders}
              aria-pressed={reminderPreferences.enabled}
              className={cn(
                "w-[48px] h-[28px] rounded-full flex items-center p-[3px] transition-colors disabled:opacity-50",
                reminderPreferences.enabled && nativeRemindersAvailable
                  ? "bg-[var(--purple)]"
                  : "bg-white/14",
              )}
            >
              <span
                className={cn(
                  "size-[22px] rounded-full bg-white shadow-[0_0_8px_rgba(0,0,0,0.2)] transition-transform",
                  reminderPreferences.enabled && nativeRemindersAvailable
                    ? "translate-x-[20px]"
                    : "translate-x-0",
                )}
              />
            </button>
          </div>

          <div className="grid grid-cols-1 gap-[12px]">
            <label className="space-y-[6px]">
              <span className="text-[12px] font-bold uppercase tracking-[0.08em] text-white/55">
                Hora
              </span>
              <input
                type="time"
                value={reminderPreferences.time}
                disabled={!nativeRemindersAvailable || isSavingReminders}
                onChange={(event) => updateReminderPreferences({ time: event.target.value })}
                className="h-[44px] w-full rounded-[14px] border border-white/15 bg-white/10 px-[12px] text-[15px] font-bold text-white outline-none transition-colors focus:border-[var(--purple2)] disabled:opacity-50"
              />
            </label>

            <div className="space-y-[8px]">
              <span className="text-[12px] font-bold uppercase tracking-[0.08em] text-white/55">
                Días
              </span>
              <div className="grid grid-cols-7 gap-[6px]">
                {REMINDER_DAYS.map((day) => {
                  const isSelected = reminderPreferences.days.includes(day.value);
                  return (
                    <button
                      key={day.value}
                      type="button"
                      onClick={() => toggleReminderDay(day.value)}
                      disabled={!nativeRemindersAvailable || isSavingReminders}
                      className={cn(
                        "h-[36px] rounded-[12px] border text-[12px] font-black transition-colors disabled:opacity-50",
                        isSelected
                          ? "border-[var(--purple2)] bg-[var(--purple)] text-white"
                          : "border-white/15 bg-white/8 text-white/70",
                      )}
                    >
                      {day.label}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>

          {reminderMessage ? (
            <p
              className={cn(
                "text-[12px] font-bold",
                reminderStatus === "scheduled" || reminderStatus === "disabled"
                  ? "text-emerald-300"
                  : "text-yellow-200",
              )}
            >
              {reminderMessage}
            </p>
          ) : null}

          <div className="flex flex-wrap gap-[8px]">
            <button
              type="button"
              onClick={handleReminderSubmit}
              disabled={isSavingReminders}
              className="inline-flex h-[40px] items-center justify-center gap-[8px] rounded-[14px] bg-[var(--purple)] px-[14px] text-[13px] font-bold text-white transition-transform active:scale-95 disabled:opacity-60"
            >
              <Save className="size-4" />
              {isSavingReminders ? "Guardando" : "Guardar"}
            </button>
            {nativeRemindersAvailable && reminderPermission !== "granted" ? (
              <button
                type="button"
                onClick={handleReminderPermissionRequest}
                disabled={isSavingReminders}
                className="inline-flex h-[40px] items-center justify-center rounded-[14px] bg-white/10 px-[14px] text-[13px] font-bold text-white transition-transform active:scale-95 disabled:opacity-60"
              >
                Pedir permiso
              </button>
            ) : null}
          </div>
        </div>

        <div className="flex items-center justify-between p-[20px] hover:bg-white/5 transition-colors cursor-pointer">
          <div className="flex items-center gap-[12px]">
            {theme === "dark" ? (
              <Moon className="size-5 text-white/74" />
            ) : theme === "light" ? (
              <Sun className="size-5 text-white/74" />
            ) : (
              <Monitor className="size-5 text-white/74" />
            )}
            <span className="text-[15px] font-bold text-white">Tema</span>
          </div>
          <div className="flex items-center gap-[8px]">
            <select
              value={theme}
              onChange={(e) => setTheme(e.target.value)}
              className="bg-transparent text-[13px] font-bold text-white/74 outline-none appearance-none cursor-pointer"
            >
              <option value="system">Sistema</option>
              <option value="theme-fire">Fuego</option>
              <option value="theme-ice">Hielo</option>
              <option value="theme-candy">Dulce</option>
              <option value="theme-night">Noche</option>
              <option value="light">Claro</option>
              <option value="dark">Oscuro</option>
            </select>
            <ChevronRight className="size-5 text-white/40 pointer-events-none" />
          </div>
        </div>

        <div className="flex items-center justify-between p-[20px] hover:bg-white/5 transition-colors cursor-pointer">
          <div className="flex items-center gap-[12px]">
            <Globe className="size-5 text-white/74" />
            <span className="text-[15px] font-bold text-white">Idioma</span>
          </div>
          <div className="flex items-center gap-[8px] text-[13px] font-bold text-white/74">
            <span>Español</span>
            <ChevronRight className="size-5 text-white/40" />
          </div>
        </div>

        <button 
          onClick={handleLogout}
          className="w-full flex items-center justify-between p-[20px] hover:bg-white/5 transition-colors"
        >
          <div className="flex items-center gap-[12px]">
            <LogOut className="size-5 text-red-400" />
            <span className="text-[15px] text-red-400 font-bold">Cerrar Sesión</span>
          </div>
          <ChevronRight className="size-5 text-white/40" />
        </button>

        {/* Danger zone */}
        <button
          onClick={() => setShowDeleteModal(true)}
          className="w-full flex items-center justify-between p-[20px] hover:bg-red-500/10 transition-colors"
        >
          <div className="flex items-center gap-[12px]">
            <Trash2 className="size-5 text-red-500" />
            <span className="text-[15px] text-red-500 font-bold">Eliminar cuenta</span>
          </div>
          <ChevronRight className="size-5 text-red-500/50" />
        </button>
      </div>

      {/* Delete account confirmation modal */}
      <ConfirmDeleteAccountModal
        isOpen={showDeleteModal}
        onClose={() => setShowDeleteModal(false)}
        onConfirm={handleDeleteAccount}
      />
    </div>
  );
}
