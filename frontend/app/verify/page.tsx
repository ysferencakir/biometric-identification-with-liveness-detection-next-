"use client";

import { useRef, useState, useEffect, useCallback } from "react";
import Link from "next/link";
import CameraFeed, { CameraFeedHandle } from "@/components/CameraFeed";
import * as api from "@/lib/api";
import type { VerifyResponse } from "@/types/api";

type Step = "idle" | "creating" | "challenge_1" | "challenge_2" | "verifying" | "done";

interface ChallengeState {
  name: string;
  instruction: string;
  passed: boolean | null;
}

const POLL_INTERVAL_MS = 120; // her 120ms'de bir frame gönder — blink yakalamak için

export default function VerifyPage() {
  const cameraRef    = useRef<CameraFeedHandle>(null);
  const pollingRef   = useRef<ReturnType<typeof setInterval> | null>(null);
  const verifyingRef = useRef(false); // paralel verify çağrısını önle

  const [step,        setStep]        = useState<Step>("idle");
  const [_sessionId,  setSessionId]   = useState("");
  const [challenges,  setChallenges]  = useState<ChallengeState[]>([]);
  const [currentIdx,  setCurrentIdx]  = useState(0);
  const [result,      setResult]      = useState<VerifyResponse | null>(null);
  const [error,       setError]       = useState("");
  const [progress,    setProgress]    = useState("");  // "Göz kırpma: 1/2"

  // Polling'i durdur
  const stopPolling = useCallback(() => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
  }, []);

  // Unmount'ta temizle
  useEffect(() => () => stopPolling(), [stopPolling]);

  // Challenge polling loop
  const startPolling = useCallback((sessId: string, ch: ChallengeState, idx: number, allChallenges: ChallengeState[]) => {
    stopPolling();
    setProgress("");
    setError("");

    pollingRef.current = setInterval(async () => {
      const frame = cameraRef.current?.capture();
      if (!frame) return;

      try {
        const res = await api.submitLiveness({
          session_id:     sessId,
          challenge_name: ch.name,
          frame,
        });

        // Backend'den gelen talimat/ilerleme mesajını göster
        setProgress(res.instruction);

        if (res.passed) {
          stopPolling();
          const updated = allChallenges.map((c, i) =>
            i === idx ? { ...c, passed: true } : c
          );
          setChallenges(updated);

          if (res.all_challenges_passed) {
            if (verifyingRef.current) return;
            verifyingRef.current = true;
            setStep("verifying");
            runVerify(sessId);
          } else {
            const nextIdx = idx + 1;
            setCurrentIdx(nextIdx);
            setStep(nextIdx === 1 ? "challenge_2" : "challenge_1");
            // Kısa bekleyip bir sonraki challenge'ı başlat
            setTimeout(() => startPolling(sessId, updated[nextIdx], nextIdx, updated), 800);
          }
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : "Hata");
      }
    }, POLL_INTERVAL_MS);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stopPolling]);

  async function startSession() {
    setError("");
    setProgress("");
    setChallenges([]);
    setResult(null);
    try {
      setStep("creating");
      const session = await api.createSession();
      setSessionId(session.session_id);

      const instructionMap: Record<string, string> = {
        blink:         "Lütfen iki kez göz kırpın.",
        head_movement: "Başınızı sağa, sonra sola çevirin.",
        texture:       "Kameraya düz bakın.",
      };

      const ch: ChallengeState[] = session.challenges.map((name) => ({
        name,
        instruction: instructionMap[name] ?? "Kameraya bakın.",
        passed: null,
      }));
      setChallenges(ch);
      setCurrentIdx(0);
      setStep("challenge_1");
      startPolling(session.session_id, ch[0], 0, ch);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Session oluşturulamadı");
      setStep("idle");
    }
  }

  async function runVerify(sessId: string) {
    try {
      const frame = cameraRef.current?.capture();
      if (!frame) throw new Error("Kare yakalanamadı.");
      const res = await api.verify({ session_id: sessId, frame });
      setResult(res);
      setStep("done");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Doğrulama hatası");
      setStep("idle");
    }
  }

  function reset() {
    stopPolling();
    verifyingRef.current = false;
    setStep("idle");
    setResult(null);
    setError("");
    setProgress("");
    setChallenges([]);
    setCurrentIdx(0);
    setSessionId("");
  }

  const currentChallenge = challenges[currentIdx];
  const stepLabel        = step === "challenge_1" ? 1 : step === "challenge_2" ? 2 : null;

  return (
    <main className="min-h-screen bg-gray-950 text-white flex flex-col items-center justify-center p-6 gap-6">
      <Link href="/" className="self-start text-gray-400 hover:text-white text-sm">← Geri</Link>
      <h1 className="text-2xl font-bold">Kimlik Doğrulama</h1>

      {/* Adım göstergesi */}
      {step !== "idle" && step !== "done" && (
        <div className="flex gap-3 items-center text-sm">
          {["Liveness 1", "Liveness 2", "Biyometrik"].map((label, i) => {
            const active = (i === 0 && step === "challenge_1") ||
                           (i === 1 && step === "challenge_2") ||
                           (i === 2 && step === "verifying");
            const done   = (i === 0 && ["challenge_2","verifying","done"].includes(step)) ||
                           (i === 1 && ["verifying","done"].includes(step));
            return (
              <div key={label} className="flex items-center gap-2">
                <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold border-2
                  ${done   ? "bg-green-600 border-green-600" :
                    active ? "border-blue-500 text-blue-400" :
                             "border-gray-600 text-gray-500"}`}>
                  {done ? "✓" : i + 1}
                </div>
                <span className={active ? "text-white" : done ? "text-green-400" : "text-gray-500"}>
                  {label}
                </span>
                {i < 2 && <span className="text-gray-600">→</span>}
              </div>
            );
          })}
        </div>
      )}

      {/* Kamera */}
      {step !== "idle" && step !== "done" && (
        <CameraFeed ref={cameraRef} className="w-80 h-60" />
      )}

      {/* Idle */}
      {step === "idle" && (
        <div className="flex flex-col items-center gap-4">
          <p className="text-gray-400 text-sm text-center max-w-xs">
            Sistem rastgele 2 canlılık testi seçer. Her ikisini geçtikten sonra yüz tanıma yapılır.
          </p>
          {error && <p className="text-red-400 text-sm">{error}</p>}
          <button onClick={startSession}
            className="px-8 py-3 bg-blue-600 hover:bg-blue-700 rounded-xl font-medium transition">
            Başlat
          </button>
        </div>
      )}

      {/* Challenge */}
      {(step === "challenge_1" || step === "challenge_2") && currentChallenge && (
        <div className="flex flex-col items-center gap-4 text-center">
          <div className="bg-gray-800 rounded-xl px-5 py-3 min-w-64">
            <p className="text-xs text-gray-400 mb-1">Adım {stepLabel} / 2 — {currentChallenge.name}</p>
            <p className="text-white font-medium">{currentChallenge.instruction}</p>
          </div>

          {/* İlerleme mesajı (backend'den geliyor) */}
          {progress && (
            <p className="text-blue-300 text-sm animate-pulse">{progress}</p>
          )}

          {error && <p className="text-red-400 text-sm">{error}</p>}

          <div className="flex items-center gap-2 text-gray-400 text-xs">
            <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse"/>
            Kamera aktif — hareketi gerçekleştirin
          </div>
        </div>
      )}

      {/* Creating / Verifying */}
      {step === "creating"  && <p className="text-gray-300 animate-pulse">Oturum oluşturuluyor…</p>}
      {step === "verifying" && <p className="text-gray-300 animate-pulse">Biyometrik doğrulama yapılıyor…</p>}

      {/* Sonuç */}
      {step === "done" && result && (
        <div className={`w-full max-w-sm rounded-2xl p-6 flex flex-col gap-3 text-center
          ${result.access_granted
            ? "bg-green-900/40 border border-green-600"
            : "bg-red-900/40 border border-red-600"}`}>
          <p className="text-4xl">{result.access_granted ? "✅" : "❌"}</p>
          <p className="text-xl font-bold">
            {result.access_granted ? "Erişim Verildi" : "Erişim Reddedildi"}
          </p>
          {result.name && (
            <p className="text-gray-300">
              Hoşgeldin, <span className="font-semibold text-white">{result.name}</span>
            </p>
          )}
          <p className="text-gray-400 text-sm">{result.decision_reason}</p>
          {result.recognition_score > 0 && (
            <p className="text-gray-500 text-xs">
              Skor: {(result.recognition_score * 100).toFixed(1)}%
            </p>
          )}
          {result.liveness_results?.length > 0 && (
            <div className="text-xs text-gray-500 flex flex-col gap-1">
              {/* Her challenge için sadece bir satır göster */}
              {Object.values(
                result.liveness_results.reduce((acc, lr) => {
                  if (!acc[lr.challenge] || lr.passed) acc[lr.challenge] = lr;
                  return acc;
                }, {} as Record<string, typeof result.liveness_results[0]>)
              ).map((lr) => (
                <span key={lr.challenge}>
                  {lr.passed ? "✓" : "✗"} {lr.challenge} — {(lr.confidence * 100).toFixed(0)}%
                </span>
              ))}
            </div>
          )}
          <button onClick={reset}
            className="mt-2 px-6 py-2 bg-gray-700 hover:bg-gray-600 rounded-xl text-sm transition">
            Tekrar Dene
          </button>
        </div>
      )}
    </main>
  );
}
