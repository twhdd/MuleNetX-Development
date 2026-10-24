/** Cross-page UI state: the account selected in triage and the explorer's last focus. */
import { create } from "zustand";

interface UiState {
  triageAccount: string | null;
  explorerAccount: string | null;
  selectTriage: (id: string | null) => void;
  focusExplorer: (id: string | null) => void;
}

export const useUi = create<UiState>((set) => ({
  triageAccount: null,
  explorerAccount: null,
  selectTriage: (triageAccount) => set({ triageAccount }),
  focusExplorer: (explorerAccount) => set({ explorerAccount }),
}));
