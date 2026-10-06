import { apiGet, API_ENDPOINTS, shouldUseOfflineFallback } from "@/services/api/client";
import { fetchHabits } from "@/services/habits/habitService";
import { getLocalStats } from "@/services/storage/localData";
import type { ProfileStats, StatsSummary, XpInfo, DetailedStats } from "@/types/stats";

export async function fetchStatsSummary(): Promise<StatsSummary> {
  try {
    return await apiGet<StatsSummary>(API_ENDPOINTS.stats.summary);
  } catch (error) {
    // Connected mode must not invent stats that disagree with the backend.
    if (shouldUseOfflineFallback(error)) {
      return getLocalStats();
    }
    throw error;
  }
}

export async function fetchXpInfo(): Promise<XpInfo> {
  return apiGet<XpInfo>(API_ENDPOINTS.stats.xp);
}

export async function fetchDetailedStats(): Promise<DetailedStats> {
  return apiGet<DetailedStats>(API_ENDPOINTS.stats.detailed);
}

export async function fetchProfileStats(): Promise<ProfileStats> {
  const [summary, habits] = await Promise.all([fetchStatsSummary(), fetchHabitsCount()]);

  return {
    ...summary,
    habits_count: habits,
  };
}

async function fetchHabitsCount(): Promise<number> {
  return (await fetchHabits()).length;
}
