"use client";

import { Suspense, useState, useEffect, useRef } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  ArrowLeft,
  Upload,
  Loader2,
  CheckCircle2,
  XCircle,
  Sparkles,
  Flame,
  ImageIcon,
  Info,
  icons,
} from "lucide-react";
import { fetchHabit } from "@/services/habits/habitService";
import { fetchTodayHabits } from "@/services/checkins/checkinService";
import { fetchStatsSummary } from "@/services/stats/statsService";
import { validateHabit, type ValidatePayload } from "@/services/validation/validationService";
import type { Habit, ValidationResult } from "@/types/habits";
import {
  getHabitFrequencyLabel,
  getHabitTargetSummary,
  SECTION_ICONS,
  VALIDATION_TYPE_LABELS,
} from "@/types/habits";
import { ClayMotionBox } from "@/components/ui/clay-motion-box";

type PageStatus = "idle" | "loading" | "success" | "error";

function TimerValidation({ habit, onComplete }: { habit: Habit, onComplete: (minutes: number) => void }) {
  const [timerState, setTimerState] = useState<"idle" | "running" | "paused">("idle");
  const [secondsLeft, setSecondsLeft] = useState((habit.target_duration || 5) * 60);
  const totalSeconds = (habit.target_duration || 5) * 60;
  
  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (timerState === "running") {
      interval = setInterval(() => {
        setSecondsLeft((prev) => {
          if (prev <= 1) {
            clearInterval(interval);
            setTimerState("idle");
            onComplete(habit.target_duration || 5);
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [timerState, habit.target_duration, onComplete]);

  const minutes = Math.floor(secondsLeft / 60);
  const seconds = secondsLeft % 60;
  const progress = totalSeconds > 0 ? secondsLeft / totalSeconds : 1;

  const radius = 60;
  const circumference = 2 * Math.PI * radius;
  const dashOffset = circumference * (1 - progress);

  return (
    <div className="flex flex-col items-center py-6 space-y-6">
      <div className="relative w-40 h-40">
        <svg className="w-full h-full -rotate-90" viewBox="0 0 140 140">
          <circle cx="70" cy="70" r={radius} fill="none" stroke="currentColor" className="text-secondary" strokeWidth="6" />
          <circle
            cx="70" cy="70" r={radius} fill="none" stroke="currentColor" className="text-primary transition-all duration-1000 ease-linear"
            strokeWidth="6" strokeLinecap="round"
            strokeDasharray={circumference} strokeDashoffset={dashOffset}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-3xl font-bold text-foreground tabular-nums">
            {String(minutes).padStart(2, "0")}:{String(seconds).padStart(2, "0")}
          </span>
          <span className="text-xs text-muted-foreground mt-1">
            {timerState === "running" ? "En curso" : timerState === "paused" ? "Pausado" : "Listo"}
          </span>
        </div>
      </div>
      
      <div className="flex w-full gap-3">
        {timerState === "idle" ? (
          <button 
            onClick={() => setTimerState("running")}
            className="flex-1 py-3.5 rounded-xl font-semibold bg-primary text-primary-foreground hover:bg-primary/90 transition-all shadow-md active:scale-[0.98]"
          >
            Comenzar {habit.target_duration} min
          </button>
        ) : (
          <>
            <button 
              onClick={() => setTimerState(timerState === "running" ? "paused" : "running")}
              className="flex-1 py-3.5 rounded-xl font-semibold bg-primary text-primary-foreground hover:bg-primary/90 transition-all shadow-md active:scale-[0.98]"
            >
              {timerState === "running" ? "Pausar" : "Reanudar"}
            </button>
            <button 
              onClick={() => {
                setTimerState("idle");
                setSecondsLeft(totalSeconds);
              }}
              className="flex-1 py-3.5 rounded-xl font-semibold bg-secondary text-foreground hover:bg-secondary/80 border border-border transition-all active:scale-[0.98]"
            >
              Cancelar
            </button>
          </>
        )}
      </div>
    </div>
  );
}

function ValidateHabitPageContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const habitId = Number(searchParams.get("id"));

  const [habit, setHabit] = useState<Habit | null>(null);
  const [loadingHabit, setLoadingHabit] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [imageBase64, setImageBase64] = useState<string | null>(null);
  const [imageMimeType, setImageMimeType] = useState<string | null>(null);
  const [textContent, setTextContent] = useState("");
  const [status, setStatus] = useState<PageStatus>("idle");
  const [result, setResult] = useState<ValidationResult | null>(null);
  const [errorMsg, setErrorMsg] = useState("");

  useEffect(() => {
    async function loadHabit() {
      try {
        const found = await fetchHabit(habitId);
        setHabit(found);
        setLoadError("");
      } catch (err) {
        setHabit(null);
        setLoadError(
          err instanceof Error && err.message.trim()
            ? err.message
            : "No se pudo cargar el hábito para validarlo.",
        );
      } finally {
        setLoadingHabit(false);
      }
    }

    loadHabit();
  }, [habitId]);

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith("image/")) {
      setErrorMsg("Por favor selecciona un archivo de imagen.");
      return;
    }

    if (file.size > 10 * 1024 * 1024) {
      setErrorMsg("La imagen debe ser menor a 10MB.");
      return;
    }

    setErrorMsg("");
    const reader = new FileReader();
    reader.onload = (ev) => {
      const dataUrl = ev.target?.result as string;
      setImagePreview(dataUrl);
      setImageBase64(dataUrl.split(",")[1]);
      setImageMimeType(file.type);
    };
    reader.readAsDataURL(file);
  }

  async function handleValidate(timerMinutes?: number) {
    if (!habit) return;

    setStatus("loading");
    setErrorMsg("");

    const validationType = habit.validation_type ?? "foto";
    const payload: ValidatePayload = { habit_id: habit.id };

    if (validationType === "foto" || validationType === "photo") {
      if (!imageBase64 || !imageMimeType) {
        setErrorMsg("Sube una foto como evidencia.");
        setStatus("idle");
        return;
      }
      payload.image_base64 = imageBase64;
      payload.mime_type = imageMimeType;
    } else if (validationType === "texto" || validationType === "text_ai") {
      if (!textContent.trim()) {
        setErrorMsg("Escribe tu evidencia textual.");
        setStatus("idle");
        return;
      }
      payload.text_content = textContent;
    } else if (validationType === "tiempo" || validationType === "time") {
      const minutesToLog = typeof timerMinutes === "number" ? timerMinutes : habit.target_duration || 5;
      if (!minutesToLog) {
        setErrorMsg("El temporizador no completó los minutos requeridos.");
        setStatus("idle");
        return;
      }
      payload.duration_minutes = minutesToLog;
    }
    // check: no extra payload field needed — server checks timestamp

    try {
      const res = await validateHabit(payload);
      setResult(res);
      setStatus(res.valido ? "success" : "error");
      if (res.valido) {
        void Promise.allSettled([fetchTodayHabits(), fetchStatsSummary()]);
      }
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Error al validar");
      setStatus("error");
    }
  }

  const targetSummary = habit ? getHabitTargetSummary(habit) : null;
  const validationType = habit?.validation_type ?? "foto";

  if (loadingHabit) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="size-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="pt-8 pb-4 max-w-lg mx-auto px-4 text-center">
        <p className="text-muted-foreground mb-4">{loadError}</p>
        <button
          onClick={() => window.location.reload()}
          className="text-primary hover:text-primary/80 font-medium text-sm"
        >
          Reintentar
        </button>
      </div>
    );
  }

  if (!habit) {
    return (
      <div className="pt-8 pb-4 max-w-lg mx-auto px-4 text-center">
        <p className="text-muted-foreground mb-4">Hábito no encontrado.</p>
        <button
          onClick={() => router.push("/habits")}
          className="text-primary hover:text-primary/80 font-medium text-sm"
        >
          ← Volver a hábitos
        </button>
      </div>
    );
  }

  return (
    <div className="pt-8 pb-4 max-w-lg mx-auto px-4 space-y-6">
      <div className="flex items-center gap-3">
        <button
          onClick={() => router.push("/habits")}
          className="flex items-center justify-center size-10 rounded-xl bg-secondary border border-border text-muted-foreground hover:text-foreground hover:border-muted-foreground transition-colors"
        >
          <ArrowLeft className="size-5" />
        </button>
        <div>
          <h1 className="text-2xl font-bold text-foreground">Validar Hábito</h1>
          <p className="text-sm text-muted-foreground">
            {(validationType === "foto" || validationType === "photo") && "Sube una foto como evidencia"}
            {(validationType === "texto") && "Escribe tu bitácora de progreso"}
            {(validationType === "text_ai") && "Escribe tu evidencia — la IA la evaluará"}
            {(validationType === "tiempo" || validationType === "time") && "Registra el tiempo completado"}
            {validationType === "check" && `Empieza antes de ${habit.deadline_time ?? "la hora límite"}`}
          </p>
        </div>
      </div>

      <ClayMotionBox className="p-4 flex items-start gap-4">
        <div className="flex items-center justify-center size-14 rounded-xl bg-secondary text-primary text-3xl shrink-0 mt-0.5">
          {(() => {
            let IconComp = icons.Circle;
            if (habit.icon && icons[habit.icon as keyof typeof icons]) {
              IconComp = icons[habit.icon as keyof typeof icons] as never;
            } else {
              const sectionKey = SECTION_ICONS[habit.section];
              if (sectionKey && icons[sectionKey as keyof typeof icons]) {
                IconComp = icons[sectionKey as keyof typeof icons] as never;
              }
            }
            return <IconComp className="size-8" />;
          })()}
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-foreground font-semibold text-lg leading-tight">{habit.name}</p>
          {habit.description ? (
            <p className="text-muted-foreground text-sm mt-1 line-clamp-2">{habit.description}</p>
          ) : null}
          <div className="flex flex-wrap gap-1.5 mt-2">
            <span className="inline-flex items-center rounded-full bg-primary/10 text-primary px-2 py-0.5 text-[11px] font-medium">
              {VALIDATION_TYPE_LABELS[habit.validation_type ?? "foto"]}
            </span>
            <span className="inline-flex items-center rounded-full bg-secondary text-muted-foreground px-2 py-0.5 text-[11px]">
              {getHabitFrequencyLabel(habit)}
            </span>
            {targetSummary ? (
              <span className="inline-flex items-center rounded-full bg-secondary text-foreground px-2 py-0.5 text-[11px] font-medium">
                🎯 {targetSummary}
              </span>
            ) : null}
            {habit.xp_base != null ? (
              <span className="inline-flex items-center rounded-full bg-violet-500/10 text-violet-400 px-2 py-0.5 text-[11px] font-medium">
                {habit.xp_base} XP base
              </span>
            ) : null}
          </div>
        </div>
      </ClayMotionBox>

      {/* Evidence guidance card — shown only in idle state */}
      {status === "idle" && (
        <div className="rounded-xl border border-blue-500/20 bg-blue-500/5 p-4 flex gap-3">
          <Info className="size-4 text-blue-400 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <p className="text-blue-300 text-xs font-semibold uppercase tracking-wider">Evidencia esperada</p>
            <p className="text-sm text-foreground/90">
              {(validationType === "foto" || validationType === "photo") && (habit.description || `Sube una foto que demuestre que completaste "${habit.name}".`)}
              {validationType === "texto" && (habit.description || `Escribe una breve recapitulación sobre "${habit.name}".`)}
              {validationType === "text_ai" && (habit.description || `Escribe una descripción de lo que hiciste para "${habit.name}". La IA evaluará si corresponde al hábito.`)}
              {(validationType === "tiempo" || validationType === "time") && (habit.description || `Ingresa el total de minutos que dedicaste a "${habit.name}".`)}
              {validationType === "check" && (habit.description || `Confirma que empezaste "${habit.name}" antes de ${habit.deadline_time ?? "la hora límite"}.`)}
            </p>
            {targetSummary ? (
              <p className="text-xs text-muted-foreground mt-1">
                Objetivo del hábito: <span className="font-medium text-foreground">{targetSummary}</span>
              </p>
            ) : null}
          </div>
        </div>
      )}

      {status === "idle" && (validationType === "foto" || validationType === "photo") && (
        <div className="space-y-4">
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            capture="environment"
            onChange={handleFileChange}
            className="hidden"
          />

          {!imagePreview ? (
            <ClayMotionBox className="p-0">
              <button
                onClick={() => fileInputRef.current?.click()}
                className="w-full rounded-xl border-2 border-dashed border-border bg-background/50 hover:border-primary/50 hover:bg-primary/5 p-12 flex flex-col items-center gap-3 transition-all duration-300 group"
              >
                <div className="size-16 rounded-full bg-secondary flex items-center justify-center group-hover:bg-primary/20 transition-colors">
                  <Upload className="size-7 text-muted-foreground group-hover:text-primary transition-colors" />
                </div>
                <div className="text-center">
                  <p className="text-foreground font-medium text-sm">
                    Toca para subir una imagen
                  </p>
                  <p className="text-muted-foreground text-xs mt-1">
                    JPG, PNG o WebP · Máximo 10MB
                  </p>
                </div>
              </button>
            </ClayMotionBox>
          ) : (
            <div className="space-y-3">
              <div className="relative rounded-xl overflow-hidden border border-border">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={imagePreview}
                  alt="Preview de evidencia"
                  className="w-full h-64 object-cover"
                />
                <button
                  onClick={() => {
                    setImagePreview(null);
                    setImageBase64(null);
                    setImageMimeType(null);
                    if (fileInputRef.current) fileInputRef.current.value = "";
                  }}
                  className="absolute top-3 right-3 size-8 rounded-full bg-black/60 backdrop-blur-sm flex items-center justify-center text-white hover:bg-black/80 transition-colors"
                >
                  ✕
                </button>
              </div>
              <button
                onClick={() => fileInputRef.current?.click()}
                className="w-full text-center text-sm text-muted-foreground hover:text-foreground transition-colors py-2"
              >
                <ImageIcon className="size-4 inline mr-1" />
                Cambiar imagen
              </button>
            </div>
          )}

          {errorMsg && (
            <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
              {errorMsg}
            </div>
          )}

          <button
            onClick={() => handleValidate()}
            disabled={!imageBase64}
            className="w-full py-3.5 rounded-xl font-semibold text-primary-foreground transition-all duration-300 disabled:opacity-30 disabled:cursor-not-allowed bg-primary hover:bg-primary/90 shadow-[0_0_20px_rgba(93,95,239,0.3)] hover:shadow-[0_0_28px_rgba(93,95,239,0.5)] active:scale-[0.98]"
          >
            <Sparkles className="size-4 inline mr-2" />
            Validar foto con IA
          </button>
        </div>
      )}

      {status === "idle" && (validationType === "texto" || validationType === "text_ai") && (
        <div className="space-y-4">
          <textarea
            value={textContent}
            onChange={(e) => setTextContent(e.target.value)}
            placeholder="Escribe tu progreso aquí..."
            rows={5}
            maxLength={1000}
            className="w-full px-4 py-3 bg-background border border-border text-foreground rounded-xl focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-colors resize-none"
          />
          {errorMsg && (
            <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
              {errorMsg}
            </div>
          )}
          <button
            onClick={() => handleValidate()}
            disabled={!textContent.trim()}
            className="w-full py-3.5 rounded-xl font-semibold text-primary-foreground transition-all duration-300 disabled:opacity-30 border bg-primary hover:bg-primary/90"
          >
            {validationType === "text_ai" ? (
              <>
                <Sparkles className="size-4 inline mr-2" />
                Validar texto con IA
              </>
            ) : "Validar texto"}
          </button>
        </div>
      )}

      {status === "idle" && validationType === "check" && (
        <div className="space-y-4">
          <div className="rounded-xl border border-border bg-secondary/50 p-6 text-center space-y-2">
            <p className="text-foreground font-semibold text-lg">
              Hora límite: {habit.deadline_time ?? "—"}
            </p>
            <p className="text-muted-foreground text-sm">
              El servidor registrará la hora exacta de tu confirmación.
            </p>
          </div>
          {errorMsg && (
            <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
              {errorMsg}
            </div>
          )}
          <button
            onClick={() => handleValidate()}
            className="w-full py-3.5 rounded-xl font-semibold text-primary-foreground bg-primary hover:bg-primary/90 transition-all shadow-md active:scale-[0.98]"
          >
            <CheckCircle2 className="size-4 inline mr-2" />
            Confirmar que empecé a tiempo
          </button>
        </div>
      )}

      {status === "idle" && (validationType === "tiempo" || validationType === "time") && (
        <div className="space-y-4">
          <TimerValidation habit={habit} onComplete={handleValidate} />
          {errorMsg && (
            <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400 mt-4">
              {errorMsg}
            </div>
          )}
        </div>
      )}

      {status === "loading" && (
        <ClayMotionBox className="p-8 flex flex-col items-center gap-4">
          <div className="relative">
            <div className="size-16 rounded-full bg-primary/20 flex items-center justify-center">
              <Loader2 className="size-8 text-primary animate-spin" />
            </div>
            <div className="absolute inset-0 size-16 rounded-full border-2 border-primary/20 animate-ping" />
          </div>
          <div className="text-center">
            <p className="text-foreground font-semibold">Validando...</p>
            <p className="text-muted-foreground text-sm mt-1">
              {validationType === "foto" ? "La IA está verificando tu evidencia fotográfica" : "Procesando tu evidencia"}
            </p>
          </div>
        </ClayMotionBox>
      )}

      {status === "success" && result && (
        <div className="space-y-4">
          <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-6 space-y-4">
            <div className="flex items-center gap-3">
              <div className="size-12 rounded-full bg-emerald-500/20 flex items-center justify-center">
                <CheckCircle2 className="size-6 text-emerald-400" />
              </div>
              <div>
                <p className="text-foreground font-semibold text-lg">¡Validación exitosa!</p>
                <p className="text-emerald-400 text-sm">{result.razon}</p>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="rounded-lg bg-secondary p-4 text-center">
                <Sparkles className="size-5 text-primary mx-auto mb-2" />
                <p className="text-2xl font-bold text-foreground">+{result.xp_ganado ?? 0}</p>
                <p className="text-xs text-muted-foreground">XP ganado</p>
              </div>
              <div className="rounded-lg bg-secondary p-4 text-center">
                <Flame className="size-5 text-orange-400 mx-auto mb-2" />
                <p className="text-2xl font-bold text-foreground">{result.nueva_racha ?? 0}</p>
                <p className="text-xs text-muted-foreground">Racha actual</p>
              </div>
            </div>

            {result.feedback?.message ? (
              <div className="rounded-lg bg-secondary p-4">
                <p className="text-sm text-foreground">{result.feedback.message}</p>
              </div>
            ) : null}

            {result.difficulty_recommendation ? (
              <div className="rounded-lg bg-secondary p-4">
                <p className="text-xs text-muted-foreground mb-1">Dificultad sugerida</p>
                <p className="text-sm font-semibold text-foreground">
                  {result.difficulty_recommendation.level} · {Math.round(result.difficulty_recommendation.confidence * 100)}%
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  {result.difficulty_recommendation.explanation}
                </p>
              </div>
            ) : null}
          </div>

          <button
            onClick={() => router.push("/habits")}
            className="w-full py-3.5 rounded-xl font-semibold text-primary-foreground bg-primary hover:bg-primary/90 transition-colors"
          >
            Volver a hábitos
          </button>
        </div>
      )}

      {status === "error" && result && (
        <div className="space-y-4">
          <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-6 space-y-4">
            <div className="flex items-center gap-3">
              <div className="size-12 rounded-full bg-red-500/20 flex items-center justify-center">
                <XCircle className="size-6 text-red-400" />
              </div>
              <div>
                <p className="text-foreground font-semibold text-lg">Validación rechazada</p>
                <p className="text-red-400 text-sm">{result.razon}</p>
              </div>
            </div>

            <div className="rounded-lg bg-secondary p-4">
              <p className="text-xs text-muted-foreground mb-1">Confianza del modelo</p>
              <p className="text-foreground font-semibold">{Math.round(result.confianza * 100)}%</p>
            </div>

            {result.feedback?.message ? (
              <div className="rounded-lg bg-secondary p-4">
                <p className="text-sm text-foreground">{result.feedback.message}</p>
              </div>
            ) : null}

            {result.difficulty_recommendation ? (
              <div className="rounded-lg bg-secondary p-4">
                <p className="text-xs text-muted-foreground mb-1">Dificultad sugerida</p>
                <p className="text-sm font-semibold text-foreground">
                  {result.difficulty_recommendation.level} · {Math.round(result.difficulty_recommendation.confidence * 100)}%
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  {result.difficulty_recommendation.explanation}
                </p>
              </div>
            ) : null}
          </div>

          <div className="grid grid-cols-2 gap-3">
            <button
              onClick={() => {
                setStatus("idle");
                setResult(null);
              }}
              className="py-3 rounded-xl font-semibold text-foreground bg-secondary hover:bg-secondary/80 border border-border transition-colors"
            >
              Intentar otra vez
            </button>
            <button
              onClick={() => router.push("/habits")}
              className="py-3 rounded-xl font-semibold text-primary-foreground bg-primary hover:bg-primary/90 transition-colors"
            >
              Volver
            </button>
          </div>
        </div>
      )}

      {status === "error" && !result && errorMsg && (
        <div className="space-y-4">
          <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-6">
            <p className="text-red-400 font-medium">{errorMsg}</p>
          </div>
          <button
            onClick={() => {
              setStatus("idle");
              setErrorMsg("");
            }}
            className="w-full py-3 rounded-xl font-semibold text-primary-foreground bg-primary hover:bg-primary/90 transition-colors"
          >
            Reintentar
          </button>
        </div>
      )}
    </div>
  );
}

export default function ValidateHabitPage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center min-h-[60vh]">
          <div className="size-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
        </div>
      }
    >
      <ValidateHabitPageContent />
    </Suspense>
  );
}
