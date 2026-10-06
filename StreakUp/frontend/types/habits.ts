export type HabitDifficulty = "facil" | "media" | "dificil";
export type ValidationType = "foto" | "texto" | "tiempo" | "photo" | "text_ai" | "time" | "check";
export type HabitMetaType = "boolean" | "quantity_liters" | "minutes";
export type HabitFrequency = "daily" | "weekly" | "custom";

export interface Habit {
  id: number;
  user_id: number;
  catalog_habit_id?: number | null;
  category_id?: number | null;
  category_name?: string | null;
  name: string;
  custom_name?: string | null;
  description?: string | null;
  custom_description?: string | null;
  difficulty?: HabitDifficulty | null;
  xp_base?: number | null;
  meta_type?: HabitMetaType | string | null;
  xp_rate?: number | null;
  max_xp_per_day?: number | null;
  active?: boolean;
  start_date?: string | null;
  end_date?: string | null;
  icon: string;
  validation_type?: ValidationType;
  habit_type: "boolean" | "time" | "quantity";
  frequency: HabitFrequency;
  section: "fire" | "plant" | "moon";
  target_duration: number | null;
  pomodoro_enabled: boolean;
  target_quantity: number | null;
  target_unit: string | null;
  deadline_time?: string | null;
  min_text_length?: number | null;
  schedule_days?: number[];
  created_at: string;
  updated_at: string;
}

export interface HabitCatalogItem {
  id: number;
  category_id: number;
  name: string;
  description: string | null;
  difficulty: HabitDifficulty;
  xp_base: number;
  meta_type: HabitMetaType | string;
  xp_rate: number;
  max_xp_per_day: number;
  active: boolean;
  validation_type: ValidationType;
  frequency: HabitFrequency;
  target_quantity: number | null;
  target_unit: string | null;
  target_duration: number | null;
}

export interface CreateHabitPayload {
  habito_id: number;
  custom_name?: string | null;
  description?: string | null;
  validation_type?: ValidationType | null;
  frequency?: HabitFrequency | null;
  target_duration?: number | null;
  target_quantity?: number | null;
  target_unit?: string | null;
  deadline_time?: string | null;
  min_text_length?: number | null;
  schedule_days?: number[];
}

export interface UpdateHabitPayload {
  name?: string | null;
  custom_name?: string | null;
  description?: string | null;
  custom_description?: string | null;
  validation_type?: ValidationType | null;
  icon?: string;
  section?: "fire" | "plant" | "moon";
  habit_type?: "boolean" | "time" | "quantity";
  frequency?: HabitFrequency | null;
  target_duration?: number | null;
  target_quantity?: number | null;
  target_unit?: string | null;
  deadline_time?: string | null;
  pomodoro_enabled?: boolean;
  min_text_length?: number | null;
  schedule_days?: number[];
}

export const SECTION_LABELS: Record<string, string> = {
  fire: "BIENESTAR",
  plant: "APRENDIZAJE",
  moon: "SALUD",
};

export const SECTION_ICONS: Record<string, string> = {
  fire: "Flame",
  plant: "Sprout",
  moon: "Moon",
};

export const FREQUENCY_LABELS: Record<HabitFrequency, string> = {
  daily: "Diaria",
  weekly: "Semanal",
  custom: "Personalizada",
};

export const WEEKDAY_LABELS: Record<number, string> = {
  0: "L",
  1: "M",
  2: "X",
  3: "J",
  4: "V",
  5: "S",
  6: "D",
};

export function getHabitFrequencyLabel(
  frequencyOrHabit: HabitFrequency | Pick<Habit, "frequency" | "schedule_days">,
  scheduleDays?: number[],
): string {
  const frequency =
    typeof frequencyOrHabit === "string" ? frequencyOrHabit : frequencyOrHabit.frequency;
  const days =
    typeof frequencyOrHabit === "string" ? scheduleDays : frequencyOrHabit.schedule_days;

  if (frequency !== "custom") {
    return FREQUENCY_LABELS[frequency];
  }

  const labels = (days ?? [])
    .filter((day) => day in WEEKDAY_LABELS)
    .sort((left, right) => left - right)
    .map((day) => WEEKDAY_LABELS[day]);

  return labels.length > 0
    ? `${FREQUENCY_LABELS.custom}: ${labels.join(", ")}`
    : FREQUENCY_LABELS.custom;
}

export const VALIDATION_TYPE_LABELS: Record<ValidationType, string> = {
  foto: "Foto",
  texto: "Texto",
  tiempo: "Tiempo",
  photo: "Foto",
  text_ai: "Texto IA",
  time: "Tiempo",
  check: "Check",
};

export function getHabitTargetSummary(habit: Pick<Habit, "target_duration" | "target_quantity" | "target_unit">): string | null {
  if (habit.target_duration !== null) {
    return `${habit.target_duration} min`;
  }
  if (habit.target_quantity !== null) {
    return habit.target_unit
      ? `${habit.target_quantity} ${habit.target_unit}`
      : `${habit.target_quantity}`;
  }
  return null;
}

export interface MotivationFeedback {
  message: string;
  tone: string;
  context?: Record<string, unknown>;
}

export interface DifficultyRecommendation {
  level: HabitDifficulty;
  confidence: number;
  explanation: string;
  source: "deterministic" | "openai" | string;
  advisory: boolean;
}

export interface ValidationResult {
  status?: string;
  valido: boolean;
  razon: string;
  confianza: number;
  xp_ganado?: number;
  nueva_racha?: number;
  new_achievements?: Array<Record<string, unknown>>;
  difficulty_recommendation?: DifficultyRecommendation;
  feedback?: MotivationFeedback;
}
