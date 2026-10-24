import { api, enc } from "./client";
import type { AuditEvent, Page, Role, User } from "./types";

export interface AuditQuery {
  user_id?: string;
  action?: string;
  resource_type?: string;
  resource_id?: string;
  outcome?: string;
  start?: string;
  end?: string;
  page?: number;
}

export const userService = {
  list: (page = 1, signal?: AbortSignal) => api.get<Page<User>>("/users", { page }, signal),
  create: (body: { username: string; role: Role; password: string }) => api.post<User>("/users", body),
  update: (id: string, body: { role?: Role; is_active?: boolean; password?: string }) => api.patch<User>(`/users/${enc(id)}`, body),
};

export const auditService = {
  list: (q: AuditQuery, signal?: AbortSignal) => api.get<Page<AuditEvent>>("/audit", { ...q }, signal),
};
