export interface SharedStreak {
  current: number;
  today_completed_members: number;
  required_members: number;
  ready: boolean;
}

export interface SharedStreakMember {
  user_id: number;
  username: string;
  status: "active" | "left" | "lost" | "winner";
  share_progress: boolean;
  joined_at: string | null;
  lost_at: string | null;
  today_completed: boolean;
  completed_days: number;
}

export interface SharedStreakGroup {
  id: number;
  name: string;
  invite_code: string;
  owner_user_id: number;
  habit_id: number | null;
  habit_name: string | null;
  max_participants: number;
  member_count: number;
  start_date: string | null;
  duration_days: number | null;
  end_date: string | null;
  group_status: "active" | "finished";
  winner_user_id: number | null;
  shared_streak: SharedStreak;
  created_at: string | null;
  members?: SharedStreakMember[];
}

export interface CreateSharedGroupPayload {
  name: string;
  user_habit_id: number;
  duration_days?: number | null;
}

export interface JoinSharedGroupPayload {
  invite_code: string;
}
