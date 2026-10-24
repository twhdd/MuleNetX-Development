import { api, enc } from "./client";
import type { Case, CaseStatus, Finding, Page, Priority, Subject } from "./types";

export type SubjectType = "ACCOUNT" | "TRANSACTION" | "RING" | "SCENARIO";

export interface CasePatch {
  version: number;
  status?: CaseStatus;
  title?: string;
  priority?: Priority;
  assigned_to?: string | null;
}

export interface EvidenceRef {
  type: "account" | "transaction" | "ring" | "community" | "path";
  id: string;
  graph_snapshot_id?: string;
  accounts?: string[];
}

export const caseService = {
  list: (q: { status?: string; assigned_to?: string; page?: number }, signal?: AbortSignal) =>
    api.get<Page<Case>>("/cases", { ...q }, signal),
  create: (body: { title: string; priority: Priority; assigned_to?: string }) => api.post<Case>("/cases", body),
  get: (id: string, signal?: AbortSignal) => api.get<Case>(`/cases/${enc(id)}`, undefined, signal),
  patch: (id: string, body: CasePatch) => api.patch<Case>(`/cases/${enc(id)}`, body),
  subjects: (id: string, page = 1, signal?: AbortSignal) => api.get<Page<Subject>>(`/cases/${enc(id)}/subjects`, { page }, signal),
  addSubject: (id: string, subject_type: SubjectType, subject_id: string) =>
    api.post<Subject>(`/cases/${enc(id)}/subjects`, { subject_type, subject_id }),
  removeSubject: (id: string, type: SubjectType, subjectId: string) =>
    api.del(`/cases/${enc(id)}/subjects/${enc(type)}/${enc(subjectId)}`),
  findings: (id: string, page = 1, signal?: AbortSignal) => api.get<Page<Finding>>(`/cases/${enc(id)}/findings`, { page }, signal),
  addFinding: (id: string, body: { type: string; description: string; evidence: EvidenceRef[]; source: string }) =>
    api.post<Finding>(`/cases/${enc(id)}/findings`, body),
};
