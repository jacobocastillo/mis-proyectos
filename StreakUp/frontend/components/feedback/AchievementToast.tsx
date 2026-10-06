"use client";

/**
 * AchievementToast
 *
 * A premium animated notification that slides in from the top whenever
 * the user unlocks a new achievement. It auto-dismisses after 4 seconds
 * but can also be dismissed manually.
 *
 * Usage — render it once at the app level and call the imperative API:
 *
 *   import { AchievementToast, showAchievementToast } from "@/components/feedback/AchievementToast";
 *
 *   // In any service or component after detecting a new achievement:
 *   showAchievementToast({ emoji: "🔥", name: "Racha de 7 días", xp_bonus: 50 });
 *
 *   // In your root layout:
 *   <AchievementToast />
 */

import { useEffect, useState, useCallback } from "react";
import { X, Sparkles } from "lucide-react";

// ─── Imperative API ──────────────────────────────────────────────────────────

export interface AchievementPayload {
  emoji: string;
  name: string;
  xp_bonus?: number;
  description?: string | null;
}

type Listener = (payload: AchievementPayload) => void;

const listeners = new Set<Listener>();

/** Call this from anywhere — services, hooks, page components — to trigger the toast. */
export function showAchievementToast(payload: AchievementPayload): void {
  listeners.forEach((fn) => fn(payload));
}

// ─── Component ───────────────────────────────────────────────────────────────

const DISPLAY_DURATION_MS = 4_000;

interface ToastState {
  visible: boolean;
  payload: AchievementPayload | null;
}

export function AchievementToast() {
  const [state, setState] = useState<ToastState>({ visible: false, payload: null });
  const timerRef = { current: undefined as ReturnType<typeof setTimeout> | undefined };

  const dismiss = useCallback(() => {
    setState((s) => ({ ...s, visible: false }));
    clearTimeout(timerRef.current);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    function handleNewAchievement(payload: AchievementPayload) {
      clearTimeout(timerRef.current);
      setState({ visible: true, payload });
      timerRef.current = setTimeout(dismiss, DISPLAY_DURATION_MS);
    }

    listeners.add(handleNewAchievement);
    return () => {
      listeners.delete(handleNewAchievement);
      clearTimeout(timerRef.current);
    };
  }, [dismiss]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!state.payload) return null;

  const { emoji, name, xp_bonus, description } = state.payload;

  return (
    <div
      aria-live="assertive"
      aria-atomic="true"
      className="pointer-events-none fixed inset-x-0 top-4 z-[60] flex justify-center px-4"
    >
      <div
        className={`pointer-events-auto w-full max-w-sm transform transition-all duration-500 ease-out ${
          state.visible
            ? "translate-y-0 opacity-100 scale-100"
            : "-translate-y-6 opacity-0 scale-95"
        }`}
      >
        <div className="relative rounded-2xl border border-yellow-400/30 bg-gradient-to-r from-yellow-950/95 via-[#1A1A2E]/98 to-orange-950/95 px-4 py-3.5 shadow-2xl shadow-yellow-500/20 backdrop-blur-md">
          {/* Glow ring */}
          <div className="absolute inset-0 rounded-2xl ring-1 ring-yellow-400/20 pointer-events-none" />

          {/* Content */}
          <div className="flex items-center gap-3">
            {/* Emoji badge */}
            <div className="flex-shrink-0 size-12 rounded-xl bg-gradient-to-br from-yellow-400 to-orange-500 flex items-center justify-center text-2xl shadow-inner shadow-yellow-600/30">
              {emoji}
            </div>

            {/* Text */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-1.5 mb-0.5">
                <Sparkles className="size-3 text-yellow-400 flex-shrink-0" />
                <span className="text-[10px] font-bold uppercase tracking-wider text-yellow-400">
                  ¡Logro desbloqueado!
                </span>
              </div>
              <p className="text-sm font-bold text-white truncate">{name}</p>
              {description && (
                <p className="text-[11px] text-muted-foreground truncate mt-0.5">
                  {description}
                </p>
              )}
              {xp_bonus != null && xp_bonus > 0 && (
                <span className="inline-flex items-center mt-1 text-[10px] font-semibold text-yellow-300 bg-yellow-400/10 rounded-full px-2 py-0.5">
                  +{xp_bonus} XP
                </span>
              )}
            </div>

            {/* Dismiss */}
            <button
              onClick={dismiss}
              className="flex-shrink-0 text-muted-foreground hover:text-white transition-colors p-1"
              aria-label="Cerrar notificación"
            >
              <X className="size-4" />
            </button>
          </div>

          {/* Progress bar */}
          <div className="mt-3 h-0.5 rounded-full bg-white/5 overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-yellow-400 to-orange-400 rounded-full"
              style={{
                animation: state.visible
                  ? `shrink ${DISPLAY_DURATION_MS}ms linear forwards`
                  : "none",
              }}
            />
          </div>
        </div>
      </div>

      {/* Keyframe for the progress-bar drain animation */}
      <style>{`
        @keyframes shrink {
          from { width: 100%; }
          to   { width: 0%; }
        }
      `}</style>
    </div>
  );
}
