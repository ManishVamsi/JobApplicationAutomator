import { create } from 'zustand';

interface AuthState {
  accessToken: string | null;
  user: {
    id: string;
    email: string;
    name: string | null;
    target_roles: string[];
    target_locations: string[];
    work_auth_status: string | null;
  } | null;
  isAuthenticated: boolean;
  setAccessToken: (token: string) => void;
  setUser: (user: AuthState['user']) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  accessToken: null,
  user: null,
  isAuthenticated: false,

  setAccessToken: (token: string) =>
    set({ accessToken: token, isAuthenticated: true }),

  setUser: (user) => set({ user }),

  logout: () =>
    set({ accessToken: null, user: null, isAuthenticated: false }),
}));
