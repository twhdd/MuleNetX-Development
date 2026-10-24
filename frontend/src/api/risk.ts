import { api, enc } from "./client";
import type { Assessment, Page, Propagation, Shap } from "./types";

export const riskService = {
  risk: (id: string, signal?: AbortSignal) => api.get<Assessment>(`/accounts/${enc(id)}/risk`, undefined, signal),
  history: (id: string, page = 1, signal?: AbortSignal) =>
    api.get<Page<Assessment>>(`/accounts/${enc(id)}/risk/history`, { page }, signal),
  propagation: (id: string, signal?: AbortSignal) =>
    api.get<Propagation>(`/accounts/${enc(id)}/risk/propagation`, undefined, signal),
  shap: (id: string, topN = 10, signal?: AbortSignal) =>
    api.get<Shap>(`/accounts/${enc(id)}/shap`, { top_n: topN }, signal),
};
