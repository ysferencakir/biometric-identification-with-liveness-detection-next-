"use client";

import { useRef, useState } from "react";
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

export default function VerifyPage() {
  const cameraRef = useRef<CameraFeedHandle>(null);
  const [step, setStep] = useState<Step>("idle");
  const [sessionId, setSessionId] = useState("");
  const [challenges, setChallenges] = useState<ChallengeState[]>([]);
  const [currentIdx, setCurrentIdx] = useState(0);
  const [result, setResult] = useState<VerifyResponse | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const instructionMap: Record<string, string> = {
    blink: "Lütfen iki kez göz kırpın.",
    head_movement: "Başınızı yavaşça sağa çevirin.",
    texture: "Kameraya düz bakın, hareketsiz kalın.",
  };

  async function startSession() {
    setBusy(true);
    setError("");
    try {
      setStep("creating");
      const session = await api.createSession();
      setSessionId(session.session_id);
      const ch: ChallengeState[] = session.challenges.map((name) => ({
        name,
        instruction: instructionMap[name] ?? "Kameraya bakın.",
        passed: null,
      }));
      setChallenges(ch);
      setCurrentIdx(0);
      setStep("challenge_1");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Session oluşturulamadı");
      setStep("idle");
    } finally {
      setBusy(false);
    }
  }

  async function submitChallenge() {
    const frame = cameraRef.current?.capture();
    if (!frame) { setError("Kare yakalanamadı, tekrar dene."); return; }
    const ch = challenges[currentIdx];
    setBusy(true);
    setError("");
    try {
      const res = await api.submitLiveness({ session_id: sessionId, challenge_name: ch.name, frame });
      const updated = [...challenges];
      updated[currentIdx] = { ...ch, passed: res.passed };
      setChallenges(updated);

      if (!res.passed) {
        setError("Challenge başarısız, tekrar dene.");
        setBusy(false);
        return;
      }

      if (res.all_challenges_passed) {
        setStep("verifying");
        await runVerify();
      } else {
        setCurrentIdx(currentIdx + 1);
        setStep("challenge_2");
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Hata oluştu");
    } finally {
      setBusy(false);
    }
  }

  async function runVerify() {
    const frame = cameraRef.current?.capture();
    if (!frame) { setError("Kare yakalanamadı."); setStep("challenge_2"); return; }
    try {
      const res = await api.verify({ session_id: sessionId, frame });
      setResult(res);
      setStep("done");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Doğrulama hatası");
      setStep("challenge_2");
    }
  }

  const currentChallenge = challenges[currentIdx];
  const stepLabel = step === "challenge_1" ? 1 : step === "challenge_2" ? 2 : null;

  return (
    <main className="min-h-screen bg-gray-950 text-white flex flex-col items-center justify-center p-6 gap-6">
      <Link href="/" className="self-start text-gray-400 hover:text-white text-sm">← Geri</Link>
      <h1 className="text-2xl font-bold">Kimlik Doğrulama</h1>

      {/* Adım göstergesi */}
      {(step !== "idle" && step !== "done") && (
        <div className="flex gap-3 items-center text-sm">
          {["Liveness 1", "Liveness 2", "Biyometrik"].map((label, i) => {
            const active = (i === 0 && step === "challenge_1") || (i === 1 && step === "challenge_2") || (i === 2 && step === "verifying");
            const done = (i === 0 && ["challenge_2", "verifying", "done"].includes(step)) || (i === 1 && ["verifying", "done"].includes(step));
            return (
              <div key={label} className="flex items-center gap-2">
                <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold border-2
                  ${done ? "bg-green-600 border-green-600" : active ? "border-blue-500 text-blue-400" : "border-gray-600 text-gray-500"}`}>
                  {done ? "✓" : i + 1}
                </div>
                <span className={active ? "text-white" : done ? "text-green-400" : "text-gray-500"}>{label}</span>
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

      {/* İçerik */}
      {step === "idle" && (
        <div className="flex flex-col items-center gap-4">
          <p className="text-gray-400 text-sm text-center max-w-xs">
            Sistem rastgele 2 canlılık testi seçer. Her ikisini geçtikten sonra biyometrik doğrulama yapılır.
          </p>
          <button onClick={startSession} disabled={busy}
            className="px-8 py-3 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-xl font-medium transition">
            Başlat
          </button>
        </div>
      )}

      {(step === "challenge_1" || step === "challenge_2") && currentChallenge && (
        <div className="flex flex-col items-center gap-4 text-center">
          <div className="bg-gray-800 rounded-xl px-5 py-3">
            <p className="text-xs text-gray-400 mb-1">Adım {stepLabel} / 2</p>
            <p className="text-white font-medium">{currentChallenge.instruction}</p>
          </div>
          {error && <p className="text-red-400 text-sm">{error}</p>}
          <button onClick={submitChallenge} disabled={busy}
            className="px-8 py-3 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-xl font-medium transition">
            {busy ? "Kontrol ediliyor…" : "Gönder"}
          </button>
        </div>
      )}

      {step === "verifying" && (
        <p className="text-gray-300 animate-pulse">Biyometrik doğrulama yapılıyor…</p>
      )}

      {step === "creating" && (
        <p className="text-gray-300 animate-pulse">Oturum oluşturuluyor…</p>
      )}

      {/* Sonuç */}
      {step === "done" && result && (
        <div className={`w-full max-w-sm rounded-2xl p-6 flex flex-col gap-3 text-center
          ${result.access_granted ? "bg-green-900/40 border border-green-600" : "bg-red-900/40 border border-red-600"}`}>
          <p className="text-4xl">{result.access_granted ? "✅" : "❌"}</p>
          <p className="text-xl font-bold">{result.access_granted ? "Erişim Verildi" : "Erişim Reddedildi"}</p>
          {result.name && <p className="text-gray-300">Hoşgeldin, <span className="font-semibold text-white">{result.name}</span></p>}
          <p className="text-gray-400 text-sm">{result.decision_reason}</p>
          {result.recognition_score > 0 && (
            <p className="text-gray-500 text-xs">Skor: {(result.recognition_score * 100).toFixed(1)}%</p>
          )}
          <button onClick={() => { setStep("idle"); setResult(null); setError(""); setChallenges([]); }}
            className="mt-2 px-6 py-2 bg-gray-700 hover:bg-gray-600 rounded-xl text-sm transition">
            Tekrar Dene
          </button>
        </div>
      )}
    </main>
  );
}
