import { api } from "./client";
import type { CopilotResponse } from "./types";

export interface CopilotScope {
  account_id?: string;
  case_id?: string;
  ring_id?: string;
}

export const copilotService = {
  query: (question: string, scope: CopilotScope) => api.post<CopilotResponse>("/copilot/query", { question, ...scope }),
};
