"use client";

import { useEffect, useState } from "react";
import { Check, ChevronDown, Clock3, Copy, Flame, LogOut, Plus, RefreshCw, Trophy, Users, X } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import {
  createSharedGroup,
  fetchSharedGroups,
  joinSharedGroup,
  leaveSharedGroup,
} from "@/services/social/socialService";
import { fetchHabits } from "@/services/habits/habitService";
import type { SharedStreakGroup, SharedStreakMember } from "@/types/social";
import type { Habit } from "@/types/habits";
import { getCachedApiData } from "@/services/api/queryCache";
import { API_ENDPOINTS } from "@/services/api/endpoints";
import { readPageMemory, writePageMemory } from "@/services/navigation/pageMemory";

interface SocialDraft {
  groupName: string;
  selectedHabitId: number | "";
  durationDays: number | null;
  inviteCode: string;
}

function memberLabel(member: SharedStreakMember): { icon: LucideIcon; text: string; color: string } {
  if (member.status === "winner") return { icon: Trophy, text: "Ganador", color: "text-amber-300" };
  if (member.status === "lost") return { icon: X, text: "Perdió", color: "text-red-400" };
  if (member.status === "left") return { icon: LogOut, text: "Salió", color: "text-white/40" };
  return member.today_completed
    ? { icon: Check, text: "Validado hoy", color: "text-[#36d98f]" }
    : { icon: Clock3, text: "Pendiente hoy", color: "text-amber-400" };
}

const DURATION_OPTIONS: Array<{ label: string; value: number | null }> = [
  { label: "Sin límite", value: null },
  { label: "7 días", value: 7 },
  { label: "15 días", value: 15 },
  { label: "30 días", value: 30 },
];

export default function SocialPage() {
  const [groups, setGroups] = useState<SharedStreakGroup[]>(() => getCachedApiData<SharedStreakGroup[]>(API_ENDPOINTS.social.groups) ?? []);
  const [habits, setHabits] = useState<Habit[]>(() => getCachedApiData<Habit[]>(API_ENDPOINTS.habits.list) ?? []);
  const [loading, setLoading] = useState(() => getCachedApiData(API_ENDPOINTS.social.groups) === null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [groupName, setGroupName] = useState(() => readPageMemory<SocialDraft>("social")?.groupName ?? "");
  const [selectedHabitId, setSelectedHabitId] = useState<number | "">(() => readPageMemory<SocialDraft>("social")?.selectedHabitId ?? "");
  const [durationDays, setDurationDays] = useState<number | null>(() => readPageMemory<SocialDraft>("social")?.durationDays ?? null);
  const [inviteCode, setInviteCode] = useState(() => readPageMemory<SocialDraft>("social")?.inviteCode ?? "");

  useEffect(() => {
    writePageMemory<SocialDraft>("social", { groupName, selectedHabitId, durationDays, inviteCode });
  }, [groupName, selectedHabitId, durationDays, inviteCode]);

  async function loadData(showSpinner = false) {
    if (showSpinner && getCachedApiData(API_ENDPOINTS.social.groups) === null) setLoading(true);
    try {
      const [groupsResult, habitsResult] = await Promise.allSettled([
        fetchSharedGroups(),
        fetchHabits(),
      ]);
      if (groupsResult.status === "fulfilled") {
        setGroups(groupsResult.value);
      } else {
        setError(groupsResult.reason instanceof Error ? groupsResult.reason.message : "No se pudieron cargar las rachas compartidas.");
      }
      if (habitsResult.status === "fulfilled") {
        setHabits(habitsResult.value.filter((h) => h.active !== false));
      }
    } finally {
      if (showSpinner) setLoading(false);
    }
  }

  useEffect(() => {
    void loadData(true);
  }, []);

  async function handleCreate(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const name = groupName.trim();
    if (name.length < 3) {
      setError("El nombre del grupo debe tener al menos 3 caracteres.");
      return;
    }
    if (!selectedHabitId) {
      setError("Debes seleccionar un hábito para la racha compartida.");
      return;
    }

    setSaving(true);
    setError("");
    try {
      const created = await createSharedGroup({
        name,
        user_habit_id: selectedHabitId,
        duration_days: durationDays,
      });
      setGroups((current) => [created, ...current.filter((group) => group.id !== created.id)]);
      setGroupName("");
      setSelectedHabitId("");
      setDurationDays(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo crear el grupo.");
    } finally {
      setSaving(false);
    }
  }

  async function handleJoin(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalizedCode = inviteCode.trim().toUpperCase();
    if (!normalizedCode) {
      setError("Escribe un código de invitación.");
      return;
    }

    setSaving(true);
    setError("");
    try {
      const joined = await joinSharedGroup({ invite_code: normalizedCode });
      setGroups((current) => [joined, ...current.filter((group) => group.id !== joined.id)]);
      setInviteCode("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo unir al grupo.");
    } finally {
      setSaving(false);
    }
  }

  async function handleLeave(groupId: number) {
    setSaving(true);
    setError("");
    try {
      await leaveSharedGroup(groupId);
      setGroups((current) => current.filter((group) => group.id !== groupId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo salir del grupo.");
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="size-8 border-2 border-white border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-[24px] pb-[80px]">
      <div className="flex items-center justify-between gap-[14px]">
        <div>
          <h2 className="text-[30px] leading-[1.05] font-bold">Rachas compartidas</h2>
          <p className="text-white/74 text-[15px]">Duelos privados por invitación · máx. 3</p>
        </div>
        <button
          onClick={() => void loadData(true)}
          className="w-[48px] h-[48px] rounded-full bg-[var(--bg3)] text-white grid place-items-center transition-transform active:scale-95"
          aria-label="Actualizar"
        >
          <RefreshCw className="size-5" />
        </button>
      </div>

      {error ? (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-100">
          {error}
        </div>
      ) : null}

      <div className="grid gap-[14px] md:grid-cols-2">
        {/* Create form */}
        <form onSubmit={handleCreate} className="rounded-[24px] bg-[var(--bg2)] border border-white/20 p-[18px] space-y-[12px]">
          <div className="flex items-center gap-[10px]">
            <Plus className="size-5 text-[var(--purple2)]" />
            <h3 className="text-[16px] font-bold">Crear grupo</h3>
          </div>
          <p className="text-[12px] text-white/50">Máximo 3 participantes por duelo.</p>
          <input
            value={groupName}
            onChange={(event) => setGroupName(event.target.value)}
            placeholder="Nombre del reto"
            maxLength={120}
            className="h-[46px] w-full rounded-[16px] border border-white/20 bg-[var(--bg1)] px-[14px] text-[14px] text-white placeholder:text-white/45 outline-none focus:border-[var(--purple2)]"
          />
          <div className="relative">
            <select
              value={selectedHabitId}
              onChange={(event) =>
                setSelectedHabitId(event.target.value ? Number(event.target.value) : "")
              }
              aria-label="Seleccionar hábito"
              className="h-[46px] w-full rounded-[16px] border border-white/20 bg-[var(--bg1)] px-[14px] text-[14px] text-white outline-none focus:border-[var(--purple2)] appearance-none cursor-pointer"
            >
              <option value="" className="bg-[#120548] text-white/60">
                Seleccionar hábito…
              </option>
              {habits.map((habit) => (
                <option key={habit.id} value={habit.id} className="bg-[#120548] text-white">
                  {habit.name}
                </option>
              ))}
            </select>
            <ChevronDown className="pointer-events-none absolute right-[14px] top-1/2 size-4 -translate-y-1/2 text-white/70" aria-hidden="true" />
          </div>
          <div className="relative">
            <select
              value={durationDays === null ? "" : String(durationDays)}
              onChange={(event) =>
                setDurationDays(event.target.value ? Number(event.target.value) : null)
              }
              aria-label="Duración del reto"
              className="h-[46px] w-full rounded-[16px] border border-white/20 bg-[var(--bg1)] px-[14px] text-[14px] text-white outline-none focus:border-[var(--purple2)] appearance-none cursor-pointer"
            >
              {DURATION_OPTIONS.map((opt) => (
                <option
                  key={opt.label}
                  value={opt.value === null ? "" : String(opt.value)}
                  className="bg-[#120548] text-white"
                >
                  {opt.label}
                </option>
              ))}
            </select>
            <ChevronDown className="pointer-events-none absolute right-[14px] top-1/2 size-4 -translate-y-1/2 text-white/70" aria-hidden="true" />
          </div>
          <button
            type="submit"
            disabled={saving}
            className="h-[46px] w-full rounded-[16px] bg-[var(--purple)] text-[14px] font-bold text-white disabled:opacity-60"
          >
            Crear reto
          </button>
        </form>

        {/* Join form */}
        <form onSubmit={handleJoin} className="rounded-[24px] bg-[var(--bg2)] border border-white/20 p-[18px] space-y-[12px]">
          <div className="flex items-center gap-[10px]">
            <Users className="size-5 text-[#36d98f]" />
            <h3 className="text-[16px] font-bold">Unirme</h3>
          </div>
          <input
            value={inviteCode}
            onChange={(event) => setInviteCode(event.target.value.toUpperCase())}
            placeholder="Código de invitación"
            className="h-[46px] w-full rounded-[16px] border border-white/20 bg-[var(--bg1)] px-[14px] text-[14px] uppercase tracking-[0.08em] text-white placeholder:normal-case placeholder:tracking-normal placeholder:text-white/45 outline-none focus:border-[#36d98f]"
          />
          <button
            type="submit"
            disabled={saving}
            className="h-[46px] w-full rounded-[16px] bg-[#238a5a] text-[14px] font-bold text-white disabled:opacity-60"
          >
            Unirme al grupo
          </button>
        </form>
      </div>

      {/* Groups list */}
      <div className="space-y-[14px]">
        <h3 className="text-[18px] font-bold">Mis grupos</h3>
        {groups.length === 0 ? (
          <div className="rounded-[24px] bg-[var(--bg2)] border border-white/20 p-[24px] text-center text-[14px] text-white/74">
            Crea un duelo privado o únete con un código para competir con amigos.
          </div>
        ) : (
          groups.map((group) => {
            const isFinished = group.group_status === "finished";
            const winners = group.members?.filter((m) => m.status === "winner") ?? [];

            return (
              <div key={group.id} className="rounded-[24px] bg-[var(--bg2)] border border-white/20 p-[18px] space-y-[14px]">
                {/* Header */}
                <div className="flex items-start justify-between gap-[12px]">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-[8px] flex-wrap">
                      <h4 className="text-[18px] font-bold truncate">{group.name}</h4>
                      {isFinished && (
                        <span className="text-[11px] font-bold px-[8px] py-[2px] rounded-full bg-amber-500/20 text-amber-300">
                          Finalizado
                        </span>
                      )}
                    </div>
                    {group.habit_name ? (
                      <p className="text-[12px] text-[#36d98f]/80 truncate mt-[2px]">
                        <span className="text-white/45">Hábito:</span> {group.habit_name}
                      </p>
                    ) : null}
                    <p className="text-[12px] text-white/50 mt-[2px]">
                      {group.duration_days != null ? `${group.duration_days} días` : "Sin límite"}
                      {" · "}
                      {group.member_count}/{group.max_participants} participantes
                    </p>
                  </div>
                  <div className={`rounded-[16px] px-[12px] py-[8px] text-right shrink-0 ${isFinished ? "bg-amber-500/20" : "bg-orange-500/20"}`}>
                    {isFinished ? (
                      <Trophy className="size-5 text-amber-300" />
                    ) : (
                      <>
                        <Flame className="size-4 inline text-orange-300 mr-1" />
                        <span className="text-[18px] font-black">{group.shared_streak.current}</span>
                        <span className="text-[11px] text-white/70"> días</span>
                      </>
                    )}
                  </div>
                </div>

                {/* Winner banner */}
                {isFinished && winners.length > 0 && (
                  <div className="rounded-[16px] bg-amber-500/15 border border-amber-500/30 px-[14px] py-[10px] flex items-center gap-[8px]">
                    <Trophy className="size-4 text-amber-300 shrink-0" />
                    <p className="text-[14px] font-bold text-amber-200">
                      {winners.length === 1
                        ? `Ganador: ${winners[0]!.username}`
                        : `Empate: ${winners.map((w) => w.username).join(", ")}`}
                    </p>
                  </div>
                )}

                {/* Today stats + invite code */}
                <div className="grid grid-cols-2 gap-[10px]">
                  {!isFinished && (
                    <div className="rounded-[16px] bg-[var(--bg1)] p-[12px]">
                      <p className="text-[11px] text-white/60 font-bold uppercase">Hoy</p>
                      <p className="text-[18px] font-black">
                        {group.shared_streak.today_completed_members}/{group.shared_streak.required_members}
                      </p>
                    </div>
                  )}
                  <button
                    type="button"
                    onClick={() => void navigator.clipboard?.writeText(group.invite_code)}
                    className={`rounded-[16px] bg-[var(--bg1)] p-[12px] text-left transition-colors hover:brightness-110 ${isFinished ? "col-span-2" : ""}`}
                  >
                    <p className="text-[11px] text-white/60 font-bold uppercase">Código</p>
                    <p className="text-[16px] font-black tracking-[0.08em]">
                      <Copy className="size-3 inline mr-1" />
                      {group.invite_code}
                    </p>
                  </button>
                </div>

                {/* Members */}
                {group.members?.length ? (
                  <div className="space-y-[6px]">
                    {group.members.map((member) => {
                      const { icon: StatusIcon, text, color } = memberLabel(member);
                      return (
                        <div
                          key={member.user_id}
                          className="flex items-center justify-between rounded-[14px] bg-[var(--bg1)] px-[12px] py-[10px]"
                        >
                          <span className="text-[14px] font-bold">{member.username}</span>
                          <span className={`text-[12px] font-bold ${color}`}>
                            <StatusIcon className="inline size-3.5 mr-1" aria-hidden="true" />
                            {text}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                ) : null}

                {/* Leave button */}
                <button
                  onClick={() => void handleLeave(group.id)}
                  disabled={saving}
                  className="inline-flex h-[40px] items-center gap-[8px] rounded-[14px] bg-red-500/14 px-[14px] text-[13px] font-bold text-red-200 disabled:opacity-60"
                >
                  <LogOut className="size-4" />
                  Dejar de compartir
                </button>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
