"use client";

import { useRef, useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import CameraFeed, { CameraFeedHandle } from "@/components/CameraFeed";
import * as api from "@/lib/api";

type Step = "idle" | "creating" | "challenge_1" | "challenge_2" | "done" | "failed";

interface ChallengeState {
  name: string;
  instruction: string;
  passed: boolean | null;
}

const POLL_MS = 120;

const INSTRUCTIONS: Record<string, string> = {
  blink:          "Lütfen doğal şekilde iki kez göz kırpın.",
  head_movement:  "Başınızı sağa, sonra sola çevirin.",
  mouth_movement: "Ağzınızı iki kez açıp kapatın.",
};

const STEP_LABELS = ["Liveness 1", "Liveness 2", "Banka"];

// ── Basit banka arayüzü ────────────────────────────────────────────────────────
function BankDashboard({ name, onExit }: { name: string; onExit: () => void }) {
  const accounts = [
    { label: "Vadesiz Hesap",  iban: "TR12 0001 2345 6789 0123 45", balance: "₺24.850,00",  color: "#60a5fa" },
    { label: "Tasarruf Hesabı", iban: "TR98 0001 2345 6789 0123 46", balance: "₺142.300,00", color: "#34d399" },
  ];
  const transactions = [
    { desc: "Market Alışverişi",    date: "24.05.2026", amount: "-₺387,50",   out: true  },
    { desc: "Maaş Ödemesi",        date: "20.05.2026", amount: "+₺18.500,00", out: false },
    { desc: "Fatura - Elektrik",   date: "18.05.2026", amount: "-₺620,00",    out: true  },
    { desc: "Online Alışveriş",    date: "15.05.2026", amount: "-₺1.240,00",  out: true  },
    { desc: "Kira Ödemesi",        date: "01.05.2026", amount: "-₺9.500,00",  out: true  },
  ];

  return (
    <div className="min-h-screen p-6" style={{ background: "var(--bg-base)", color: "var(--text-primary)" }}>
      {/* Header */}
      <div className="max-w-3xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl flex items-center justify-center font-bold text-white"
              style={{ background: "linear-gradient(135deg,#059669,#10b981)" }}>
              B
            </div>
            <div>
              <p className="font-bold text-sm">BiometriBank</p>
              <p className="text-xs" style={{ color: "var(--text-muted)" }}>Hoşgeldiniz, {name}</p>
            </div>
          </div>
          <button onClick={onExit}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors"
            style={{ background: "rgba(239,68,68,0.1)", color: "#fca5a5", border: "1px solid rgba(239,68,68,0.2)" }}>
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 9V5.25A2.25 2.25 0 0013.5 3h-6a2.25 2.25 0 00-2.25 2.25v13.5A2.25 2.25 0 007.5 21h6a2.25 2.25 0 002.25-2.25V15M12 9l-3 3m0 0l3 3m-3-3h12.75" />
            </svg>
            Çıkış
          </button>
        </div>

        {/* Hesaplar */}
        <div className="grid grid-cols-2 gap-4 mb-6">
          {accounts.map(acc => (
            <div key={acc.iban} className="rounded-2xl p-5"
              style={{ background: "var(--bg-surface)", border: "1px solid var(--border)" }}>
              <p className="text-xs mb-3" style={{ color: "var(--text-muted)" }}>{acc.label}</p>
              <p className="text-2xl font-bold mb-1" style={{ color: acc.color }}>{acc.balance}</p>
              <p className="text-xs font-mono" style={{ color: "var(--text-faint)" }}>{acc.iban}</p>
            </div>
          ))}
        </div>

        {/* İşlemler */}
        <div className="rounded-2xl overflow-hidden"
          style={{ background: "var(--bg-surface)", border: "1px solid var(--border)" }}>
          <div className="px-5 py-4 border-b" style={{ borderColor: "var(--border)" }}>
            <p className="text-sm font-semibold">Son İşlemler</p>
          </div>
          {transactions.map((tx, i) => (
            <div key={i} className="flex items-center justify-between px-5 py-3 border-b last:border-0"
              style={{ borderColor: "var(--border)" }}>
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
                  style={{ background: tx.out ? "rgba(239,68,68,0.1)" : "rgba(16,185,129,0.1)" }}>
                  <svg className="w-4 h-4" style={{ color: tx.out ? "#fca5a5" : "#34d399" }}
                    fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round"
                      d={tx.out ? "M4.5 19.5l15-15m0 0H8.25m11.25 0v11.25" : "M19.5 4.5l-15 15m0 0h11.25m-11.25 0V8.25"} />
                  </svg>
                </div>
                <div>
                  <p className="text-sm font-medium">{tx.desc}</p>
                  <p className="text-xs" style={{ color: "var(--text-muted)" }}>{tx.date}</p>
                </div>
              </div>
              <span className="text-sm font-semibold"
                style={{ color: tx.out ? "#fca5a5" : "#34d399" }}>
                {tx.amount}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── Ana sayfa ──────────────────────────────────────────────────────────────────
export default function BankaPage() {
  const router    = useRouter();
  const cameraRef = useRef<CameraFeedHandle>(null);
  const pollingRef   = useRef<ReturnType<typeof setInterval> | null>(null);
  const verifyingRef = useRef(false);

  const [step,       setStep]       = useState<Step>("idle");
  const [challenges, setChallenges] = useState<ChallengeState[]>([]);
  const [currentIdx, setCurrentIdx] = useState(0);
  const [progress,   setProgress]   = useState("");
  const [error,      setError]      = useState("");
  const [userName,   setUserName]   = useState("");

  useEffect(() => {
    const stored = sessionStorage.getItem("verified_user");
    if (!stored) { router.replace("/"); return; }
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setUserName(stored);
  }, [router]);

  const stopPolling = useCallback(() => {
    if (pollingRef.current) { clearInterval(pollingRef.current); pollingRef.current = null; }
  }, []);

  useEffect(() => () => stopPolling(), [stopPolling]);

  // Ref to allow self-call inside setTimeout without TDZ issues
  const startPollingRef = useRef<(sessId: string, ch: ChallengeState, idx: number, all: ChallengeState[]) => void>(() => {});

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
            setStep("done");
          } else {
            const next = idx + 1;
            setCurrentIdx(next);
            setStep(next === 1 ? "challenge_2" : "challenge_1");
            setTimeout(() => startPollingRef.current(sessId, updated[next], next, updated), 800);
          }
        }
      } catch (e) { setError(e instanceof Error ? e.message : "Hata"); stopPolling(); }
    }, POLL_MS);
  }, [stopPolling]);

  useEffect(() => { startPollingRef.current = startPolling; }, [startPolling]);

  async function startSession() {
    setError(""); setProgress(""); setChallenges([]);
    verifyingRef.current = false;
    setStep("creating");
    try {
      const session = await api.createSession();
      const ch = session.challenges.map(name => ({
        name,
        instruction: INSTRUCTIONS[name] ?? "Kameraya bakın.",
        passed: null,
      }));
      setChallenges(ch);
      setCurrentIdx(0);
      setStep("challenge_1");
      startPolling(session.session_id, ch[0], 0, ch);
    } catch (e) { setError(e instanceof Error ? e.message : "Bağlantı hatası"); setStep("idle"); }
  }

  function reset() {
    stopPolling();
    verifyingRef.current = false;
    setStep("idle");
    setError("");
    setProgress("");
    setChallenges([]);
    setCurrentIdx(0);
  }

  // Banka arayüzü göster
  if (step === "done") {
    return <BankDashboard name={userName} onExit={() => router.push("/dashboard")} />;
  }

  const activeStep  = step === "challenge_1" ? 0 : step === "challenge_2" ? 1 : step === "done" ? 2 : -1;
  const currentCh   = challenges[currentIdx];
  const inChallenge = step === "challenge_1" || step === "challenge_2";

  return (
    <main className="relative min-h-screen flex flex-col items-center justify-center p-6 z-10">
      <div className="w-full max-w-sm slide-up">

        <Link href="/dashboard" className="inline-flex items-center gap-2 text-sm mb-8 transition-colors"
          style={{ color: "var(--text-muted)" }}>
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
          </svg>
          Geri
        </Link>

        {/* Banka başlık */}
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-xl flex items-center justify-center font-bold text-white shrink-0"
            style={{ background: "linear-gradient(135deg,#059669,#10b981)" }}>
            B
          </div>
          <div>
            <h1 className="text-xl font-bold">BiometriBank</h1>
            <p className="text-xs" style={{ color: "var(--text-muted)" }}>Güvenli Giriş — Canlılık Doğrulama</p>
          </div>
        </div>

        {/* Adım göstergesi */}
        {step !== "idle" && (
          <div className="flex items-center gap-2 mb-5">
            {STEP_LABELS.map((label, i) => {
              const done   = i < activeStep;
              const active = i === activeStep;
              return (
                <div key={label} className="flex items-center gap-2 flex-1">
                  <div className="flex items-center gap-1.5 shrink-0">
                    <div className="w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold transition-all"
                      style={{
                        background: done ? "var(--success)" : active ? "#059669" : "var(--bg-elevated)",
                        color: (done || active) ? "white" : "var(--text-muted)",
                        boxShadow: active ? "0 0 12px rgba(16,185,129,0.4)" : "none",
                      }}>
                      {done ? "✓" : i + 1}
                    </div>
                    <span className="text-xs hidden sm:block"
                      style={{ color: active ? "var(--text-primary)" : "var(--text-muted)" }}>
                      {label}
                    </span>
                  </div>
                  {i < 2 && (
                    <div className="flex-1 h-px"
                      style={{ background: i < activeStep ? "var(--success)" : "var(--border)" }} />
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* Kamera */}
        {step !== "idle" && (
          <div className="rounded-2xl overflow-hidden mb-4"
            style={{ border: "1px solid rgba(16,185,129,0.3)", height: "260px" }}>
            <CameraFeed ref={cameraRef} className="w-full h-full" />
          </div>
        )}

        {/* Idle */}
        {step === "idle" && (
          <div className="rounded-2xl p-6 text-center"
            style={{ background: "var(--bg-surface)", border: "1px solid rgba(16,185,129,0.2)" }}>
            <div className="w-14 h-14 rounded-2xl mx-auto mb-4 flex items-center justify-center"
              style={{ background: "rgba(16,185,129,0.1)" }}>
              <svg className="w-7 h-7" style={{ color: "#34d399" }} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" />
              </svg>
            </div>
            <h2 className="font-semibold mb-2">Canlılık Doğrulama</h2>
            <p className="text-sm mb-5 leading-relaxed" style={{ color: "var(--text-muted)" }}>
              Banka hesabınıza erişmek için 2 canlılık testi gereklidir.
            </p>
            {error && (
              <p className="text-xs mb-4 px-3 py-2 rounded-lg"
                style={{ background: "rgba(239,68,68,0.1)", color: "#fca5a5" }}>
                {error}
              </p>
            )}
            <button onClick={startSession}
              className="w-full py-3 rounded-xl font-semibold text-white transition-all"
              style={{ background: "linear-gradient(135deg,#059669,#10b981)", boxShadow: "0 4px 20px rgba(16,185,129,0.3)" }}>
              Doğrulamayı Başlat
            </button>
          </div>
        )}

        {/* Challenge */}
        {inChallenge && currentCh && (
          <div className="rounded-2xl p-5 text-center"
            style={{ background: "var(--bg-surface)", border: "1px solid rgba(16,185,129,0.2)" }}>
            <p className="text-xs mb-1" style={{ color: "var(--text-muted)" }}>
              Adım {currentIdx + 1} / 2 — <span className="font-mono">{currentCh.name}</span>
            </p>
            <p className="font-semibold mb-4">{currentCh.instruction}</p>

            {progress && progress !== currentCh.instruction && (
              <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-sm mb-3"
                style={{ background: "rgba(16,185,129,0.1)", color: "#34d399" }}>
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 pulse-soft" />
                {progress}
              </div>
            )}

            {error && <p className="text-sm mt-2" style={{ color: "#fca5a5" }}>{error}</p>}

            <div className="flex items-center justify-center gap-2 mt-3 text-xs" style={{ color: "var(--text-muted)" }}>
              <span className="w-2 h-2 rounded-full" style={{ background: "#34d399" }} />
              Kamera aktif — hareketi gerçekleştirin
            </div>
          </div>
        )}

        {step === "creating" && (
          <div className="text-center py-4">
            <p className="pulse-soft text-sm" style={{ color: "var(--text-muted)" }}>
              Oturum hazırlanıyor…
            </p>
          </div>
        )}

        {/* Hata varsa sıfırla */}
        {error && step === "idle" && (
          <button onClick={reset}
            className="w-full mt-3 py-2.5 rounded-xl text-sm font-medium"
            style={{ background: "var(--bg-elevated)", color: "var(--text-primary)", border: "1px solid var(--border)" }}>
            Tekrar Dene
          </button>
        )}

      </div>
    </main>
  );
}
