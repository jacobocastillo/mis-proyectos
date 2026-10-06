export type PomodoroTheme = "fire" | "candle" | "ice" | "hourglass";

export interface PomodoroSession {
  id: number;
  user_id: number;
  habit_id: number | null;
  theme: PomodoroTheme;
  study_minutes: number;
  break_minutes: number;
  cycles: number;
  completed: boolean;
  interruption_count: number;
  bonus_xp_awarded: number | null;
  started_at: string | null;
  completed_at: string | null;
  xp_awarded?: number | null;
  bonus_xp?: number | null;
}

export interface CreatePomodoroSessionPayload {
  habit_id?: number | null;
  theme?: PomodoroTheme;
  study_minutes?: number;
  break_minutes?: number;
  cycles?: number;
}
