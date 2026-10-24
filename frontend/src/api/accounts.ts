import { api, enc } from "./client";
import type { Account, Features, Page, Temporal, TransactionPage } from "./types";

export interface AccountSearch {
  q?: string;
  risk_tier?: string;
  account_type?: string;
  sort?: "risk_score" | "account_id" | "source_account_ref" | "risk_tier";
  order?: "asc" | "desc";
  page?: number;
  page_size?: number;
}

export interface TransactionQuery {
  start?: string;
  end?: string;
  type?: string;
  direction?: "in" | "out";
  page_size?: number;
  cursor?: string;
}

export const accountService = {
  search: (q: AccountSearch, signal?: AbortSignal) => api.get<Page<Account>>("/accounts", { ...q }, signal),
  get: (id: string, signal?: AbortSignal) => api.get<Account>(`/accounts/${enc(id)}`, undefined, signal),
  transactions: (id: string, q: TransactionQuery, signal?: AbortSignal) =>
    api.get<TransactionPage>(`/accounts/${enc(id)}/transactions`, { ...q }, signal),
  features: (id: string, signal?: AbortSignal) => api.get<Features>(`/accounts/${enc(id)}/features`, undefined, signal),
  temporal: (id: string, signal?: AbortSignal) => api.get<Temporal>(`/accounts/${enc(id)}/temporal`, undefined, signal),
};
