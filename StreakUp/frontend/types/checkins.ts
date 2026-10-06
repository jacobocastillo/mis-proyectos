import type { Habit } from "./habits";

export interface TodayHabit extends Habit {
  checked_today: boolean;
}

export interface CheckinAchievement {
  emoji: string;
  name: string;
  xp_bonus?: number;
  description?: string | null;
}

export interface CheckinToggleResult {
  checked: boolean;
  habit_id: number;
  date: string;
  new_achievements?: CheckinAchievement[];
}
