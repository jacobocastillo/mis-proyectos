"use client";

import React, { useState, useEffect, useRef, useCallback, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Play, Pause, Square, Trophy } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  completePomodoroSession,
  createPomodoroSession,
  fetchPomodoroSessions,
  interruptPomodoroSession,
} from "@/services/pomodoro/pomodoroService";
import { fetchHabits } from "@/services/habits/habitService";
import type { PomodoroSession } from "@/types/pomodoro";
import type { Habit } from "@/types/habits";

const THEMES = {
  fire: { label: "Fuego", bg: "from-orange-950 to-[#0A0A0A]", accent: "#F97316" },
  candle: { label: "Vela", bg: "from-purple-950 to-[#0A0A0A]", accent: "#A855F7" },
  ice: { label: "Hielo", bg: "from-blue-950 to-[#0A0A0A]", accent: "#3B82F6" },
  hourglass: { label: "Reloj", bg: "from-amber-950 to-[#0A0A0A]", accent: "#D97706" },
};

type ThemeKey = keyof typeof THEMES;
type TimerState = "idle" | "focus" | "break" | "finished";

/* ─── Animated Theme Components ─── */

interface AnimProps { progress: number; isPaused?: boolean; isActive?: boolean; }

function FireAnimation({ progress, isPaused, isActive }: AnimProps) {
  const scale = 0.35 + progress * 0.65;
  const opacity = 0.35 + progress * 0.65;
  const glowR = Math.round(20 + progress * 40);

  return (
    <svg viewBox="0 0 140 150" className="w-32 h-36 mx-auto" style={{ filter: isActive && !isPaused ? `drop-shadow(0 0 ${glowR}px rgba(249,115,22,0.7))` : undefined }}>
      {/* Ember particles (static glows) */}
      {isActive && !isPaused && [
        { cx: 50 },
        { cx: 70 },
        { cx: 90 },
      ].map((e, i) => (
        <circle key={i} cx={e.cx} cy={80} r="2.5" fill="#FBBF24" opacity="0.6">
        </circle>
      ))}
      <g transform={`translate(70, 130) scale(${scale})`} opacity={opacity}>
        {/* Outer flame */}
        <path d="M0,-80 C-20,-60 -30,-30 -25,0 C-25,15 -15,20 0,20 C15,20 25,15 25,0 C30,-30 20,-60 0,-80Z" fill="#F97316">
        </path>
        {/* Middle flame */}
        <path d="M0,-55 C-12,-38 -16,-18 -13,0 C-13,10 -6,15 0,15 C6,15 13,10 13,0 C16,-18 12,-38 0,-55Z" fill="#FB923C">
        </path>
        {/* Inner hot core */}
        <path d="M0,-30 C-6,-20 -8,-8 -6,0 C-6,6 -3,9 0,9 C3,9 6,6 6,0 C8,-8 6,-20 0,-30Z" fill="#FEF08A" />
      </g>
    </svg>
  );
}

function CandleAnimation({ progress, isPaused, isActive }: AnimProps) {
  const height = 55 + progress * 45;
  const flameScale = 0.4 + progress * 0.6;

  return (
    <svg viewBox="0 0 120 180" className="w-28 h-40 mx-auto"
      style={{ filter: isActive && !isPaused ? "drop-shadow(0 0 18px rgba(168,85,247,0.6))" : undefined }}>
      {/* Ambient glow behind flame */}
      {isActive && <ellipse cx="60" cy={170 - height - 10} rx="18" ry="8" fill="#A855F7" opacity="0.25"></ellipse>}
      {/* Candle body with gradient */}
      <defs>
        <linearGradient id="candleGrad" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor="#6D28D9" />
          <stop offset="50%" stopColor="#8B5CF6" />
          <stop offset="100%" stopColor="#5B21B6" />
        </linearGradient>
      </defs>
      <rect x="35" y={170 - height} width="50" height={height} rx="5" fill="url(#candleGrad)" />
      {/* Highlight */}
      <rect x="42" y={172 - height} width="8" height={height * 0.6} rx="4" fill="white" opacity="0.12" />
      {/* Wax drips */}
      {progress > 0.25 && <path d={`M35,${175 - height} Q32,${183 - height} 35,${191 - height}`} stroke="#7C3AED" strokeWidth="5" fill="none" strokeLinecap="round" opacity="0.5" />}
      {progress > 0.5  && <path d={`M82,${178 - height} Q85,${186 - height} 82,${196 - height}`} stroke="#6D28D9" strokeWidth="4" fill="none" strokeLinecap="round" opacity="0.4" />}
      {/* Wick */}
      <line x1="60" y1="162 - height" x2="60" y2={168 - height} stroke="#374151" strokeWidth="2.5" />
      {/* Flame */}
      <g transform={`translate(60,${158 - height}) scale(${flameScale})`}>
        <ellipse cx="0" cy="-16" rx="7" ry="14" fill="#FDE68A">
        </ellipse>
        <ellipse cx="0" cy="-13" rx="4" ry="9" fill="#F59E0B">
        </ellipse>
        <ellipse cx="0" cy="-10" rx="2" ry="5" fill="white" opacity="0.6" />
      </g>
    </svg>
  );
}

function IceAnimation({ progress }: AnimProps) {
  const meltY = (1 - progress) * 28;
  const puddleRx = 8 + (1 - progress) * 32;
  const cubeH = 30 + progress * 35;

  return (
    <svg viewBox="0 0 110 140" className="w-28 h-36 mx-auto">
      <defs>
        <linearGradient id="iceGrad" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#BAE6FD" stopOpacity="0.9" />
          <stop offset="100%" stopColor="#3B82F6" stopOpacity="0.5" />
        </linearGradient>
        <filter id="iceBlur"><feGaussianBlur stdDeviation="1" /></filter>
      </defs>
      <g transform={`translate(0,${meltY})`}>
        {/* Main ice block */}
        <rect x="22" y="20" width="66" height={cubeH} rx="7" fill="url(#iceGrad)" />
        {/* Refraction facets */}
        <polygon points="22,20 55,20 40,38" fill="white" opacity="0.18" />
        <polygon points="88,20 55,20 70,35" fill="white" opacity="0.12" />
        {/* Vertical shine */}
        <rect x="32" y="24" width="7" height={cubeH * 0.55} rx="3" fill="white" opacity="0.28" />
        <rect x="44" y="22" width="4" height={cubeH * 0.35} rx="2" fill="white" opacity="0.18" />
        {/* Crack lines */}
        {progress < 0.7 && <line x1="60" y1="28" x2="72" y2={28 + cubeH * 0.4} stroke="white" strokeWidth="1" opacity="0.15" />}
      </g>
      {/* Drip 1 */}
      {progress > 0.15 && progress < 0.92 && (
        <ellipse cx="58" cy={`${70 + meltY}`} rx="3" ry="4" fill="#60A5FA" opacity="0.4">
        </ellipse>
      )}
      {/* Drip 2 */}
      {progress > 0.3 && progress < 0.88 && (
        <ellipse cx="42" cy={`${70 + meltY}`} rx="2" ry="3" fill="#93C5FD" opacity="0.4">
        </ellipse>
      )}
      {/* Puddle */}
      <ellipse cx="55" cy="118" rx={puddleRx} ry="6" fill="#3B82F6" opacity={0.15 + (1 - progress) * 0.25} />
    </svg>
  );
}

function HourglassAnimation({ progress }: AnimProps) {
  const topSand = progress * 34;
  const bottomSand = (1 - progress) * 34;

  return (
    <svg viewBox="0 0 90 130" className={`w-24 h-32 mx-auto`}>
      {/* Frame bars */}
      <rect x="12" y="3" width="66" height="8" rx="3" fill="#D97706" />
      <rect x="12" y="119" width="66" height="8" rx="3" fill="#D97706" />
      {/* Vertical frame rods */}
      <line x1="16" y1="11" x2="16" y2="119" stroke="#B45309" strokeWidth="3" />
      <line x1="74" y1="11" x2="74" y2="119" stroke="#B45309" strokeWidth="3" />
      {/* Glass outline top */}
      <path d="M20,11 L20,48 L45,63 L70,48 L70,11 Z" fill="#FEF3C7" opacity="0.06" stroke="#D97706" strokeWidth="1.5" />
      {/* Glass outline bottom */}
      <path d="M20,119 L20,82 L45,67 L70,82 L70,119 Z" fill="#FEF3C7" opacity="0.06" stroke="#D97706" strokeWidth="1.5" />
      {/* Top sand mass */}
      <path d={`M22,${14 + (34 - topSand)} L45,${50 - topSand * 0.22} L68,${14 + (34 - topSand)} Z`} fill="#FBBF24" opacity="0.75" />
      {/* Bottom sand mass */}
      <path d={`M22,${117 - bottomSand} L45,${117 - bottomSand * 0.75} L68,${117 - bottomSand} L68,117 L22,117 Z`} fill="#FCD34D" opacity="0.75" />
      {/* Sand stream */}
      {progress > 0.04 && progress < 0.96 && (
        <line x1="45" y1="59" x2="45" y2={77 + bottomSand * 0.35} stroke="#FBBF24" strokeWidth="2.5" opacity="0.65">
        </line>
      )}
      {/* Center pinch glow */}
      <ellipse cx="45" cy="63" rx="4" ry="2" fill="#FDE68A" opacity="0.4" />
    </svg>
  );
}

const THEME_ANIMATIONS: Record<ThemeKey, React.FC<AnimProps>> = {
  fire: FireAnimation,
  candle: CandleAnimation,
  ice: IceAnimation,
  hourglass: HourglassAnimation,
};

function PomodoroContent() {
  const searchParams = useSearchParams();
  const themeKey = (searchParams.get("theme") as ThemeKey) || "fire";
  const theme = THEMES[themeKey] || THEMES.fire;
  const ThemeAnim = THEME_ANIMATIONS[themeKey] || THEME_ANIMATIONS.fire;

  const [studyMinutes, setStudyMinutes] = useState(25);
  const [breakMinutes, setBreakMinutes] = useState(5);
  const [cycles, setCycles] = useState(4);

  const [timerState, setTimerState] = useState<TimerState>("idle");
  const [secondsLeft, setSecondsLeft] = useState(25 * 60);
  const [totalSeconds, setTotalSeconds] = useState(25 * 60);
  const [currentCycle, setCurrentCycle] = useState(1);
  const [isPaused, setIsPaused] = useState(false);
  const [activeSessionId, setActiveSessionId] = useState<number | null>(null);
  const [recentSessions, setRecentSessions] = useState<PomodoroSession[]>([]);
  const [sessionError, setSessionError] = useState("");
  const [recentSessionsError, setRecentSessionsError] = useState("");
  const [timeHabits, setTimeHabits] = useState<Habit[]>([]);
  const [selectedHabitId, setSelectedHabitId] = useState<number | null>(null);
  const [xpAwarded, setXpAwarded] = useState<number | null>(null);
  const [bonusXp, setBonusXp] = useState<number | null>(null);

  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const completingSessionRef = useRef(false);

  const clearTimer = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  const loadRecentSessions = useCallback(async () => {
    try {
      setRecentSessions(await fetchPomodoroSessions(5));
      setRecentSessionsError("");
    } catch (error) {
      setRecentSessionsError(
        error instanceof Error && error.message.trim()
          ? error.message
          : "No se pudieron cargar las sesiones recientes reales.",
      );
    }
  }, []);

  useEffect(() => {
    loadRecentSessions();
  }, [loadRecentSessions]);

  useEffect(() => {
    fetchHabits()
      .then((habits) => setTimeHabits(habits.filter((h) => h.pomodoro_enabled && h.active !== false)))
      .catch(() => {/* non-critical, habit selector will be empty */});
  }, []);

  // Timer tick
  useEffect(() => {
    if (timerState !== "idle" && timerState !== "finished" && !isPaused) {
      intervalRef.current = setInterval(() => {
        setSecondsLeft((prev) => {
          if (prev <= 1) {
            clearTimer();
            // Transition to next phase
            if (timerState === "focus") {
              if (currentCycle >= cycles) {
                setTimerState("finished");
                return 0;
              }
              setTimerState("break");
              const breakSecs = breakMinutes * 60;
              setTotalSeconds(breakSecs);
              return breakSecs;
            } else if (timerState === "break") {
              setCurrentCycle((c) => c + 1);
              setTimerState("focus");
              const focusSecs = studyMinutes * 60;
              setTotalSeconds(focusSecs);
              return focusSecs;
            }
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    }

    return () => clearTimer();
  }, [timerState, isPaused, currentCycle, cycles, breakMinutes, studyMinutes, clearTimer]);

  async function startTimer() {
    setSessionError("");

    try {
      const session = await createPomodoroSession({
        theme: themeKey,
        study_minutes: studyMinutes,
        break_minutes: breakMinutes,
        cycles,
        habit_id: selectedHabitId ?? undefined,
      });
      setActiveSessionId(session.id);
      setRecentSessions((prev) => [session, ...prev.filter((existing) => existing.id !== session.id)].slice(0, 5));
      
      const secs = studyMinutes * 60;
      setSecondsLeft(secs);
      setTotalSeconds(secs);
      setCurrentCycle(1);
      setTimerState("focus");
      setIsPaused(false);
      completingSessionRef.current = false;
    } catch (error) {
      setSessionError(error instanceof Error ? error.message : "No se pudo iniciar la sesión.");
    }
  }

  function togglePause() {
    const nowPausing = !isPaused;
    setIsPaused(nowPausing);
    if (nowPausing && activeSessionId !== null) {
      void interruptPomodoroSession(activeSessionId).catch(() => {});
    }
  }

  function stopTimer() {
    if (activeSessionId !== null && timerState !== "finished") {
      void interruptPomodoroSession(activeSessionId).catch(() => {});
    }
    clearTimer();
    setTimerState("idle");
    setSecondsLeft(studyMinutes * 60);
    setTotalSeconds(studyMinutes * 60);
    setIsPaused(false);
    setCurrentCycle(1);
    setActiveSessionId(null);
    setXpAwarded(null);
    setBonusXp(null);
    completingSessionRef.current = false;
  }

  useEffect(() => {
    if (timerState !== "finished" || activeSessionId === null || completingSessionRef.current) {
      return;
    }

    completingSessionRef.current = true;

    void completePomodoroSession(activeSessionId)
      .then((session) => {
        setRecentSessions((prev) => [session, ...prev.filter((existing) => existing.id !== session.id)].slice(0, 5));
        setXpAwarded(session.xp_awarded ?? null);
        setBonusXp(session.bonus_xp ?? null);
        setSessionError("");
      })
      .catch((error) => {
        setSessionError(error instanceof Error ? error.message : "No se pudo completar la sesión.");
      });
  }, [activeSessionId, timerState]);

  const minutes = Math.floor(secondsLeft / 60);
  const seconds = secondsLeft % 60;
  const progress = totalSeconds > 0 ? secondsLeft / totalSeconds : 1;

  // SVG circle calculations
  const radius = 90;
  const circumference = 2 * Math.PI * radius;
  const dashOffset = circumference * (1 - progress);

  return (
    <div className={`min-h-screen bg-gradient-to-b ${theme.bg} flex flex-col pb-[80px]`}>
      {/* Header */}
      <div className="px-4 pt-6 pb-2">
        <Link href="/" className="inline-flex items-center gap-2 text-white/75 hover:text-white transition-colors font-bold">
          <ArrowLeft className="size-5" />
          <span className="text-[15px]">Atrás</span>
        </Link>
      </div>

      <div className="flex-1 flex flex-col items-center px-4 max-w-lg mx-auto w-full">
        {/* Theme Animation */}
        <div className="py-4">
          <ThemeAnim
            progress={progress}
            isPaused={isPaused}
            isActive={timerState !== "idle" && timerState !== "finished"}
          />
        </div>

        {/* Circular Timer */}
        <div className="relative w-52 h-52 mb-[24px]">
          <svg className="w-full h-full -rotate-90" viewBox="0 0 200 200">
            {/* Background circle */}
            <circle cx="100" cy="100" r={radius} fill="none" stroke="currentColor" className="text-white/10" strokeWidth="6" />
            {/* Progress circle */}
            <circle
              cx="100"
              cy="100"
              r={radius}
              fill="none"
              stroke={theme.accent}
              strokeWidth="6"
              strokeLinecap="round"
              strokeDasharray={circumference}
              strokeDashoffset={dashOffset}
              className="transition-all duration-1000 ease-linear drop-shadow-[0_0_12px_currentColor]"
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-[48px] font-black text-white tabular-nums leading-none tracking-tight">
              {String(minutes).padStart(2, "0")}:{String(seconds).padStart(2, "0")}
            </span>
            <span className="text-[13px] text-white/75 font-bold mt-1 uppercase tracking-wider">
              {timerState === "focus" ? "Enfocado" : timerState === "break" ? "Descanso" : timerState === "finished" ? "¡Completado!" : "Listo"}
            </span>
            {timerState !== "idle" && timerState !== "finished" && (
              <span className="text-[11px] text-white/50 font-bold mt-1 bg-white/10 px-2 py-0.5 rounded-full border border-white/5">
                Ciclo {currentCycle}/{cycles}
              </span>
            )}
          </div>
        </div>

        {/* Configuration */}
        <div className="w-full p-[20px] rounded-[24px] bg-white/5 border border-white/10 space-y-[16px] mb-[24px]">
          <h3 className="text-[18px] font-bold text-center">Configuración</h3>

          <div className="space-y-[8px]">
            <Label className="text-[13px] text-white/75 font-bold">Tiempo de estudio (minutos)</Label>
            <Input
              type="number"
              min={1}
              max={120}
              value={studyMinutes}
              onChange={(e) => {
                const v = parseInt(e.target.value) || 25;
                setStudyMinutes(v);
                if (timerState === "idle") {
                  setSecondsLeft(v * 60);
                  setTotalSeconds(v * 60);
                }
              }}
              disabled={timerState !== "idle"}
              className="h-[48px] bg-white/5 border-white/10 text-white text-center text-[18px] font-bold rounded-[16px]"
            />
          </div>

          <div className="space-y-[8px]">
            <Label className="text-[13px] text-white/75 font-bold">Tiempo de descanso (minutos)</Label>
            <Input
              type="number"
              min={1}
              max={60}
              value={breakMinutes}
              onChange={(e) => setBreakMinutes(parseInt(e.target.value) || 5)}
              disabled={timerState !== "idle"}
              className="h-[48px] bg-white/5 border-white/10 text-white text-center text-[18px] font-bold rounded-[16px]"
            />
          </div>

          <div className="space-y-[8px]">
            <Label className="text-[13px] text-white/75 font-bold">Número de ciclos</Label>
            <Input
              type="number"
              min={1}
              max={12}
              value={cycles}
              onChange={(e) => setCycles(parseInt(e.target.value) || 4)}
              disabled={timerState !== "idle"}
              className="h-[48px] bg-white/5 border-white/10 text-white text-center text-[18px] font-bold rounded-[16px]"
            />
          </div>

          {timeHabits.length > 0 && (
            <div className="space-y-[8px]">
              <Label className="text-[13px] text-white/75 font-bold">Hábito vinculado (opcional)</Label>
              <select
                value={selectedHabitId ?? ""}
                onChange={(e) => setSelectedHabitId(e.target.value ? Number(e.target.value) : null)}
                disabled={timerState !== "idle"}
                className="w-full h-[48px] rounded-[16px] bg-white/5 border border-white/10 text-white text-[14px] font-bold px-4 disabled:opacity-50"
              >
                <option value="">Sin hábito</option>
                {timeHabits.map((h) => (
                  <option key={h.id} value={h.id}>{h.custom_name ?? h.name}</option>
                ))}
              </select>
            </div>
          )}
        </div>

        {/* Controls */}
        <div className="w-full space-y-[12px]">
          {sessionError && (
            <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">
              {sessionError}
            </div>
          )}
          {timerState === "idle" ? (
            <Button
              onClick={startTimer}
              className="w-full"
              size="lg"
              variant="sacro"
            >
              <Play className="size-5 mr-2" />
              Comenzar
            </Button>
          ) : timerState === "finished" ? (
            <div className="w-full p-[24px] rounded-[24px] bg-white/5 border border-white/10 text-center space-y-4">
              <Trophy className="size-16 mx-auto animate-bounce" style={{ color: "#FBBF24" }} />
              <div className="space-y-1">
                <p className="text-[20px] font-bold text-white">¡Sesión Completada!</p>
                <p className="text-[13px] text-white/75 font-bold">
                  {cycles} ciclo{cycles !== 1 ? "s" : ""} · {studyMinutes}m enfocado · {breakMinutes}m descanso
                </p>
                {xpAwarded !== null && xpAwarded > 0 && (
                  <p className="text-[13px] font-bold text-yellow-300">+{xpAwarded} XP</p>
                )}
                {xpAwarded === 0 && selectedHabitId !== null && (
                  <p className="text-[11px] text-white/50 font-bold">XP ya registrado hoy</p>
                )}
                {bonusXp !== null && bonusXp > 0 && (
                  <p className="text-[13px] font-bold text-emerald-300">+{bonusXp} XP bonus (sin interrupciones)</p>
                )}
              </div>
              <Button
                onClick={stopTimer}
                className="w-full mt-2"
                size="lg"
                variant="sacro"
              >
                Nueva sesión
              </Button>
            </div>
          ) : (
            <>
              <Button
                onClick={togglePause}
                className="w-full"
                size="lg"
                variant="sacro"
              >
                {isPaused ? (
                  <><Play className="size-5 mr-2" /> Reanudar</>
                ) : (
                  <><Pause className="size-5 mr-2" /> Pausar</>
                )}
              </Button>
              <Button
                onClick={stopTimer}
                className="w-full bg-white/5 hover:bg-red-500/20 text-white border-white/10 hover:border-red-500/30"
                size="lg"
                variant="sacro-ghost"
              >
                <Square className="size-4 mr-2" />
                Finalizar sesión
              </Button>
            </>
          )}
        </div>

        {/* Recent Sessions */}
        <div className="mt-[24px] w-full p-[20px] rounded-[24px] bg-white/5 border border-white/10 space-y-[12px]">
          <div className="flex items-center justify-between">
            <h3 className="text-[16px] font-bold text-white">Sesiones recientes</h3>
            <button
              type="button"
              onClick={() => void loadRecentSessions()}
              className="text-[11px] font-bold text-white/50 hover:text-white transition-colors uppercase tracking-wider"
            >
              Recargar
            </button>
          </div>

          {recentSessionsError ? (
            <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">
              {recentSessionsError}
            </div>
          ) : null}

          {!recentSessionsError && recentSessions.length === 0 ? (
            <p className="text-[13px] text-white/50 font-bold">Aún no hay sesiones guardadas.</p>
          ) : recentSessions.length > 0 ? (
            <div className="space-y-[8px]">
              {recentSessions.map((session) => (
                <div
                  key={session.id}
                  className="flex items-center justify-between rounded-[16px] border border-white/5 bg-white/5 px-[16px] py-[12px]"
                >
                  <div>
                    <p className="text-[14px] font-bold text-white leading-tight mb-1">
                      {THEMES[session.theme]?.label ?? "Pomodoro"} · {session.study_minutes}m
                    </p>
                    <p className="text-[11px] text-white/50 font-bold">
                      {session.cycles} ciclo{session.cycles === 1 ? "" : "s"} · descanso {session.break_minutes}m
                    </p>
                  </div>
                  <span
                    className={`text-[10px] font-bold px-[8px] py-[4px] rounded-full uppercase tracking-wider ${
                      session.completed ? "bg-emerald-500/20 text-emerald-200" : "bg-amber-500/20 text-amber-200"
                    }`}
                  >
                    {session.completed ? "Completa" : "Progreso"}
                  </span>
                </div>
              ))}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}

export default function PomodoroPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-[#0A0A0A] flex items-center justify-center">
        <div className="size-8 border-2 border-white border-t-transparent rounded-full animate-spin" />
      </div>
    }>
      <PomodoroContent />
    </Suspense>
  );
}
