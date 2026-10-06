import { apiGet, apiPost, API_ENDPOINTS, shouldUseOfflineFallback } from "@/services/api/client";
import { getSession } from "@/services/auth/authService";
import {
  cacheTodayHabits,
  getLocalHabitById,
  getLocalTodayHabits,
  syncLocalCheckinResult,
  toggleLocalCheckin,
} from "@/services/storage/localData";
import { enqueueOrCancelToggleCheckin } from "@/services/sync/syncQueue";
import type { ValidationType } from "@/types/habits";
import type { CheckinToggleResult, TodayHabit } from "@/types/checkins";

interface ToggleCheckinPayload {
  habit_id: number;
  date?: string;
}

function isValidationGated(validationType?: ValidationType | null): boolean {
  return Boolean(validationType) && validationType !== "check";
}

export async function fetchTodayHabits(): Promise<TodayHabit[]> {
  try {
    const habits = await apiGet<TodayHabit[]>(API_ENDPOINTS.checkins.today);
    return cacheTodayHabits(habits);
  } catch (error) {
    // Local today data is only valid when offline mode is explicitly enabled.
    if (shouldUseOfflineFallback(error)) {
      return getLocalTodayHabits();
    }
    throw error;
  }
}

export async function toggleCheckin(payload: ToggleCheckinPayload): Promise<CheckinToggleResult> {
  try {
    const result = await apiPost<CheckinToggleResult>(
      API_ENDPOINTS.checkins.toggle,
      JSON.stringify(payload),
    );
    return syncLocalCheckinResult(result);
  } catch (error) {
    if (shouldUseOfflineFallback(error)) {
      const today = new Date().toISOString().slice(0, 10);
      const date = payload.date ?? today;
      const session = getSession();
      const userId = Number(session?.user.id ?? 0);
      const habit = getLocalHabitById(payload.habit_id, userId);

      if (isValidationGated(habit?.validation_type)) {
        throw new Error(
          "Este hábito requiere validación del servidor. Conéctate para registrar tu progreso.",
        );
      }

      const result = toggleLocalCheckin(payload.habit_id, userId, date);
      enqueueOrCancelToggleCheckin(payload.habit_id, date, userId);
      return result;
    }
    throw error;
  }
}
