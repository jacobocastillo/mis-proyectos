export type HabitHistorySource = "completion" | "validation";
export type HabitHistoryStatus = "completed" | "approved" | "rejected" | "pending";

export interface HabitHistoryEvent {
  id: string;
  source: HabitHistorySource;
  habit_id: number;
  catalog_habit_id: number | null;
  habit_name: string | null;
  category_id: number | null;
  category_name: string | null;
  event_date: string | null;
  occurred_at: string;
  status: HabitHistoryStatus;
  validation_type: string | null;
  xp_awarded: number;
  validation_id: number | null;
  checkin_id: number | null;
  reason: string | null;
  confidence: number | null;
}

export interface HabitHistoryResponse {
  items: HabitHistoryEvent[];
  next_cursor: string | null;
}

export interface HabitHistoryFilters {
  from?: string;
  to?: string;
  habit_id?: number;
  status?: HabitHistoryStatus;
  limit?: number;
  cursor?: string;
}
