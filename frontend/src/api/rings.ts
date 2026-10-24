import { api, enc } from "./client";
import type { MotifPage, Ring, RingEvidence, RingFeatures, RingMemberPage, RingPage, RingRisk, RingTransactionPage } from "./types";

export type RingStatus = "CANDIDATE" | "REVIEWED" | "DISMISSED";
export type RingClass = "SUSPICIOUS_COMMUNITY" | "POTENTIAL_FRAUD_RING_CANDIDATE";

export interface MotifQuery {
  type?: string;
  start?: string;
  end?: string;
  page?: number;
}

export const ringService = {
  list: (q: { class?: string; status?: string; min_score?: string; page?: number }, signal?: AbortSignal) =>
    api.get<RingPage>("/rings", { ...q }, signal),
  get: (id: string, signal?: AbortSignal) => api.get<Ring>(`/rings/${enc(id)}`, undefined, signal),
  setStatus: (id: string, status: RingStatus) => api.patch<Ring>(`/rings/${enc(id)}/status`, { status }),
  accounts: (id: string, page = 1, signal?: AbortSignal) => api.get<RingMemberPage>(`/rings/${enc(id)}/accounts`, { page }, signal),
  transactions: (id: string, cursor?: string, signal?: AbortSignal) =>
    api.get<RingTransactionPage>(`/rings/${enc(id)}/transactions`, { page_size: 50, cursor }, signal),
  features: (id: string, signal?: AbortSignal) => api.get<RingFeatures>(`/rings/${enc(id)}/features`, undefined, signal),
  risk: (id: string, signal?: AbortSignal) => api.get<RingRisk>(`/rings/${enc(id)}/risk`, undefined, signal),
  evidence: (id: string, section: string, page = 1, signal?: AbortSignal) =>
    api.get<RingEvidence>(`/rings/${enc(id)}/evidence`, { section, page }, signal),
  motifs: (id: string, q: MotifQuery, signal?: AbortSignal) => api.get<MotifPage>(`/rings/${enc(id)}/motifs`, { ...q }, signal),
};

export const motifService = {
  ofAccount: (accountId: string, q: MotifQuery, signal?: AbortSignal) =>
    api.get<MotifPage>(`/accounts/${enc(accountId)}/motifs`, { ...q }, signal),
};
