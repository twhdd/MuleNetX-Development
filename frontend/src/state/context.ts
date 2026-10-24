/** Active analytical context (SRS §6.9), polled from `/context`. */
import { create } from "zustand";
import { pipelineService } from "../api/pipeline";
import type { Context } from "../api/types";

export const CONTEXT_POLL_MS = 30_000;

interface ContextState {
  context: Context | null;
  error: string | null;
  loadedAt: number | null;
  refresh: () => Promise<void>;
  reset: () => void;
}

export const useActiveContext = create<ContextState>((set) => ({
  context: null,
  error: null,
  loadedAt: null,
  refresh: async () => {
    try {
      const context = await pipelineService.context();
      set({ context, error: null, loadedAt: Date.now() });
    } catch (err) {
      set({ error: (err as Error).message });
    }
  },
  reset: () => set({ context: null, error: null, loadedAt: null }),
}));
