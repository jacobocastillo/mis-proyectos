"use client";

import { Suspense, useEffect, useState, type FormEvent } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { ClayMotionBox } from "@/components/ui/clay-motion-box";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { fetchHabit, updateHabit } from "@/services/habits/habitService";
import {
  getHabitTargetSummary,
  FREQUENCY_LABELS,
  WEEKDAY_LABELS,
  VALIDATION_TYPE_LABELS,
  type Habit,
  type HabitFrequency,
} from "@/types/habits";

function isTimeType(vt: string): boolean {
  return vt === "tiempo" || vt === "time";
}
function isTextType(vt: string): boolean {
  return vt === "texto" || vt === "text_ai";
}

const FREQUENCIES: Array<{ value: HabitFrequency; label: string }> = [
  { value: "daily", label: FREQUENCY_LABELS.daily },
  { value: "weekly", label: FREQUENCY_LABELS.weekly },
  { value: "custom", label: FREQUENCY_LABELS.custom },
];

const WEEKDAYS = Object.entries(WEEKDAY_LABELS).map(([value, label]) => ({
  value: Number(value),
  label,
}));

function EditHabitPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const habitId = Number(searchParams.get("id"));

  const [habit, setHabit] = useState<Habit | null>(null);
  const [customName, setCustomName] = useState("");
  const [description, setDescription] = useState("");
  const [frequency, setFrequency] = useState<HabitFrequency>("daily");
  const [targetDuration, setTargetDuration] = useState<string>("");
  const [targetQuantity, setTargetQuantity] = useState<string>("");
  const [targetUnit, setTargetUnit] = useState("");
  const [deadlineTime, setDeadlineTime] = useState("");
  const [minTextLength, setMinTextLength] = useState<string>("");
  const [scheduleDays, setScheduleDays] = useState<number[]>([]);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [loadingHabit, setLoadingHabit] = useState(true);

  useEffect(() => {
    async function load() {
      if (!Number.isInteger(habitId) || habitId <= 0) {
        setError("Selecciona un hábito desde la lista.");
        setLoadingHabit(false);
        return;
      }

      try {
        const loadedHabit = await fetchHabit(habitId);
        setHabit(loadedHabit);
        setCustomName(loadedHabit.custom_name ?? "");
        setDescription(loadedHabit.custom_description ?? "");
        setFrequency(loadedHabit.frequency);
        setTargetDuration(
          loadedHabit.target_duration !== null ? String(loadedHabit.target_duration) : "",
        );
        setTargetQuantity(
          loadedHabit.target_quantity !== null ? String(loadedHabit.target_quantity) : "",
        );
        setTargetUnit(loadedHabit.target_unit ?? "");
        setDeadlineTime(loadedHabit.deadline_time ?? "");
        setMinTextLength(
          loadedHabit.min_text_length != null ? String(loadedHabit.min_text_length) : "",
        );
        setScheduleDays(loadedHabit.schedule_days ?? []);
        setError("");
      } catch (err) {
        setError(
          err instanceof Error && err.message.trim()
            ? err.message
            : "No se pudo cargar el hábito.",
        );
      } finally {
        setLoadingHabit(false);
      }
    }

    void load();
  }, [habitId]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setIsLoading(true);

    if (frequency === "custom" && scheduleDays.length === 0) {
      setError("Debes seleccionar al menos un día para la frecuencia personalizada.");
      setIsLoading(false);
      return;
    }

    const vt = habit?.validation_type ?? "foto";

    try {
      await updateHabit(habitId, {
        custom_name: customName.trim() || null,
        description: description.trim() || null,
        frequency,
        target_duration: isTimeType(vt) && targetDuration.trim() ? Number(targetDuration) : null,
        target_quantity: !isTimeType(vt) && targetQuantity.trim() ? Number(targetQuantity) : null,
        target_unit: !isTimeType(vt) && targetUnit.trim() ? targetUnit.trim() : null,
        deadline_time: vt === "check" && deadlineTime.trim() ? deadlineTime.trim() : null,
        min_text_length: isTextType(vt) && minTextLength.trim() ? Number(minTextLength) : null,
        schedule_days: frequency === "custom" ? scheduleDays : undefined,
      });
      router.push("/habits");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al actualizar hábito.");
    } finally {
      setIsLoading(false);
    }
  }

  if (loadingHabit) {
    return (
      <div className="flex justify-center py-20">
        <div className="size-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!habit) {
    return (
      <div className="pt-6 pb-4 max-w-lg mx-auto px-4">
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          {error || "Hábito no encontrado."}
        </div>
      </div>
    );
  }

  return (
    <div className="pt-6 pb-4 max-w-lg mx-auto px-4">
      <div className="flex items-center gap-4 mb-6">
        <Link
          href="/habits"
          className="flex items-center justify-center size-10 rounded-lg text-muted-foreground hover:bg-secondary hover:text-foreground transition-colors"
        >
          <ArrowLeft className="size-5" />
        </Link>
        <h1 className="text-xl font-bold text-foreground flex-1 text-center pr-10">
          Editar hábito
        </h1>
      </div>

      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400 mb-4">
          {error}
        </div>
      )}

      <ClayMotionBox className="p-5 mb-4 space-y-2">
        <p className="text-xs uppercase tracking-wider text-muted-foreground">Base de catálogo</p>
        <p className="text-foreground font-semibold">{habit.name}</p>
        {habit.description ? (
          <p className="text-sm text-muted-foreground">{habit.description}</p>
        ) : null}
        <div className="flex flex-wrap gap-2 text-xs">
          <span className="rounded-full bg-primary/10 text-primary px-3 py-1">
            {VALIDATION_TYPE_LABELS[habit.validation_type ?? "foto"]}
          </span>
          {getHabitTargetSummary(habit) ? (
            <span className="rounded-full bg-secondary text-foreground px-3 py-1">
              {getHabitTargetSummary(habit)}
            </span>
          ) : null}
          {habit.xp_base != null ? (
            <span className="rounded-full bg-green-500/10 text-green-600 px-3 py-1">
              XP base: {habit.xp_base}
            </span>
          ) : null}
          {(habit.max_xp_per_day ?? 0) > 0 ? (
            <span className="rounded-full bg-violet-500/10 text-violet-400 px-3 py-1">
              Cap: {habit.max_xp_per_day} XP/día
            </span>
          ) : null}
          {(habit.xp_rate ?? 0) > 0 ? (
            <span className="rounded-full bg-blue-500/10 text-blue-400 px-3 py-1">
              +{habit.xp_rate} XP/min
            </span>
          ) : null}
        </div>
      </ClayMotionBox>

      <ClayMotionBox className="p-6 mt-4">
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="space-y-2">
            <Label className="text-sm font-semibold text-foreground">Nombre personalizado</Label>
            <Input
              value={customName}
              onChange={(event) => setCustomName(event.target.value)}
              placeholder={habit.name}
              maxLength={120}
              className="h-12 bg-white/13 border border-white/20 text-white rounded-xl focus-visible:ring-[var(--purple)]/50 focus-visible:border-[var(--purple)] placeholder:text-white/40 px-4"
            />
            <p className="text-xs text-muted-foreground">
              Déjalo vacío para usar el nombre del catálogo: <span className="italic">{habit.name}</span>.
            </p>
          </div>

          <div className="space-y-2">
            <Label className="text-sm font-semibold text-foreground">Descripción personalizada</Label>
            <textarea
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              placeholder={habit.description ?? "Describe qué evidencia contará como completado (ej: foto con vaso de agua lleno)"}
              rows={4}
              maxLength={2000}
              className="w-full px-4 py-3 bg-white/13 border border-white/20 text-white rounded-xl focus:outline-none focus:ring-2 focus:ring-[var(--purple)]/50 focus:border-[var(--purple)] transition-colors resize-none placeholder:text-white/40"
            />
            <p className="text-xs text-muted-foreground">
              Esta descripción guía la validación con IA. Sé específico sobre qué evidencia se espera.
            </p>
          </div>

          <div className="space-y-2">
            <Label className="text-sm font-semibold text-foreground">Frecuencia</Label>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
              {FREQUENCIES.map((option) => (
                <button
                  key={option.value}
                  type="button"
                  onClick={() => setFrequency(option.value)}
                  className={`h-11 rounded-xl text-sm font-medium border transition-all duration-200 ${
                    frequency === option.value
                      ? "border-[var(--purple2)] text-white bg-[var(--purple)]"
                      : "border-white/20 text-white/74 bg-white/13 hover:bg-white/20"
                  }`}
                >
                  {option.label}
                </button>
              ))}
            </div>
          </div>

          {frequency === "custom" && (
            <div className="space-y-2">
              <Label className="text-sm font-semibold text-foreground">Días de la semana</Label>
              <div className="flex flex-wrap gap-2">
                {WEEKDAYS.map((day) => {
                  const isSelected = scheduleDays.includes(day.value);
                  return (
                    <button
                      key={day.value}
                      type="button"
                      onClick={() => {
                        if (isSelected) {
                          setScheduleDays((prev) => prev.filter((d) => d !== day.value));
                        } else {
                          setScheduleDays((prev) => [...prev, day.value].sort());
                        }
                      }}
                      className={`size-10 rounded-full text-sm font-semibold border transition-all duration-200 ${
                        isSelected
                          ? "border-[var(--purple2)] bg-[var(--purple)] text-white"
                          : "border-white/20 bg-white/13 text-white/74 hover:border-[var(--purple)]/50"
                      }`}
                    >
                      {day.label}
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {(() => {
            const vt = habit.validation_type ?? "foto";
            return (
              <>
                {isTimeType(vt) && (
                  <div className="space-y-2">
                    <Label className="text-sm font-semibold text-foreground">Duración objetivo</Label>
                    <div className="flex items-center gap-3">
                      <Input
                        type="number"
                        min={1}
                        value={targetDuration}
                        onChange={(event) => setTargetDuration(event.target.value)}
                        placeholder="e.g. 15"
                        className="h-12 w-28 bg-white/13 border border-white/20 text-white rounded-xl text-center focus-visible:ring-[var(--purple)]/50 focus-visible:border-[var(--purple)] placeholder:text-white/40"
                      />
                      <span className="text-muted-foreground text-sm">minutos</span>
                    </div>
                  </div>
                )}

                {vt === "check" && (
                  <div className="space-y-2">
                    <Label className="text-sm font-semibold text-foreground">Hora límite</Label>
                    <div className="flex items-center gap-3">
                      <Input
                        type="time"
                        value={deadlineTime}
                        onChange={(event) => setDeadlineTime(event.target.value)}
                        required
                        className="h-12 w-36 bg-white/13 border border-white/20 text-white rounded-xl text-center focus-visible:ring-[var(--purple)]/50 focus-visible:border-[var(--purple)]"
                      />
                      <span className="text-muted-foreground text-sm">hora del día</span>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      Debes confirmar que empezaste antes de esta hora para ganar XP.
                    </p>
                  </div>
                )}

                {!isTimeType(vt) && vt !== "check" && (
                  <div className="space-y-2">
                    <Label className="text-sm font-semibold text-foreground">Meta de cantidad (Opcional)</Label>
                    <div className="flex items-center gap-3">
                      <Input
                        type="number"
                        min={1}
                        value={targetQuantity}
                        onChange={(event) => setTargetQuantity(event.target.value)}
                        placeholder="e.g. 3"
                        className="h-12 w-28 bg-white/13 border border-white/20 text-white rounded-xl text-center focus-visible:ring-[var(--purple)]/50 focus-visible:border-[var(--purple)] placeholder:text-white/40"
                      />
                      <Input
                        value={targetUnit}
                        onChange={(event) => setTargetUnit(event.target.value)}
                        placeholder="vasos, pasos..."
                        className="h-12 flex-1 bg-white/13 border border-white/20 text-white rounded-xl focus-visible:ring-[var(--purple)]/50 focus-visible:border-[var(--purple)] placeholder:text-white/40 px-4"
                      />
                    </div>
                  </div>
                )}

                {isTextType(vt) && (
                  <div className="space-y-2 animate-in fade-in slide-in-from-top-2 duration-300">
                    <Label className="text-sm font-semibold text-foreground">Longitud mínima de texto (Opcional)</Label>
                    <div className="flex items-center gap-3">
                      <Input
                        type="number"
                        min={1}
                        value={minTextLength}
                        onChange={(event) => setMinTextLength(event.target.value)}
                        placeholder="e.g. 50"
                        className="h-12 w-28 bg-white/13 border border-white/20 text-white rounded-xl text-center focus-visible:ring-[var(--purple)]/50 focus-visible:border-[var(--purple)] placeholder:text-white/40"
                      />
                      <span className="text-muted-foreground text-sm">caracteres</span>
                    </div>
                  </div>
                )}
              </>
            );
          })()}

          <Button
            type="submit"
            disabled={isLoading}
            className="w-full h-[48px] rounded-[20px] text-[16px] font-bold bg-[var(--purple)] hover:bg-[var(--purple2)] text-white shadow-[0_0_15px_rgba(157,85,255,0.4)] transition-transform active:scale-95"
          >
            {isLoading ? "Guardando..." : "Guardar cambios"}
          </Button>
        </form>
      </ClayMotionBox>
    </div>
  );
}

export default function EditHabitPage() {
  return (
    <Suspense
      fallback={
        <div className="flex justify-center py-20">
          <div className="size-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
        </div>
      }
    >
      <EditHabitPageContent />
    </Suspense>
  );
}
