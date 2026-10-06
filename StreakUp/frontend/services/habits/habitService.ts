import {
  apiDelete,
  apiGet,
  apiPost,
  apiPut,
  API_ENDPOINTS,
  shouldUseOfflineFallback,
} from "@/services/api/client";
import {
  cacheHabits,
  createLocalHabit,
  deleteLocalHabit,
  getLocalHabits,
  updateLocalHabit,
  upsertLocalHabit,
} from "@/services/storage/localData"; 
import type { Habit, HabitCatalogItem, CreateHabitPayload, UpdateHabitPayload } from "@/types/habits";

export async function fetchHabitCatalog(): Promise<HabitCatalogItem[]> {
  return apiGet<HabitCatalogItem[]>(API_ENDPOINTS.habits.catalog);
}

export async function fetchHabits(): Promise<Habit[]> {
  try {
    const habits = await apiGet<Habit[]>(API_ENDPOINTS.habits.list);
    return cacheHabits(habits);
  } catch (error) {
    // Local habit reads are allowed only in explicit offline mode.
    if (shouldUseOfflineFallback(error)) {
      return getLocalHabits();
    }
    throw error;
  }
}

export async function fetchHabit(id: number): Promise<Habit> {
  try {
    const habit = await apiGet<Habit>(API_ENDPOINTS.habits.detail(id));
    return upsertLocalHabit(habit);
  } catch (error) {
    if (shouldUseOfflineFallback(error)) {
      const habit = getLocalHabits().find((candidate) => candidate.id === id);
      if (habit) {
        return habit;
      }
      throw new Error("Hábito no encontrado.");
    }
    throw error;
  }
}

export async function createHabit(payload: CreateHabitPayload): Promise<Habit> {
  try {
    const habit = await apiPost<Habit>(API_ENDPOINTS.habits.create, JSON.stringify(payload));
    return upsertLocalHabit(habit);
  } catch (error) {
    // Connected mode must fail honestly for writes; only explicit offline mode can emulate them.
    if (shouldUseOfflineFallback(error)) {
      return createLocalHabit(payload);
    }
    throw error;
  }
}

export async function updateHabit(id: number, payload: UpdateHabitPayload): Promise<Habit> {
  try {
    const habit = await apiPut<Habit>(API_ENDPOINTS.habits.update(id), JSON.stringify(payload));
    return upsertLocalHabit(habit);
  } catch (error) {
    if (shouldUseOfflineFallback(error)) {
      return updateLocalHabit(id, payload);
    }
    throw error;
  }
}

export async function deleteHabit(id: number): Promise<void> {
  try {
    await apiDelete<void>(API_ENDPOINTS.habits.delete(id));
    deleteLocalHabit(id);
  } catch (error) {
    // Connected mode must fail honestly for writes; only explicit offline mode can emulate them.
    if (shouldUseOfflineFallback(error)) {
      deleteLocalHabit(id);
      return;
    }
    throw error;
  }
}
