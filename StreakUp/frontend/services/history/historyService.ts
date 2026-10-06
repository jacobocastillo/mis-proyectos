import { apiGet, API_ENDPOINTS } from "@/services/api/client";
import type { HabitHistoryFilters, HabitHistoryResponse } from "@/types/history";

function buildQuery(filters: HabitHistoryFilters = {}): string {
  const params = new URLSearchParams();

  Object.entries(filters).forEach(([key, value]) => {
    if (value === undefined || value === null || value === "") {
      return;
    }
    params.set(key, String(value));
  });

  const query = params.toString();
  return query ? `?${query}` : "";
}

export async function fetchHabitHistory(
  filters: HabitHistoryFilters = {},
): Promise<HabitHistoryResponse> {
  return apiGet<HabitHistoryResponse>(`${API_ENDPOINTS.checkins.history}${buildQuery(filters)}`);
}
