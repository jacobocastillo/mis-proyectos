export const API_ENDPOINTS = {
  auth: {
    login: "/api/auth/login",
    register: "/api/auth/register",
    refresh: "/api/auth/refresh",
    logout: "/api/auth/logout",
  },
  user: {
    /** Get the authenticated user's profile */
    me: "/api/users/me",
    /** Update editable profile fields for the authenticated user */
    update: "/api/users/me",
    /** Permanently delete the authenticated user's account */
    delete: "/api/users/me",
    /** Export the authenticated user's portable data */
    export: "/api/users/me/export",
  },
  telemetry: {
    errors: "/api/telemetry/errors",
  },
  habits: {
    list: "/api/habits",
    create: "/api/habits",
    catalog: "/api/habits/catalog",
    validate: "/api/validate",
    detail: (id: number) => `/api/habits/${id}`,
    update: (id: number) => `/api/habits/${id}`,
    delete: (id: number) => `/api/habits/${id}`,
  },
  checkins: {
    toggle: "/api/checkins/toggle",
    today: "/api/checkins/today",
    history: "/api/checkins/history",
  },
  sync: {
    push: "/api/sync",
  },
  stats: {
    summary: "/api/stats/summary",
    xp: "/api/stats/xp",
    detailed: "/api/stats/detailed",
  },
  pomodoro: {
    sessions: "/api/pomodoro/sessions",
    complete: (id: number) => `/api/pomodoro/sessions/${id}/complete`,
    interrupt: (id: number) => `/api/pomodoro/sessions/${id}/interrupt`,
  },
  achievements: {
    /** List all achievements for the authenticated user */
    list: "/api/achievements",
  },
  social: {
    groups: "/api/social/groups",
    join: "/api/social/groups/join",
    detail: (id: number) => `/api/social/groups/${id}`,
    membership: (id: number) => `/api/social/groups/${id}/membership`,
  },
} as const;
