import { create } from "zustand";
import { persist } from "zustand/middleware";

interface AuthState {
  token: string | null;
  username: string | null;
  role: string | null;
  userId: number | null;
  setAuth: (t: string, u: string, r: string, uid: number) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      username: null,
      role: null,
      userId: null,
      setAuth: (t, u, r, uid) => set({ token: t, username: u, role: r, userId: uid }),
      logout: () => set({ token: null, username: null, role: null, userId: null }),
    }),
    { name: "auth-store" }
  )
);

// 聊天页状态持久化：弹窗/侧边面板关闭后输入框与生成内容不清空
interface ChatDraftState {
  input: string;
  sessionId: string | null;
  lastAnswer: string;
  setInput: (s: string) => void;
  setSessionId: (s: string | null) => void;
  setLastAnswer: (s: string) => void;
  clear: () => void;
}

export const useChatDraftStore = create<ChatDraftState>()(
  persist(
    (set) => ({
      input: "",
      sessionId: null,
      lastAnswer: "",
      setInput: (s) => set({ input: s }),
      setSessionId: (s) => set({ sessionId: s }),
      setLastAnswer: (s) => set({ lastAnswer: s }),
      clear: () => set({ input: "", lastAnswer: "" }),
    }),
    { name: "chat-draft-store" }
  )
);
