// API_CONTRACT.md ile senkron tutulmalı

export interface HealthResponse {
  status: string;
  version: string;
  model: string;
}

// ── Registration ──────────────────────────────────────────────────────────────

export interface RegisterRequest {
  name: string;
  frames: string[]; // base64[]
}

export interface RegisterResponse {
  success: boolean;
  user_id: string | null;
  name: string | null;
  frames_used: number;
  message: string;
}

// ── Recognition ───────────────────────────────────────────────────────────────

export interface RecognitionResponse {
  face_detected: boolean;
  face_count: number;
  recognized: boolean;
  user_id: string | null;
  name: string | null;
  recognition_score: number;
  bbox: [number, number, number, number] | null;
  message: string;
}

// ── Session ───────────────────────────────────────────────────────────────────

export interface SessionCreateResponse {
  session_id: string;
  challenges: string[]; // ["blink", "texture"]
  expires_at: string;   // ISO-8601
}

export type SessionStatus = "active" | "completed" | "expired" | "denied";

export interface SessionStatusResponse {
  session_id: string;
  status: SessionStatus;
  challenges: string[];
  completed_challenges: string[];
  expires_at: string;
}

// ── Liveness ──────────────────────────────────────────────────────────────────

export interface DetectorInfo {
  name: string;
  instruction: string;
}

export interface LivenessAvailableResponse {
  detectors: DetectorInfo[];
}

export interface LivenessSubmitRequest {
  session_id: string;
  challenge_name: string;
  frame: string; // base64
}

export interface LivenessSubmitResponse {
  challenge_name: string;
  passed: boolean;
  confidence: number;
  instruction: string;
  all_challenges_passed: boolean;
}

// ── Verify ────────────────────────────────────────────────────────────────────

export interface VerifyRequest {
  session_id: string;
  frame: string; // base64
}

export interface LivenessResultSummary {
  challenge: string;
  passed: boolean;
  confidence: number;
}

export interface VerifyResponse {
  access_granted: boolean;
  matched_user: string | null;
  name: string | null;
  recognition_score: number;
  liveness_results: LivenessResultSummary[];
  decision_reason: string;
}

// ── Users ─────────────────────────────────────────────────────────────────────

export interface UserSummary {
  id: string;
  name: string;
  created_at: string;
}

export interface UsersListResponse {
  users: UserSummary[];
  count: number;
}

export interface ApiError {
  detail: string;
}

// ── Speech Liveness ───────────────────────────────────────────────────────────

export interface SpeechChallengeResponse {
  challenge_id: string;
  target_text: string;
}

export interface SpeechLivenessResponse {
  success: boolean;
  target_text: string;
  transcript: string;
  similarity: number;
  threshold: number;
  word_match_ratio: number;
  duration_seconds: number;
}

