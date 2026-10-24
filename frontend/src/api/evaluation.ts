import { api, enc } from "./client";
import type { EvaluationRun, EvaluationSummary, Page } from "./types";

export const evaluationService = {
  start: () => api.post<{ evaluation_run_id: string; status: string }>("/evaluation/runs", {}),
  list: (page = 1, signal?: AbortSignal) => api.get<Page<EvaluationRun>>("/evaluation/runs", { page }, signal),
  get: (id: string, signal?: AbortSignal) => api.get<EvaluationSummary>(`/evaluation/runs/${enc(id)}`, undefined, signal),
};
