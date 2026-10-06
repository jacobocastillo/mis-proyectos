export interface StatsSummary {
  streak: number;
  today_completed: number;
  today_total: number;
  completion_rate: number;
  total_xp: number;
  level: number;
  validations_today: number;
  feedback?: {
    message: string;
    tone: string;
    context?: Record<string, unknown>;
  };
}

export interface ProfileStats extends StatsSummary {
  habits_count: number;
}

export interface XpInfo {
  total_xp: number;
  level: number;
  xp_in_level: number;
  xp_for_next_level: number;
  progress_pct: number;
}

export interface DetailedStats {
  summary: {
    streak: number;
    completion_rate: number;
    total_completed: number;
    total_habits: number;
    total_xp: number;
    level: number;
  };
  weekly_history: {
    date: string;
    label: string;
    completed: number;
    total: number;
  }[];
  per_habit: {
    id: number;
    name: string;
    icon: string;
    completed: number;
    total: number;
    rate: number;
  }[];
  calendar: {
    date: string;
    count: number;
    intensity: number;
  }[];
  records: {
    longest_streak: number;
    best_day: number;
    current_streak: number;
    active_days: number;
  };
  validations: {
    total_successful: number;
    total_attempts: number;
    success_rate: number;
  };
}
