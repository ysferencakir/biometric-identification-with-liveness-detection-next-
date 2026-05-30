import type {
  HealthResponse,
  LivenessAvailableResponse,
  LivenessSubmitRequest,
  LivenessSubmitResponse,
  RecognitionResponse,
  RegisterRequest,
  RegisterResponse,
  SessionCreateResponse,
  SessionStatusResponse,
  UsersListResponse,
  VerifyRequest,
  VerifyResponse,
} from "@/types/api";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

async function request<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Bilinmeyen hata");
  }

  return res.json() as Promise<T>;
}

// ── System ────────────────────────────────────────────────────────────────────

export const health = () =>
  request<HealthResponse>("/health");

// ── Session ───────────────────────────────────────────────────────────────────

export const createSession = () =>
  request<SessionCreateResponse>("/session/create", { method: "POST", body: "{}" });

export const getSession = (sessionId: string) =>
  request<SessionStatusResponse>(`/session/${sessionId}`);

// ── Liveness ──────────────────────────────────────────────────────────────────

export const getAvailableDetectors = () =>
  request<LivenessAvailableResponse>("/liveness/available");

export const submitLiveness = (body: LivenessSubmitRequest) =>
  request<LivenessSubmitResponse>("/liveness/submit", {
    method: "POST",
    body: JSON.stringify(body),
  });

// ── Recognition ───────────────────────────────────────────────────────────────

export const recognize = (image_b64: string) =>
  request<RecognitionResponse>("/recognize", {
    method: "POST",
    body: JSON.stringify({ image_b64 }),
  });

// ── Verify ────────────────────────────────────────────────────────────────────

export const verify = (body: VerifyRequest) =>
  request<VerifyResponse>("/verify", {
    method: "POST",
    body: JSON.stringify(body),
  });

// ── Register ──────────────────────────────────────────────────────────────────

export const register = (body: RegisterRequest) =>
  request<RegisterResponse>("/register", {
    method: "POST",
    body: JSON.stringify(body),
  });

// ── Users ─────────────────────────────────────────────────────────────────────

export const listUsers = () =>
  request<UsersListResponse>("/users");

export const deleteUser = (userId: string) =>
  request<{ success: boolean; message: string }>(`/users/${userId}`, {
    method: "DELETE",
  });
