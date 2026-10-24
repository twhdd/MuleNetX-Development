import { api, enc } from "./client";
import type { AccountCommunity, CommunityDetail, CommunityPage, GraphMetrics, Neighborhood, PathDetail, PathQuery } from "./types";

export interface NeighborhoodQuery {
  account_id: string;
  depth?: number;
  max_nodes?: number;
  max_edges?: number;
  graph_snapshot_id?: string;
}

export interface PathRequest {
  source_account_id: string;
  destination_account_id: string;
  mode?: "SHORTEST" | "ALL";
  max_depth?: number;
  max_results?: number;
}

export const graphService = {
  neighborhood: (q: NeighborhoodQuery, signal?: AbortSignal) => api.get<Neighborhood>("/graph/neighborhood", { ...q }, signal),
  metrics: (accountId: string, signal?: AbortSignal) => api.get<GraphMetrics>("/graph/metrics", { account_id: accountId }, signal),
  path: (q: PathRequest, signal?: AbortSignal) => api.get<PathQuery>("/graph/path", { ...q }, signal),
  pathById: (pathId: string, snapshotId: string, accounts: string[], page = 1, signal?: AbortSignal) =>
    api.get<PathDetail>(`/graph/paths/${enc(pathId)}`, { graph_snapshot_id: snapshotId, accounts: accounts.join(","), page }, signal),
};

export const communityService = {
  list: (page = 1, signal?: AbortSignal) => api.get<CommunityPage>("/communities", { page }, signal),
  get: (id: string, page = 1, signal?: AbortSignal) => api.get<CommunityDetail>(`/communities/${enc(id)}`, { page }, signal),
  ofAccount: (accountId: string, page = 1, signal?: AbortSignal) =>
    api.get<AccountCommunity>(`/accounts/${enc(accountId)}/community`, { page }, signal),
};
