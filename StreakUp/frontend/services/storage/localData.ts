import { getSession } from "@/services/auth/authService";
import { DB_KEYS, dbRead, dbWrite } from "@/services/storage/offlineDb";
import { runMigrationsOnce } from "@/services/storage/localMigrations";
import type { CheckinToggleResult, TodayHabit } from "@/types/checkins";
import type { Habit, CreateHabitPayload, UpdateHabitPayload } from "@/types/habits";
import type { CreatePomodoroSessionPayload, PomodoroSession } from "@/types/pomodoro";
import type { StatsSummary } from "@/types/stats";

// This module serves two distinct purposes:
// 1. cache successful server responses for later offline use
// 2. emulate write flows only when offline mode is explicitly enabled
// Connected mode must never call these write helpers after a network failure.

interface StoredCheckin {
  user_id: number;
  habit_id: number;
  date: string;
}

function getCurrentUserId(): number {
  const session = getSession();
  const userId = Number(session?.user.id ?? 0);
  return Number.isFinite(userId) ? userId : 0;
}

function getNowIso(): string {
  return new Date().toISOString();
}

function getTodayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

function replaceUserRecords<T extends { user_id: number }>(
  records: T[],
  userId: number,
  nextRecords: T[],
): T[] {
  return records.filter((record) => record.user_id !== userId).concat(nextRecords);
}

function nextNegativeId(existingIds: number[]): number {
  const minimum = existingIds.reduce((min, id) => Math.min(min, id), 0);
  return minimum <= 0 ? minimum - 1 : -1;
}

function readAllHabits(): Habit[] {
  runMigrationsOnce();
  return dbRead<Habit[]>(DB_KEYS.habits, []);
}

function writeAllHabits(habits: Habit[]): void {
  dbWrite(DB_KEYS.habits, habits);
}

function readAllCheckins(): StoredCheckin[] {
  runMigrationsOnce();
  return dbRead<StoredCheckin[]>(DB_KEYS.checkins, []);
}

function writeAllCheckins(checkins: StoredCheckin[]): void {
  dbWrite(DB_KEYS.checkins, checkins);
}

function readAllPomodoroSessions(): PomodoroSession[] {
  runMigrationsOnce();
  return dbRead<PomodoroSession[]>(DB_KEYS.pomodoroSessions, []);
}

function writeAllPomodoroSessions(sessions: PomodoroSession[]): void {
  dbWrite(DB_KEYS.pomodoroSessions, sessions);
}

export function cacheHabits(habits: Habit[], userId = getCurrentUserId()): Habit[] {
  if (userId <= 0) {
    return habits;
  }

  const normalizedHabits = habits.map((habit) => ({
    ...habit,
    user_id: habit.user_id ?? userId,
  }));

  const allHabits = readAllHabits();
  writeAllHabits(replaceUserRecords(allHabits, userId, normalizedHabits));
  return normalizedHabits;
}

export function getLocalHabits(userId = getCurrentUserId()): Habit[] {
  return readAllHabits()
    .filter((habit) => habit.user_id === userId)
    .sort((left, right) => left.name.localeCompare(right.name, "es"));
}

export function getLocalHabitById(id: number, userId = getCurrentUserId()): Habit | null {
  return getLocalHabits(userId).find((habit) => habit.id === id) ?? null;
}

export function createLocalHabit(payload: CreateHabitPayload, userId = getCurrentUserId()): Habit {
  const allHabits = readAllHabits();
  const now = getNowIso();
  const validationType = payload.validation_type ?? "foto";
  const targetDuration = payload.target_duration ?? null;
  const targetQuantity = payload.target_quantity ?? null;
  const targetUnit = payload.target_unit ?? null;
  const isTimeType = validationType === "tiempo" || validationType === "time";
  const habitType =
    isTimeType || targetDuration !== null
      ? "time"
      : targetQuantity !== null
      ? "quantity"
      : "boolean";
  const habit: Habit = {
    id: nextNegativeId(allHabits.map((existingHabit) => existingHabit.id)),
    user_id: userId,
    catalog_habit_id: payload.habito_id,
    name: payload.custom_name?.trim() || "Hábito Offline",
    custom_name: payload.custom_name?.trim() || null,
    description: payload.description?.trim() || null,
    custom_description: payload.description?.trim() || null,
    icon: "Flame",
    validation_type: validationType,
    habit_type: habitType,
    frequency: payload.frequency ?? "daily",
    section: "fire",
    target_duration: targetDuration,
    pomodoro_enabled: isTimeType,
    target_quantity: targetQuantity,
    target_unit: targetUnit,
    schedule_days: payload.frequency === "custom" ? payload.schedule_days ?? [] : [],
    created_at: now,
    updated_at: now,
  };

  writeAllHabits(allHabits.concat(habit));
  return habit;
}

export function upsertLocalHabit(habit: Habit, userId = getCurrentUserId()): Habit {
  const allHabits = readAllHabits();
  const normalizedHabit = { ...habit, user_id: habit.user_id ?? userId };
  const nextHabits = allHabits.filter(
    (existingHabit) => !(existingHabit.user_id === normalizedHabit.user_id && existingHabit.id === normalizedHabit.id),
  );
  nextHabits.push(normalizedHabit);
  writeAllHabits(nextHabits);
  return normalizedHabit;
}

export function updateLocalHabit(
  id: number,
  payload: UpdateHabitPayload,
  userId = getCurrentUserId(),
): Habit {
  const allHabits = readAllHabits();
  const index = allHabits.findIndex((habit) => habit.user_id === userId && habit.id === id);

  if (index === -1) {
    throw new Error("Habit not found in local storage.");
  }

  const updatedHabit: Habit = {
    ...allHabits[index],
    ...payload,
    name: payload.custom_name?.trim() ?? payload.name?.trim() ?? allHabits[index].name,
    custom_name: payload.custom_name ?? allHabits[index].custom_name ?? null,
    description: payload.description ?? allHabits[index].description ?? null,
    custom_description: payload.description ?? allHabits[index].custom_description ?? null,
    validation_type: payload.validation_type ?? allHabits[index].validation_type ?? "foto",
    frequency: payload.frequency ?? allHabits[index].frequency,
    schedule_days:
      payload.frequency === "custom"
        ? payload.schedule_days ?? allHabits[index].schedule_days ?? []
        : payload.frequency
        ? []
        : payload.schedule_days ?? allHabits[index].schedule_days ?? [],
    pomodoro_enabled: (() => {
      const vt = payload.validation_type ?? allHabits[index].validation_type ?? "foto";
      return vt === "tiempo" || vt === "time";
    })(),
    habit_type: (() => {
      const vt = payload.validation_type ?? allHabits[index].validation_type ?? "foto";
      const isTime = vt === "tiempo" || vt === "time";
      const dur = payload.target_duration ?? allHabits[index].target_duration;
      const qty = payload.target_quantity ?? allHabits[index].target_quantity;
      return isTime || dur !== null ? "time" : qty !== null ? "quantity" : "boolean";
    })(),
    updated_at: getNowIso(),
  };

  allHabits[index] = updatedHabit;
  writeAllHabits(allHabits);
  return updatedHabit;
}

export function deleteLocalHabit(id: number, userId = getCurrentUserId()): void {
  writeAllHabits(readAllHabits().filter((habit) => !(habit.user_id === userId && habit.id === id)));
  writeAllCheckins(
    readAllCheckins().filter((checkin) => !(checkin.user_id === userId && checkin.habit_id === id)),
  );
}

function syncTodayCheckins(todayHabits: TodayHabit[], userId = getCurrentUserId(), targetDate = getTodayIso()): void {
  const currentCheckins = readAllCheckins().filter((checkin) => !(checkin.user_id === userId && checkin.date === targetDate));
  const todayCheckins = todayHabits
    .filter((habit) => habit.checked_today)
    .map((habit) => ({ user_id: userId, habit_id: habit.id, date: targetDate }));

  writeAllCheckins(currentCheckins.concat(todayCheckins));
}

export function cacheTodayHabits(todayHabits: TodayHabit[], userId = getCurrentUserId()): TodayHabit[] {
  cacheHabits(todayHabits, userId);
  syncTodayCheckins(todayHabits, userId);
  return todayHabits;
}

export function getLocalTodayHabits(userId = getCurrentUserId(), targetDate = getTodayIso()): TodayHabit[] {
  const habits = getLocalHabits(userId).filter((habit) =>
    isLocalHabitEligibleOnDate(habit, targetDate, userId),
  );
  const checkedIds = new Set(
    readAllCheckins()
      .filter((checkin) => checkin.user_id === userId && checkin.date === targetDate)
      .map((checkin) => checkin.habit_id),
  );

  return habits.map((habit) => ({
    ...habit,
    checked_today: checkedIds.has(habit.id),
  }));
}

export function toggleLocalCheckin(
  habitId: number,
  userId = getCurrentUserId(),
  targetDate = getTodayIso(),
): CheckinToggleResult {
  const habit = getLocalHabitById(habitId, userId);
  if (!habit) {
    throw new Error("Habit not found.");
  }

  const allCheckins = readAllCheckins();
  const existingIndex = allCheckins.findIndex(
    (checkin) => checkin.user_id === userId && checkin.habit_id === habitId && checkin.date === targetDate,
  );

  if (existingIndex >= 0) {
    allCheckins.splice(existingIndex, 1);
    writeAllCheckins(allCheckins);
    return { checked: false, habit_id: habitId, date: targetDate };
  }

  allCheckins.push({ user_id: userId, habit_id: habitId, date: targetDate });
  writeAllCheckins(allCheckins);
  return { checked: true, habit_id: habitId, date: targetDate };
}

export function syncLocalCheckinResult(
  result: CheckinToggleResult,
  userId = getCurrentUserId(),
): CheckinToggleResult {
  const allCheckins = readAllCheckins().filter(
    (checkin) => !(checkin.user_id === userId && checkin.habit_id === result.habit_id && checkin.date === result.date),
  );

  if (result.checked) {
    allCheckins.push({
      user_id: userId,
      habit_id: result.habit_id,
      date: result.date,
    });
  }

  writeAllCheckins(allCheckins);
  return result;
}

function countEligibleCheckinsForDate(userId: number, date: string, habits: Habit[]): number {
  const eligibleIds = new Set(
    habits
      .filter((habit) => isLocalHabitEligibleOnDate(habit, date, userId))
      .map((habit) => habit.id),
  );
  return readAllCheckins().filter(
    (checkin) =>
      checkin.user_id === userId &&
      checkin.date === date &&
      eligibleIds.has(checkin.habit_id),
  ).length;
}

function getDateIso(daysAgo: number): string {
  const date = new Date();
  date.setDate(date.getDate() - daysAgo);
  return date.toISOString().slice(0, 10);
}

function getWeekBounds(dateIso: string): { start: string; end: string } {
  const date = new Date(`${dateIso}T00:00:00`);
  const mondayFirstDay = (date.getDay() + 6) % 7;
  const start = new Date(date);
  start.setDate(date.getDate() - mondayFirstDay);
  const end = new Date(start);
  end.setDate(start.getDate() + 6);

  return {
    start: start.toISOString().slice(0, 10),
    end: end.toISOString().slice(0, 10),
  };
}

function getMondayFirstWeekday(dateIso: string): number {
  return (new Date(`${dateIso}T00:00:00`).getDay() + 6) % 7;
}

function hasLocalCheckin(userId: number, habitId: number, date: string): boolean {
  return readAllCheckins().some(
    (checkin) => checkin.user_id === userId && checkin.habit_id === habitId && checkin.date === date,
  );
}

function hasLocalWeeklyCheckin(userId: number, habitId: number, date: string): boolean {
  const { start, end } = getWeekBounds(date);
  return readAllCheckins().some(
    (checkin) =>
      checkin.user_id === userId &&
      checkin.habit_id === habitId &&
      checkin.date >= start &&
      checkin.date <= end,
  );
}

function isLocalHabitEligibleOnDate(habit: Habit, targetDate: string, userId: number): boolean {
  if (habit.frequency === "daily") {
    return true;
  }

  if (habit.frequency === "weekly") {
    return !hasLocalWeeklyCheckin(userId, habit.id, targetDate) || hasLocalCheckin(userId, habit.id, targetDate);
  }

  if (habit.frequency === "custom") {
    const scheduleDays = habit.schedule_days ?? [];
    if (scheduleDays.length === 0) {
      return false;
    }
    return scheduleDays.includes(getMondayFirstWeekday(targetDate));
  }

  return false;
}

export function getLocalStats(userId = getCurrentUserId()): StatsSummary {
  const habits = getLocalHabits(userId);
  const today = getTodayIso();
  const todayTotal = habits.filter((habit) =>
    isLocalHabitEligibleOnDate(habit, today, userId),
  ).length;
  const todayCompleted = Math.min(
    countEligibleCheckinsForDate(userId, today, habits),
    todayTotal,
  );

  let weeklyCheckins = 0;
  let weeklyOpportunities = 0;
  for (let daysAgo = 0; daysAgo < 7; daysAgo += 1) {
    const date = getDateIso(daysAgo);
    weeklyCheckins += countEligibleCheckinsForDate(userId, date, habits);
    weeklyOpportunities += habits.filter((habit) =>
      isLocalHabitEligibleOnDate(habit, date, userId),
    ).length;
  }

  const completionRate = weeklyOpportunities > 0 ? Math.round((weeklyCheckins / weeklyOpportunities) * 100) : 0;

  let streak = 0;
  let cursor = 0;
  let skippedTodayWithoutCheckins = false;

  while (true) {
    const date = getDateIso(cursor);
    const checkins = countEligibleCheckinsForDate(userId, date, habits);

    if (checkins > 0) {
      streak += 1;
      cursor += 1;
      continue;
    }

    if (cursor === 0 && !skippedTodayWithoutCheckins) {
      skippedTodayWithoutCheckins = true;
      cursor += 1;
      continue;
    }

    break;
  }

  return {
    streak,
    today_completed: todayCompleted,
    today_total: todayTotal,
    completion_rate: completionRate,
    total_xp: 0,
    level: 1,
    validations_today: 0,
  };
}

export function cachePomodoroSessions(
  sessions: PomodoroSession[],
  userId = getCurrentUserId(),
): PomodoroSession[] {
  if (userId <= 0) {
    return sessions;
  }

  const normalizedSessions = sessions.map((session) => ({
    ...session,
    user_id: session.user_id ?? userId,
  }));

  const allSessions = readAllPomodoroSessions();
  writeAllPomodoroSessions(replaceUserRecords(allSessions, userId, normalizedSessions));
  return normalizedSessions;
}

export function getLocalPomodoroSessions(userId = getCurrentUserId(), limit = 10): PomodoroSession[] {
  return readAllPomodoroSessions()
    .filter((session) => session.user_id === userId)
    .sort((left, right) => (right.started_at ?? "").localeCompare(left.started_at ?? ""))
    .slice(0, limit);
}

export function createLocalPomodoroSession(
  payload: CreatePomodoroSessionPayload,
  userId = getCurrentUserId(),
): PomodoroSession {
  const allSessions = readAllPomodoroSessions();
  const session: PomodoroSession = {
    id: nextNegativeId(allSessions.map((existingSession) => existingSession.id)),
    user_id: userId,
    habit_id: payload.habit_id ?? null,
    theme: payload.theme ?? "fire",
    study_minutes: payload.study_minutes ?? 25,
    break_minutes: payload.break_minutes ?? 5,
    cycles: payload.cycles ?? 4,
    completed: false,
    interruption_count: 0,
    bonus_xp_awarded: null,
    started_at: getNowIso(),
    completed_at: null,
  };

  writeAllPomodoroSessions(allSessions.concat(session));
  return session;
}

export function upsertLocalPomodoroSession(session: PomodoroSession): PomodoroSession {
  const allSessions = readAllPomodoroSessions();
  const nextSessions = allSessions.filter(
    (existingSession) => !(existingSession.user_id === session.user_id && existingSession.id === session.id),
  );
  nextSessions.push(session);
  writeAllPomodoroSessions(nextSessions);
  return session;
}

export function completeLocalPomodoroSession(
  sessionId: number,
  userId = getCurrentUserId(),
): PomodoroSession {
  const allSessions = readAllPomodoroSessions();
  const index = allSessions.findIndex(
    (session) => session.user_id === userId && session.id === sessionId,
  );

  if (index === -1) {
    throw new Error("Session not found.");
  }

  const completedSession: PomodoroSession = {
    ...allSessions[index],
    completed: true,
    completed_at: getNowIso(),
  };

  allSessions[index] = completedSession;
  writeAllPomodoroSessions(allSessions);
  return completedSession;
}
