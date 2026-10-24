import { api, enc, request } from "./client";
import type { Context, IngestionAccepted, IngestionRun, Model, Page, PipelineAccepted, PipelineRun, Profile } from "./types";

export interface UploadFields {
  file: File;
  name: string;
  dataset_version: string;
  source: string;
  schema_version: string;
  adapter: string;
  adapter_config?: string;
}

export const pipelineService = {
  context: (signal?: AbortSignal) => api.get<Context>("/context", undefined, signal),
  upload: (f: UploadFields) => {
    const form = new FormData();
    // browsers label .csv inconsistently (e.g. application/vnd.ms-excel); the server accepts text/csv only
    form.set("file", f.file.type === "text/csv" ? f.file : new File([f.file], f.file.name, { type: "text/csv" }));
    form.set("name", f.name);
    form.set("dataset_version", f.dataset_version);
    form.set("source", f.source);
    form.set("schema_version", f.schema_version);
    form.set("adapter", f.adapter);
    form.set("adapter_config", f.adapter_config ?? "{}");
    return request<IngestionAccepted>("POST", "/ingestion", { form });
  },
  ingestions: (page = 1, signal?: AbortSignal) => api.get<Page<IngestionRun>>("/ingestion", { page }, signal),
  ingestion: (id: string, signal?: AbortSignal) => api.get<IngestionRun>(`/ingestion/${enc(id)}`, undefined, signal),
  profile: (datasetId: string, signal?: AbortSignal) => api.get<Profile>(`/datasets/${enc(datasetId)}/profile`, undefined, signal),
  runs: (q: { dataset_id?: string; state?: string; page?: number }, signal?: AbortSignal) =>
    api.get<Page<PipelineRun>>("/pipeline-runs", { ...q }, signal),
  run: (id: string, signal?: AbortSignal) => api.get<PipelineRun>(`/pipeline-runs/${enc(id)}`, undefined, signal),
  start: (datasetId: string) => api.post<PipelineAccepted>("/pipeline-runs", { dataset_id: datasetId }),
  retry: (id: string) => api.post<PipelineAccepted>(`/pipeline-runs/${enc(id)}/retry`),
  models: (page = 1, signal?: AbortSignal) => api.get<Page<Model>>("/models", { page }, signal),
  model: (version: string, signal?: AbortSignal) => api.get<Model>(`/models/${enc(version)}`, undefined, signal),
};
