const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";

export type User = {
  id: number;
  email: string;
  username: string;
  role: string;
  status: string;
  points_balance: number;
  created_at: string;
};

export type AuthResponse = {
  access_token: string;
  refresh_token: string;
  user: User;
  daily_bonus_awarded: number;
};

export type Analysis = {
  id: number;
  original_filename: string;
  file_format: string;
  file_size: number;
  duration_sec: number | null;
  sample_rate: number | null;
  channels: number | null;
  bpm: number | null;
  musical_key: string | null;
  lufs: number | null;
  rms: number | null;
  waveform: number[] | null;
  spectrogram: number[][] | null;
  status: string;
  points_cost: number;
  created_at: string;
};

export type Package = { id: number; name: string; points: number; price: number; currency: string };
export type Plan = { id: number; name: string; monthly_price: number; monthly_points: number; api_limit: number };
export type ApiKey = { id: number; key_prefix: string; name: string; status: string; created_at: string; api_key?: string };
export type ApiUsage = { id: number; key_prefix: string; endpoint: string; status_code: number; points_cost: number; created_at: string };
export type Transaction = { id: number; transaction_type: string; points_change: number; description: string; created_at: string };

const ACCESS_TOKEN_KEY = "audio_analysis_system_access_token";
const REFRESH_TOKEN_KEY = "audio_analysis_system_refresh_token";

let accessToken = localStorage.getItem(ACCESS_TOKEN_KEY) ?? "";
let refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY) ?? "";

export function setToken(token: string): void {
  accessToken = token;
  if (token) {
    localStorage.setItem(ACCESS_TOKEN_KEY, token);
  } else {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
  }
}

export function setSession(response: AuthResponse): void {
  setToken(response.access_token);
  refreshToken = response.refresh_token;
  localStorage.setItem(REFRESH_TOKEN_KEY, response.refresh_token);
}

export function clearTokens(): void {
  accessToken = "";
  refreshToken = "";
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
}

async function refreshAccessToken(): Promise<boolean> {
  if (!refreshToken) return false;
  const response = await fetch(`${API_BASE}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken })
  });
  if (!response.ok) {
    clearTokens();
    return false;
  }
  const data = (await response.json()) as AuthResponse;
  setSession(data);
  return true;
}

async function request<T>(path: string, init: RequestInit = {}, retry = true): Promise<T> {
  const headers = new Headers(init.headers);
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);
  if (init.body !== undefined && !(init.body instanceof FormData)) headers.set("Content-Type", "application/json");
  const response = await fetch(`${API_BASE}${path}`, { ...init, headers });
  if (!response.ok) {
    if (response.status === 401 && retry && refreshToken && !path.startsWith("/auth/")) {
      const refreshed = await refreshAccessToken();
      if (refreshed) return request<T>(path, init, false);
    }
    const detail = await response.json().catch(() => ({ error: { message: "通信に失敗しました。" } }));
    throw new Error(detail.error?.message ?? "リクエストに失敗しました。");
  }
  return response.json() as Promise<T>;
}

export const api = {
  register: (email: string, username: string, password: string) =>
    request<AuthResponse>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, username, password, password_confirmation: password })
    }),
  login: (email: string, password: string) =>
    request<AuthResponse>("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),
  logout: () =>
    request("/auth/logout", {
      method: "POST",
      body: refreshToken ? JSON.stringify({ refresh_token: refreshToken }) : undefined
    }),
  logoutAll: () => request("/auth/logout-all", { method: "POST" }),
  me: () => request<User>("/auth/me"),
  balance: () => request<{ points_balance: number; analysis_cost: number }>("/points/balance"),
  transactions: () => request<Transaction[]>("/points/transactions"),
  analyze: (file: File) => {
    const data = new FormData();
    data.append("file", file);
    return request<Analysis>("/songs/analyze", { method: "POST", body: data });
  },
  history: (filter = "") => request<{ items: Analysis[]; total: number }>(`/songs/history${filter}`),
  packages: () => request<Package[]>("/pricing/packages"),
  plans: () => request<Plan[]>("/plans"),
  subscribe: (planId: number) =>
    request("/subscriptions", { method: "POST", body: JSON.stringify({ plan_id: planId }) }),
  redeem: (code: string) =>
    request("/coupons/redeem", { method: "POST", body: JSON.stringify({ code }) }),
  order: (packageId: number) =>
    request<{ id: number }>("/orders", { method: "POST", body: JSON.stringify({ package_id: packageId }) }),
  pay: (orderId: number) => request(`/orders/${orderId}/mock-pay`, { method: "POST" }),
  keys: () => request<ApiKey[]>("/api-keys"),
  keyUsage: () => request<ApiUsage[]>("/api-keys/usage"),
  issueKey: (name: string) => request<ApiKey>("/api-keys", { method: "POST", body: JSON.stringify({ name }) }),
  revokeKey: (id: number) => request(`/api-keys/${id}`, { method: "DELETE" }),
  adminUsers: () => request<User[]>("/admin/users"),
  adminStatus: (id: number, status: string) =>
    request<User>(`/admin/users/${id}/status`, { method: "PATCH", body: JSON.stringify({ status }) }),
  adminPoints: (id: number, points: number) =>
    request<User>(`/admin/users/${id}/points`, { method: "PATCH", body: JSON.stringify({ points_change: points, reason: "管理画面による調整" }) }),
  report: async (id: number) => {
    const response = await fetch(`${API_BASE}/songs/history/${id}/report`, {
      headers: { Authorization: `Bearer ${accessToken}` }
    });
    if (!response.ok) throw new Error("レポートの生成に失敗しました。");
    return response.blob();
  },
  token: () => accessToken
};
