"use client";

import { useEffect, useMemo, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { createHabit, fetchHabitCatalog } from "@/services/habits/habitService";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { ClayMotionBox } from "@/components/ui/clay-motion-box";
import { Input } from "@/components/ui/input";
import {
  getHabitTargetSummary,
  FREQUENCY_LABELS,
  WEEKDAY_LABELS,
  VALIDATION_TYPE_LABELS,
  type HabitCatalogItem,
  type HabitFrequency,
} from "@/types/habits";

const FREQUENCIES: Array<{ value: HabitFrequency; label: string }> = [
  { value: "daily", label: FREQUENCY_LABELS.daily },
  { value: "weekly", label: FREQUENCY_LABELS.weekly },
  { value: "custom", label: FREQUENCY_LABELS.custom },
];

const WEEKDAYS = Object.entries(WEEKDAY_LABELS).map(([value, label]) => ({
  value: Number(value),
  label,
}));

function isTimeType(vt: string): boolean {
  return vt === "tiempo" || vt === "time";
}
function isTextType(vt: string): boolean {
  return vt === "texto" || vt === "text_ai";
}

export default function NewHabitPage() {
  const router = useRouter();
  const [catalog, setCatalog] = useState<HabitCatalogItem[]>([]);
  const [selectedHabitId, setSelectedHabitId] = useState<number | null>(null);
  const [customName, setCustomName] = useState("");
  const [description, setDescription] = useState("");
  const [frequency, setFrequency] = useState<HabitFrequency>("daily");
  const [targetDuration, setTargetDuration] = useState<string>("");
  const [targetQuantity, setTargetQuantity] = useState<string>("");
  const [targetUnit, setTargetUnit] = useState("");
  const [deadlineTime, setDeadlineTime] = useState("");
  const [minTextLength, setMinTextLength] = useState<string>("");
  const [scheduleDays, setScheduleDays] = useState<number[]>([]);
  const [loadingCatalog, setLoadingCatalog] = useState(true);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    async function loadCatalog() {
      try {
        const habits = await fetchHabitCatalog();
        setCatalog(habits);
        const firstHabit = habits[0] ?? null;
        setSelectedHabitId(firstHabit?.id ?? null);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Error al cargar el catálogo.");
      } finally {
        setLoadingCatalog(false);
      }
    }

    void loadCatalog();
  }, []);

  const selectedHabit = useMemo(
    () => catalog.find((habit) => habit.id === selectedHabitId) ?? null,
    [catalog, selectedHabitId],
  );

  useEffect(() => {
    if (!selectedHabit) {
      return;
    }

    setCustomName("");
    setDescription("");
    setFrequency(selectedHabit.frequency);
    setTargetDuration(
      selectedHabit.target_duration !== null ? String(selectedHabit.target_duration) : "",
    );
    setTargetQuantity(
      selectedHabit.target_quantity !== null ? String(selectedHabit.target_quantity) : "",
    );
    setTargetUnit(selectedHabit.target_unit ?? "");
    setDeadlineTime("");
    setMinTextLength("");
    setScheduleDays([]);
  }, [selectedHabit]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");

    if (!selectedHabitId || !selectedHabit) {
      setError("Selecciona un hábito del catálogo.");
      return;
    }

    if (frequency === "custom" && scheduleDays.length === 0) {
      setError("Debes seleccionar al menos un día para la frecuencia personalizada.");
      return;
    }

    const vt = selectedHabit.validation_type;

    setIsLoading(true);

    try {
      await createHabit({
        habito_id: selectedHabitId,
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
      setError(err instanceof Error ? err.message : "Error al asignar el hábito.");
    } finally {
      setIsLoading(false);
    }
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
          Agregar hábito
        </h1>
      </div>

      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400 mb-4">
          {error}
        </div>
      )}

      <ClayMotionBox className="p-6 mt-4">
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="space-y-2">
            <Label className="text-sm font-semibold text-foreground">Hábito del catálogo</Label>
            <select
              value={selectedHabitId ?? ""}
              onChange={(e) => setSelectedHabitId(Number(e.target.value))}
              required
              disabled={loadingCatalog || catalog.length === 0}
              className="w-full h-12 px-4 bg-background border border-border text-foreground rounded-xl focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-colors appearance-none cursor-pointer"
            >
              {catalog.map((habit) => (
                <option key={habit.id} value={habit.id} className="bg-background text-foreground">
                  {habit.name}
                </option>
              ))}
            </select>
          </div>

          {loadingCatalog && (
            <div className="flex justify-center py-6">
              <div className="size-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
            </div>
          )}

          {!loadingCatalog && selectedHabit && (() => {
            const vt = selectedHabit.validation_type;
            return (
              <>
                <div className="rounded-xl border border-border bg-secondary/50 p-4 space-y-2">
                  <p className="text-xs uppercase tracking-wider text-muted-foreground">Base de catálogo</p>
                  <p className="text-foreground font-semibold">{selectedHabit.name}</p>
                  {selectedHabit.description ? (
                    <p className="text-sm text-muted-foreground">{selectedHabit.description}</p>
                  ) : null}
                  <div className="flex flex-wrap gap-2 text-xs">
                    <span className="rounded-full bg-primary/10 text-primary px-3 py-1">
                      {VALIDATION_TYPE_LABELS[vt]}
                    </span>
                    {getHabitTargetSummary(selectedHabit) ? (
                      <span className="rounded-full bg-background text-foreground px-3 py-1">
                        {getHabitTargetSummary(selectedHabit)}
                      </span>
                    ) : null}
                    <span className="rounded-full bg-green-500/10 text-green-600 px-3 py-1">
                      XP base: {selectedHabit.xp_base}
                    </span>
                    {selectedHabit.max_xp_per_day > 0 ? (
                      <span className="rounded-full bg-violet-500/10 text-violet-400 px-3 py-1">
                        Cap: {selectedHabit.max_xp_per_day} XP/día
                      </span>
                    ) : null}
                    {selectedHabit.xp_rate > 0 ? (
                      <span className="rounded-full bg-blue-500/10 text-blue-400 px-3 py-1">
                        +{selectedHabit.xp_rate} XP/min
                      </span>
                    ) : null}
                  </div>
                </div>

                <div className="space-y-2">
                  <Label className="text-sm font-semibold text-foreground">Nombre personalizado</Label>
                  <Input
                    value={customName}
                    onChange={(event) => setCustomName(event.target.value)}
                    placeholder={selectedHabit.name}
                    className="h-12 bg-background border-border text-foreground rounded-xl focus-visible:ring-primary/50 focus-visible:border-primary"
                  />
                </div>

                <div className="space-y-2">
                  <Label className="text-sm font-semibold text-foreground">Descripción personalizada</Label>
                  <textarea
                    value={description}
                    onChange={(event) => setDescription(event.target.value)}
                    placeholder={selectedHabit.description ?? "Describe este hábito"}
                    rows={4}
                    className="w-full px-4 py-3 bg-background border border-border text-foreground rounded-xl focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-colors resize-none"
                  />
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
                            ? "border-primary text-primary bg-primary/10"
                            : "border-border text-foreground bg-background hover:bg-secondary"
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
                                ? "border-primary bg-primary text-primary-foreground"
                                : "border-border bg-background text-muted-foreground hover:border-primary/50"
                            }`}
                          >
                            {day.label}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                )}

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
                        className="h-12 w-28 bg-background border-border text-foreground rounded-xl text-center focus-visible:ring-primary/50 focus-visible:border-primary"
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
                        className="h-12 w-36 bg-background border-border text-foreground rounded-xl text-center focus-visible:ring-primary/50 focus-visible:border-primary"
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
                        className="h-12 w-28 bg-background border-border text-foreground rounded-xl text-center focus-visible:ring-primary/50 focus-visible:border-primary"
                      />
                      <Input
                        value={targetUnit}
                        onChange={(event) => setTargetUnit(event.target.value)}
                        placeholder="vasos, pasos..."
                        className="h-12 flex-1 bg-background border-border text-foreground rounded-xl focus-visible:ring-primary/50 focus-visible:border-primary"
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
                        className="h-12 w-28 bg-background border-border text-foreground rounded-xl text-center focus-visible:ring-primary/50 focus-visible:border-primary"
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
            disabled={isLoading || loadingCatalog || !selectedHabitId}
            className="w-full h-12 rounded-xl text-primary-foreground font-semibold"
          >
            {isLoading ? "Guardando..." : "Agregar a mis hábitos"}
          </Button>
        </form>
      </ClayMotionBox>
    </div>
  );
}
