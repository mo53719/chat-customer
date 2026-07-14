import { create } from "zustand";

interface PageState {
  currentSessionId: string | null;
  selectedDocId: string | null;
  selectedAgentName: string | null;
  setSession: (id: string | null) => void;
  setDoc: (id: string | null) => void;
  setAgent: (name: string | null) => void;
}

export const usePageStore = create<PageState>((set) => ({
  currentSessionId: null,
  selectedDocId: null,
  selectedAgentName: null,
  setSession: (id) => set({ currentSessionId: id }),
  setDoc: (id) => set({ selectedDocId: id }),
  setAgent: (name) => set({ selectedAgentName: name }),
}));