import { api, request } from "./client";
import type { LoginResponse, User } from "./types";

export const authService = {
  login: (username: string, password: string) =>
    request<LoginResponse>("POST", "/auth/login", { body: { username, password }, anonymous: true }),
  logout: () => api.post<void>("/auth/logout"),
  me: () => api.get<User>("/auth/me"),
};
