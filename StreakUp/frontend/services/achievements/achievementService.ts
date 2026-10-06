/**
 * achievementService
 *
 * Fetches achievement data from the backend for the authenticated user.
 */

import { apiGet, API_ENDPOINTS } from "@/services/api/client";

/** A single achievement entry as returned by GET /api/achievements */
export interface AchievementItem {
  id: number;
  key: string;
  name: string;
  description: string | null;
  emoji: string;
  xp_bonus: number;
  /** true when the authenticated user has earned this achievement */
  earned: boolean;
  /** ISO datetime string, only present for earned achievements */
  earned_at?: string | null;
}

/**
 * Fetches all catalog achievements with their earned status for
 * the current user.
 */
export async function fetchAchievements(): Promise<AchievementItem[]> {
  return apiGet<AchievementItem[]>(API_ENDPOINTS.achievements.list);
}
