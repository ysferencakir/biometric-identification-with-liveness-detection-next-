"use client";

import { useRef, useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import CameraFeed, { CameraFeedHandle } from "@/components/CameraFeed";
import * as api from "@/lib/api";
import type { VerifyResponse } from "@/types/api";

type Step = "idle" | "creating" | "challenge_1" | "challenge_2" | "verifying" | "done";

interface ChallengeState { name: string; instruction: string; passed: boolean | null; }

const POLL_MS = 120;

const INSTRUCTIONS: Record<string, string> = {
  blink:         "Lütfen doğal şekilde iki kez göz kırpın.",
  head_movement: "Başınızı sağa, sonra sola çevirin.",
  texture:       "Kameraya düz bakın, hareketsiz kalın.",
};

const STEP_LABELS = ["Liveness 1", "Liveness 2", "Biyometrik"];

export default function VerifyPage() {
  const router       = useRouter();
  const cameraRef    = useRef<CameraFeedHandle>(null);
  const pollingRef   = useRef<ReturnType<typeof setInterval> | null>(null);
  const verifyingRef = useRef(false);

  const [step,       setStep]       = useState<Step>("idle");
  const [_sessionId, setSessionId]  = useState("");
  const [challenges, setChallenges] = useState<ChallengeState[]>([]);
  const [currentIdx, setCurrentIdx] = useState(0);
  const [result,     setResult]     = useState<VerifyResponse | null>(null);
  const [error,      setError]      = useState("");
  const [progress,   setProgress]   = useState("");

  const stopPolling = useCallback(() => {
    if (pollingRef.current) { clearInterval(pollingRef.current); pollingRef.current = null; }
  }, []);

  useEffect(() => () => stopPolling(), [stopPolling]);

  const startPolling = useCallback((sessId: string, ch: ChallengeState, idx: number, all: ChallengeState[]) => {
    stopPolling();
    setProgress(""); setError("");

    pollingRef.current = setInterval(async () => {
      const frame = cameraRef.current?.capture();
      if (!frame) return;
      try {
        const res = await api.submitLiveness({ session_id: sessId, challenge_name: ch.name, frame });
        setProgress(res.instruction);
        if (res.passed) {
          stopPolling();
          const updated = all.map((c, i) => i === idx ? { ...c, passed: true } : c);
          setChallenges(updated);
          if (res.all_challenges_passed) {
            if (verifyingRef.current) return;
            verifyingRef.current = true;
            setStep("verifying");
            runVerify(sessId);
          } else {
            const next = idx + 1;
            setCurrentIdx(next);
            setStep(next === 1 ? "challenge_2" : "challenge_1");
            setTimeout(() => startPolling(sessId, updated[next], next, updated), 800);
          }
        }
      } catch (e) { setError(e instanceof Error ? e.message : "Hata"); stopPolling(); }
    }, POLL_MS);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stopPolling]);

  async function startSession() {
    setError(""); setProgress(""); setChallenges([]); setResult(null);
    verifyingRef.current = false;
    setStep("creating");
    try {
      const session = await api.createSession();
      setSessionId(session.session_id);
      const ch = session.challenges.map(name => ({ name, instruction: INSTRUCTIONS[name] ?? "Kameraya bakın.", passed: null }));
      setChallenges(ch);
      setCurrentIdx(0);
      setStep("challenge_1");
      startPolling(session.session_id, ch[0], 0, ch);
    } catch (e) { setError(e instanceof Error ? e.message : "Session hatası"); setStep("idle"); }
  }

  async function runVerify(sessId: string) {
    try {
      const frame = cameraRef.current?.capture();
      if (!frame) throw new Error("Kare yakalanamadı.");
      const res = await api.verify({ session_id: sessId, frame });
      setResult(res); setStep("done");
      if (res.access_granted && res.matched_user) {
        sessionStorage.setItem("verified_user", res.matched_user);
        setTimeout(() => router.push("/dashboard"), 1500);
      }
    } catch (e) { setError(e instanceof Error ? e.message : "Doğrulama hatası"); setStep("idle"); }
  }

  function reset() { stopPolling(); verifyingRef.current = false; setStep("idle"); setResult(null); setError(""); setProgress(""); setChallenges([]); setCurrentIdx(0); setSessionId(""); }

  const activeStep = step === "challenge_1" ? 0 : step === "challenge_2" ? 1 : step === "verifying" ? 2 : -1;
  const currentCh  = challenges[currentIdx];
  const inChallenge = step === "challenge_1" || step === "challenge_2";

  return (
    <main className="relative min-h-screen flex flex-col items-center justify-center p-6 z-10">
      <div className="w-full max-w-md slide-up">

        <Link href="/" className="inline-flex items-center gap-2 text-sm mb-8 transition-colors"
          style={{ color: "var(--text-muted)" }}>
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
          </svg>
          Geri
        </Link>

        <h1 className="text-2xl font-bold mb-6">Kimlik Doğrulama</h1>

        {/* Adım göstergesi */}
        {step !== "idle" && step !== "done" && (
          <div className="flex items-center gap-2 mb-6">
            {STEP_LABELS.map((label, i) => {
              const done   = i < activeStep || (i === 0 && activeStep > 0) || (i === 1 && activeStep > 1);
              const active = i === activeStep;
              return (
                <div key={label} className="flex items-center gap-2 flex-1">
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold transition-all`}
                      style={{
                        background: done ? "var(--success)" : active ? "var(--accent)" : "var(--bg-elevated)",
                        color: (done || active) ? "white" : "var(--text-muted)",
                        border: active ? "2px solid rgba(59,130,246,0.5)" : "none",
                        boxShadow: active ? "0 0 12px var(--accent-glow)" : "none",
                      }}>
                      {done ? "✓" : i + 1}
                    </div>
                    <span className="text-xs hidden sm:block" style={{ color: active ? "var(--text-primary)" : "var(--text-muted)" }}>
                      {label}
                    </span>
                  </div>
                  {i < 2 && <div className="flex-1 h-px" style={{ background: i < activeStep ? "var(--success)" : "var(--border)" }} />}
                </div>
              );
            })}
          </div>
        )}

        {/* Kamera */}
        {step !== "idle" && step !== "done" && (
          <div className="rounded-2xl overflow-hidden mb-5" style={{ border: "1px solid var(--border)", height: "260px" }}>
            <CameraFeed ref={cameraRef} className="w-full h-full" />
          </div>
        )}

        {/* Idle */}
        {step === "idle" && (
          <div className="rounded-2xl p-6 text-center" style={{ background: "var(--bg-surface)", border: "1px solid var(--border)" }}>
            <div className="w-14 h-14 rounded-2xl mx-auto mb-5 flex items-center justify-center"
              style={{ background: "var(--accent-glow)", border: "1px solid rgba(59,130,246,0.2)" }}>
              <svg className="w-7 h-7 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" />
              </svg>
            </div>
            <h2 className="font-semibold mb-2">Hazır mısınız?</h2>
            <p className="text-sm mb-6 leading-relaxed" style={{ color: "var(--text-muted)" }}>
              Sistem rastgele 2 canlılık testi seçer. Her ikisini geçtikten sonra yüz tanıma yapılır.
            </p>
            {error && <p className="text-sm mb-4 px-3 py-2 rounded-lg" style={{ background: "rgba(239,68,68,0.1)", color: "#fca5a5" }}>{error}</p>}
            <button onClick={startSession}
              className="w-full py-3 rounded-xl font-semibold text-white transition-all"
              style={{ background: "var(--accent)", boxShadow: "0 4px 20px var(--accent-glow)" }}>
              Başlat
            </button>
          </div>
        )}

        {/* Challenge */}
        {inChallenge && currentCh && (
          <div className="rounded-2xl p-5 text-center" style={{ background: "var(--bg-surface)", border: "1px solid var(--border)" }}>
            <p className="text-xs mb-1" style={{ color: "var(--text-muted)" }}>
              Adım {currentIdx + 1} / 2 — <span className="font-mono">{currentCh.name}</span>
            </p>
            <p className="font-semibold mb-4">{currentCh.instruction}</p>

            {progress && progress !== currentCh.instruction && (
              <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-sm mb-3"
                style={{ background: "rgba(59,130,246,0.1)", color: "#93c5fd" }}>
                <span className="w-1.5 h-1.5 rounded-full bg-blue-400 pulse-soft" />
                {progress}
              </div>
            )}
            {error && <p className="text-sm mt-2" style={{ color: "#fca5a5" }}>{error}</p>}

            <div className="flex items-center justify-center gap-2 mt-3 text-xs" style={{ color: "var(--text-muted)" }}>
              <span className="w-2 h-2 rounded-full" style={{ background: "var(--success)" }} />
              Kamera aktif — hareketi gerçekleştirin
            </div>
          </div>
        )}

        {(step === "creating" || step === "verifying") && (
          <div className="text-center py-4">
            <p className="pulse-soft text-sm" style={{ color: "var(--text-muted)" }}>
              {step === "creating" ? "Oturum oluşturuluyor…" : "Biyometrik doğrulama yapılıyor…"}
            </p>
          </div>
        )}

        {/* Sonuç */}
        {step === "done" && result && (
          <div className="rounded-2xl p-6 text-center slide-up"
            style={{
              background: result.access_granted ? "rgba(16,185,129,0.08)" : "rgba(239,68,68,0.08)",
              border: `1px solid ${result.access_granted ? "rgba(16,185,129,0.3)" : "rgba(239,68,68,0.3)"}`,
            }}>
            <div className="w-16 h-16 rounded-2xl mx-auto mb-5 flex items-center justify-center"
              style={{ background: result.access_granted ? "rgba(16,185,129,0.15)" : "rgba(239,68,68,0.15)" }}>
              {result.access_granted
                ? <svg className="w-8 h-8" style={{ color: "var(--success)" }} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" /></svg>
                : <svg className="w-8 h-8" style={{ color: "var(--danger)" }} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
              }
            </div>

            <h2 className="text-xl font-bold mb-1">
              {result.access_granted ? "Erişim Verildi" : "Erişim Reddedildi"}
            </h2>

            {result.name && (
              <p className="mb-1" style={{ color: "var(--text-muted)" }}>
                Hoşgeldin, <span className="font-semibold" style={{ color: "var(--text-primary)" }}>{result.name}</span>
              </p>
            )}

            <p className="text-sm mb-4" style={{ color: "var(--text-muted)" }}>{result.decision_reason}</p>

            {result.recognition_score > 0 && (
              <div className="inline-block px-3 py-1 rounded-full text-xs mb-4"
                style={{ background: "rgba(255,255,255,0.06)", color: "var(--text-muted)" }}>
                Yüz skoru: {(result.recognition_score * 100).toFixed(1)}%
              </div>
            )}

            {result.liveness_results?.length > 0 && (
              <div className="flex justify-center gap-3 mb-5">
                {Object.values(
                  result.liveness_results.reduce((acc, lr) => {
                    if (!acc[lr.challenge] || lr.passed) acc[lr.challenge] = lr;
                    return acc;
                  }, {} as Record<string, typeof result.liveness_results[0]>)
                ).map((lr) => (
                  <div key={lr.challenge} className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs"
                    style={{
                      background: lr.passed ? "rgba(16,185,129,0.12)" : "rgba(239,68,68,0.12)",
                      color: lr.passed ? "#6ee7b7" : "#fca5a5",
                    }}>
                    {lr.passed ? "✓" : "✗"} {lr.challenge}
                  </div>
                ))}
              </div>
            )}

            <button onClick={reset}
              className="w-full py-2.5 rounded-xl text-sm font-medium transition-all"
              style={{ background: "var(--bg-elevated)", color: "var(--text-primary)", border: "1px solid var(--border)" }}>
              Tekrar Dene
            </button>
          </div>
        )}

      </div>
    </main>
  );
}
