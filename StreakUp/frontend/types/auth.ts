export interface AuthUser {
  id: number;
  username: string;
  email: string;
  role: string;
  created_at?: string;
}

export interface AuthSession {
  accessToken: string;
  refreshToken?: string;
  user: AuthUser;
}
