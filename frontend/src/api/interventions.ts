import { api, enc } from "./client";
import type { InterventionCandidatePage, Page, Scenario, ScenarioAccepted, ScenarioPage } from "./types";

export type OperationType = "ACCOUNT_REMOVAL" | "INTERMEDIARY_REMOVAL" | "ACCOUNT_SET_REMOVAL" | "EDGE_REMOVAL";

export interface SimulateRequest {
  mode: "RANK" | "EVALUATE";
  intervention_type?: OperationType;
  target_ids?: string[];
}

/** Simulation only (SRS §16A.1): nothing here can block, freeze or change a real account or payment. */
export const interventionService = {
  simulate: (ringId: string, body: SimulateRequest) => api.post<ScenarioAccepted>(`/rings/${enc(ringId)}/interventions/simulate`, body),
  ofRing: (ringId: string, page = 1, signal?: AbortSignal) => api.get<ScenarioPage>(`/rings/${enc(ringId)}/interventions`, { page }, signal),
  get: (scenarioId: string, signal?: AbortSignal) => api.get<Scenario>(`/interventions/${enc(scenarioId)}`, undefined, signal),
  candidates: (scenarioId: string, page = 1, signal?: AbortSignal) =>
    api.get<InterventionCandidatePage>(`/interventions/${enc(scenarioId)}/candidates`, { page }, signal),
};

export type { Page };
