import axios from "axios";

const api = axios.create({ baseURL: "/api", timeout: 60000 });

api.interceptors.request.use((cfg) => {
  const token = localStorage.getItem("token");
  if (token) cfg.headers.Authorization = `Bearer ${token}`;
  return cfg;
});

api.interceptors.response.use(
  (res) => res.data,
  (err) => {
    const status = err.response?.status;
    const detail = err.response?.data?.detail;
    const msg = detail || err.message;

    // 401：token 失效或未登录，跳转登录页（避免页面"看起来空了"）
    if (status === 401 && !window.location.pathname.startsWith("/login")) {
      localStorage.removeItem("token");
      localStorage.removeItem("auth-store");
      const redirect = encodeURIComponent(window.location.pathname + window.location.search);
      window.location.href = `/login?redirect=${redirect}`;
      return Promise.reject(new Error("登录已过期，正在跳转登录页..."));
    }
    return Promise.reject(new Error(msg));
  }
);

export default api;

// ---- Auth ----
export const authApi = {
  login: (username: string, password: string) =>
    api.post("/auth/login", { username, password }),
  register: (username: string, password: string, nickname?: string) =>
    api.post("/auth/register", { username, password, nickname }),
};

// ---- Chat ----
export const chatApi = {
  send: (message: string, sessionId?: string, channel = "web") =>
    api.post("/chat", { message, session_id: sessionId, channel }),
};

// ---- Sessions ----
export const sessionApi = {
  list: (keyword?: string) => api.get("/sessions", { params: { keyword } }),
  recent: (limit = 50) => api.get("/sessions/recent", { params: { limit } }),
  visitors: (params?: {
    keyword?: string; channel?: string; status?: string;
    date_from?: string; date_to?: string; page?: number; page_size?: number;
  }) => api.get("/sessions/visitors", { params }),
  messages: (sid: string) => api.get(`/sessions/${sid}/messages`),
  close: (sid: string) => api.post(`/sessions/${sid}/close`),
  transfer: (sid: string) => api.post(`/sessions/${sid}/transfer`),
};

// ---- Stats ----
export const statsApi = {
  dashboard: (days = 7) => api.get("/stats/dashboard", { params: { days } }),
  overview: (days = 7) => api.get("/stats/overview", { params: { days } }),
  service: (days = 30) => api.get("/stats/service", { params: { days } }),
  topIntents: (days = 7) => api.get("/stats/top-intents", { params: { days } }),
  dailySessions: (days = 30) => api.get("/stats/daily-sessions", { params: { days } }),
};

// ---- Knowledge ----
export const knowledgeApi = {
  list: () => api.get("/knowledge"),
  upload: (file: File, title?: string, chunkSize?: number, overlap?: number,
           action?: string, parentDocId?: string) => {
    const fd = new FormData();
    fd.append("file", file);
    if (title) fd.append("title", title);
    if (chunkSize !== undefined) fd.append("chunk_size", String(chunkSize));
    if (overlap !== undefined) fd.append("overlap", String(overlap));
    if (action) fd.append("action", action);
    if (parentDocId) fd.append("parent_doc_id", parentDocId);
    return api.post("/knowledge/upload", fd);
  },
  remove: (docId: string) => api.delete(`/knowledge/${docId}`),
  config: () => api.get("/knowledge/config"),
  saveConfig: (chunkSize: number, overlap: number) =>
    api.post("/knowledge/config", { chunk_size: chunkSize, overlap }),
  chunks: (docId: string, limit = 100) => api.get(`/knowledge/${docId}/chunks`, { params: { limit } }),
  byHash: (fileHash: string) => api.get(`/knowledge/by-hash/${fileHash}`),
  versions: (docId: string) => api.get(`/knowledge/${docId}/versions`),
  restoreVersion: (docId: string, versionNo: number) =>
    api.post(`/knowledge/${docId}/restore-version`, null, { params: { version_no: versionNo } }),
};

// ---- Prompts ----
export const promptApi = {
  agents: () => api.get("/prompts/agents"),
  versions: (agent: string) => api.get(`/prompts/${agent}/versions`),
  active: (agent: string) => api.get(`/prompts/${agent}/active`),
  save: (agent_name: string, content: string, change_note?: string) =>
    api.post("/prompts/save", { agent_name, content, change_note }),
  activate: (version_id: number) => api.post("/prompts/activate", { version_id }),
  compare: (version_a_id: number, version_b_id: number, test_question: string) =>
    api.post("/prompts/compare", { version_a_id, version_b_id, test_question }),
  remove: (version_id: number) => api.delete(`/prompts/${version_id}`),
};

// ---- Feedback ----
export const feedbackApi = {
  submit: (data: any) => api.post("/feedback", data),
  list: (rating?: string) => api.get("/feedback", { params: { rating } }),
  analysis: () => api.get("/feedback/analysis"),
  analysisOf: (fid: number) => api.get(`/feedback/${fid}/analysis`),
};

// ---- Ops ----
export const opsApi = {
  toolStats: (days = 7) => api.get("/ops/tool-stats", { params: { days } }),
  tokenStats: (days = 7) => api.get("/ops/token-stats", { params: { days } }),
  topErrors: (days = 7) => api.get("/ops/top-errors", { params: { days } }),
  taskLatency: (days = 7) => api.get("/ops/task-latency", { params: { days } }),
  systemStatus: () => api.get("/ops/system-status"),
};

// ---- Products ----
export const productApi = {
  list: (params?: { keyword?: string; category_id?: number; brand?: string; min_price?: number; max_price?: number; limit?: number; offset?: number }) =>
    api.get("/products", { params }),
  getById: (id: number) => api.get(`/products/${id}`),
  getBySku: (sku: string) => api.get(`/products/by-sku/${sku}`),
  create: (data: any) => api.post("/products", data),
  update: (id: number, data: any) => api.put(`/products/${id}`, data),
  remove: (id: number) => api.delete(`/products/${id}`),
  categories: () => api.get("/products/categories"),
  createCategory: (name: string, parent_id?: number, sort_order?: number) =>
    api.post("/products/categories", { name, parent_id, sort_order }),
  reindexKb: () => api.post("/products/reindex-kb"),
};

// ---- Agent Model Config ----
export const agentModelApi = {
  agents: () => api.get("/agent-models/agents"),
  list: () => api.get("/agent-models"),
  defaults: () => api.get("/agent-models/defaults"),
  save: (agentName: string, data: any) => api.post(`/agent-models/${agentName}`, data),
  reset: (agentName: string) => api.delete(`/agent-models/${agentName}`),
};

// ---- Channel ----
export const channelApi = {
  list: () => api.get("/channels"),
  update: (channelKey: string, data: any) => api.put(`/channels/${channelKey}`, data),
  toggle: (channelKey: string) => api.post(`/channels/${channelKey}/toggle`),
};

// ---- Recycle ----
export const recycleApi = {
  list: (table_name?: string) => api.get("/recycle", { params: { table_name } }),
  restore: (id: number) => api.post(`/recycle/${id}/restore`),
};
