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
  SpeechChallengeResponse,
  SpeechLivenessResponse,
} from "@/types/api";

const getBaseUrl = () => {
  if (typeof window !== "undefined") {
    const hostname = window.location.hostname;
    // Map 'localhost' to '127.0.0.1' to avoid IPv6 (::1) resolution issues on Windows
    const host = hostname === "localhost" ? "127.0.0.1" : hostname;
    return `http://${host}:8000/api/v1`;
  }
  return "http://127.0.0.1:8000/api/v1";
};

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || getBaseUrl();

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
    let msg = "Bilinmeyen hata";
    if (err && err.detail) {
      if (typeof err.detail === "string") {
        msg = err.detail;
      } else if (Array.isArray(err.detail)) {
        msg = err.detail.map((d: any) => d.msg || JSON.stringify(d)).join(", ");
      } else if (typeof err.detail === "object") {
        msg = err.detail.message || JSON.stringify(err.detail);
      } else {
        msg = String(err.detail);
      }
    }
    throw new Error(msg);
  }

  return res.json() as Promise<T>;
}

// ── System ────────────────────────────────────────────────────────────────────

export const health = () =>
  request<HealthResponse>("/health");

// ── Session ───────────────────────────────────────────────────────────────────

export const createSession = (excludeSpeech: boolean = false) =>
  request<SessionCreateResponse>("/session/create", {
    method: "POST",
    body: JSON.stringify({ exclude_speech: excludeSpeech }),
  });

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

// ── Speech Liveness ───────────────────────────────────────────────────────────

export const getSpeechChallenge = () =>
  request<SpeechChallengeResponse>("/speech-liveness/challenge", { method: "POST" });

export const verifySpeechLiveness = async (
  challengeId: string,
  audioBlob: Blob,
  sessionId?: string
): Promise<SpeechLivenessResponse> => {
  const formData = new FormData();
  formData.append("challenge_id", challengeId);
  formData.append("audio_file", audioBlob, "recording.wav");
  if (sessionId) {
    formData.append("session_id", sessionId);
  }

  const res = await fetch(`${BASE_URL}/speech-liveness/verify`, {
    method: "POST",
    body: formData,
    // Note: Do NOT set Content-Type header so the browser sets the multipart boundary automatically
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    let msg = "Bilinmeyen hata";
    if (err && err.detail) {
      msg = typeof err.detail === "string" ? err.detail : JSON.stringify(err.detail);
    }
    throw new Error(msg);
  }

  return res.json() as Promise<SpeechLivenessResponse>;
};
