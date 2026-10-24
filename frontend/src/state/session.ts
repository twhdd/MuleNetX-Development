/** Session store. The token lives in memory only (SRS §20.2): a reload requires login. */
import { create } from "zustand";
import type { Role } from "../api/types";

export interface SessionUser {
  user_id: string;
  username: string;
  role: Role;
}

interface SessionState {
  token: string | null;
  user: SessionUser | null;
  expiresAt: number | null;
  /** Set when the server rejected the token, so the login screen can say why. */
  expired: boolean;
  signIn: (token: string, user: SessionUser, expiresIn: number) => void;
  signOut: () => void;
  expire: () => void;
}

export const useSession = create<SessionState>((set) => ({
  token: null,
  user: null,
  expiresAt: null,
  expired: false,
  signIn: (token, user, expiresIn) => set({ token, user, expiresAt: Date.now() + expiresIn * 1000, expired: false }),
  signOut: () => set({ token: null, user: null, expiresAt: null, expired: false }),
  expire: () => set({ token: null, user: null, expiresAt: null, expired: true }),
}));

export function hasRole(role: Role | undefined, ...allowed: Role[]): boolean {
  return role !== undefined && allowed.includes(role);
}
