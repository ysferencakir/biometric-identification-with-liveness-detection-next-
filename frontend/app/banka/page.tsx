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
  new_blink:      "Lütfen yeni yöntemle (New Blink) doğal şekilde iki kez göz kırpın.",
  head_movement:  "Başınızı sağa, sonra sola çevirin.",
  mouth_movement: "Ağzınızı iki kez açıp kapatın.",
  speech:         "Lütfen ekrandaki cümleyi sesli okuyun.",
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
  const sessionRef   = useRef("");

  const [step,       setStep]       = useState<Step>("idle");
  const [challenges, setChallenges] = useState<ChallengeState[]>([]);
  const [currentIdx, setCurrentIdx] = useState(0);
  const [progress,   setProgress]   = useState("");
  const [error,      setError]      = useState("");
  const [userName,   setUserName]   = useState("");

  // Speech Liveness States
  const [speechChallengeId, setSpeechChallengeId] = useState("");
  const [speechTargetText, setSpeechTargetText] = useState("");
  const [speechTranscript, setSpeechTranscript] = useState("");
  const [speechState, setSpeechState] = useState<"idle" | "loading" | "recording" | "verifying" | "success" | "failed">("idle");
  const [speechTimeLeft, setSpeechTimeLeft] = useState(25.0);

  const speechRecorderRef = useRef<MediaRecorder | null>(null);
  const speechChunksRef = useRef<Blob[]>([]);
  const speechTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const speechStreamRef = useRef<MediaStream | null>(null);
  const recognitionRef = useRef<any>(null);

  useEffect(() => {
    const stored = sessionStorage.getItem("verified_user");
    if (!stored) { router.replace("/"); return; }
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setUserName(stored);
  }, [router]);

  const stopPolling = useCallback(() => {
    if (pollingRef.current) { clearInterval(pollingRef.current); pollingRef.current = null; }
  }, []);

  const cleanupSpeechMedia = useCallback(() => {
    if (speechTimerRef.current) {
      clearInterval(speechTimerRef.current);
      speechTimerRef.current = null;
    }
    if (speechStreamRef.current) {
      speechStreamRef.current.getTracks().forEach(track => track.stop());
      speechStreamRef.current = null;
    }
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch (err) {
        // already stopped
      }
      recognitionRef.current = null;
    }
  }, []);

  useEffect(() => {
    return () => {
      stopPolling();
      cleanupSpeechMedia();
    };
  }, [stopPolling, cleanupSpeechMedia]);

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
            
            const nextCh = updated[next];
            if (nextCh.name === "speech") {
              setupSpeechChallenge();
            } else {
              setTimeout(() => startPollingRef.current(sessId, nextCh, next, updated), 800);
            }
          }
        }
      } catch (e) { setError(e instanceof Error ? e.message : "Hata"); stopPolling(); }
    }, POLL_MS);
  }, [stopPolling]);

  useEffect(() => { startPollingRef.current = startPolling; }, [startPolling]);

  async function setupSpeechChallenge() {
    setSpeechState("loading");
    setSpeechTranscript("");
    setError("");
    try {
      const res = await api.getSpeechChallenge();
      setSpeechChallengeId(res.challenge_id);
      setSpeechTargetText(res.target_text);
      setSpeechState("idle");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Cümle yüklenemedi.");
      setSpeechState("idle");
    }
  }

  async function startSpeechRecording() {
    setError("");
    cleanupSpeechMedia();
    setSpeechState("recording");
    setSpeechTimeLeft(25.0);
    speechChunksRef.current = [];
    setSpeechTranscript(""); // Clear old transcript

    // Initialize Web Speech API for Real-Time feedback (WOW Factor)
    try {
      const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      if (SpeechRecognition) {
        const rec = new SpeechRecognition();
        rec.continuous = true;
        rec.interimResults = true;
        rec.lang = "tr-TR";
        
        rec.onresult = (event: any) => {
          let interimTranscript = "";
          let finalTranscript = "";
          
          for (let i = event.resultIndex; i < event.results.length; ++i) {
            if (event.results[i].isFinal) {
              finalTranscript += event.results[i][0].transcript;
            } else {
              interimTranscript += event.results[i][0].transcript;
            }
          }
          
          const liveText = finalTranscript + interimTranscript;
          if (liveText.trim()) {
            setSpeechTranscript(liveText);
          }
        };
        
        recognitionRef.current = rec;
        rec.start();
      }
    } catch (speechApiErr) {
      console.warn("Web Speech API not supported or failed to initialize:", speechApiErr);
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      speechStreamRef.current = stream;
      
      const mediaRecorder = new MediaRecorder(stream, { mimeType: "audio/webm" });
      speechRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          speechChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(speechChunksRef.current, { type: "audio/webm" });
        await handleVerifySpeech(audioBlob);
      };

      mediaRecorder.start();

      const timer = setInterval(() => {
        setSpeechTimeLeft((prev) => {
          if (prev <= 0.1) {
            clearInterval(timer);
            if (mediaRecorder.state === "recording") {
              mediaRecorder.stop();
            }
            return 0;
          }
          return Number((prev - 0.1).toFixed(1));
        });
      }, 100);
      speechTimerRef.current = timer;

    } catch (err) {
      setError("Mikrofon izni alınamadı. Lütfen tarayıcı ayarlarını kontrol edin.");
      setSpeechState("idle");
      cleanupSpeechMedia();
    }
  }

  function stopSpeechRecordingEarly() {
    if (speechRecorderRef.current && speechRecorderRef.current.state === "recording") {
      speechRecorderRef.current.stop();
      setSpeechState("verifying");
    }
    cleanupSpeechMedia();
  }

  async function handleVerifySpeech(blob: Blob) {
    setSpeechState("verifying");
    setError("");
    try {
      const res = await api.verifySpeechLiveness(speechChallengeId, blob, sessionRef.current);
      setSpeechTranscript(res.transcript);
      if (res.success) {
        setSpeechState("success");
        const updated = challenges.map((c, i) => i === currentIdx ? { ...c, passed: true } : c);
        setChallenges(updated);
        
        const allPassed = updated.every(c => c.passed);
        if (allPassed) {
          if (verifyingRef.current) return;
          verifyingRef.current = true;
          setTimeout(() => {
            setStep("done");
          }, 1500);
        } else {
          const next = currentIdx + 1;
          setTimeout(() => {
            setCurrentIdx(next);
            setStep(next === 1 ? "challenge_2" : "challenge_1");
            const nextCh = updated[next];
            if (nextCh.name === "speech") {
              setupSpeechChallenge();
            } else {
              startPolling(sessionRef.current, nextCh, next, updated);
            }
          }, 1500);
        }
      } else {
        setSpeechState("failed");
        setError("Cümle eşleşmedi, lütfen tekrar deneyin.");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Doğrulama sunucu hatası.");
      setSpeechState("failed");
    }
  }

  async function handleSkipSpeech() {
    cleanupSpeechMedia();
    setError("");
    setProgress("");
    await startSession(true);
  }

  async function startSession(excludeSpeech = false) {
    const shouldExclude = excludeSpeech === true;
    stopPolling();
    cleanupSpeechMedia();
    setError(""); setProgress(""); setChallenges([]);
    verifyingRef.current = false;
    setStep("creating");
    setSpeechState("idle");
    setSpeechTargetText("");
    setSpeechTranscript("");

    try {
      const session = await api.createSession(shouldExclude);
      sessionRef.current = session.session_id;
      const ch = session.challenges.map(name => ({
        name,
        instruction: INSTRUCTIONS[name] ?? "Kameraya bakın.",
        passed: null,
      }));
      setChallenges(ch);
      setCurrentIdx(0);
      setStep("challenge_1");

      if (ch[0].name === "speech") {
        setupSpeechChallenge();
      } else {
        startPolling(session.session_id, ch[0], 0, ch);
      }
    } catch (e) { setError(e instanceof Error ? e.message : "Bağlantı hatası"); setStep("idle"); }
  }

  function reset() {
    stopPolling();
    cleanupSpeechMedia();
    verifyingRef.current = false;
    sessionRef.current = "";
    setStep("idle");
    setError("");
    setProgress("");
    setChallenges([]);
    setCurrentIdx(0);
    setSpeechState("idle");
    setSpeechTargetText("");
    setSpeechTranscript("");
  }

  // Banka arayüzü göster
  if (step === "done") {
    return <BankDashboard name={userName} onExit={() => router.push("/dashboard")} />;
  }

  const activeStep  = step === "challenge_1" ? 0 : step === "challenge_2" ? 1 : -1;
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
            <button onClick={() => startSession(false)}
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
            
            {currentCh.name === "speech" ? (
              <div className="flex flex-col items-center">
                {speechState === "loading" ? (
                  <div className="py-4">
                    <p className="text-sm pulse-soft" style={{ color: "var(--text-muted)" }}>Yeni cümle üretiliyor…</p>
                  </div>
                ) : (
                  <>
                    <p className="font-semibold text-xs tracking-wider uppercase mb-1.5" style={{ color: "var(--text-muted)" }}>
                      Lütfen Bu Cümleyi Sesli Okuyun:
                    </p>
                    <p className="text-sm md:text-base font-bold mb-4 px-3 py-2.5 rounded-xl tracking-wide leading-snug w-full"
                      style={{ background: "var(--bg-elevated)", border: "1px solid var(--border)", color: "var(--text-primary)" }}>
                      “{speechTargetText}”
                    </p>

                    {speechState === "recording" && (
                      <div className="flex flex-col items-center mb-3">
                        <p className="text-xs text-red-400 animate-pulse font-semibold">
                          Dinleniyor... ({speechTimeLeft.toFixed(1)} sn)
                        </p>
                        {/* Audio Wave columns */}
                        <div className="flex items-end gap-1 h-5 mt-1">
                          {[1, 2, 3, 4, 3, 2, 1].map((bar, i) => (
                            <div key={i} className="w-0.5 bg-red-400 rounded-full animate-bounce"
                              style={{
                                height: `${bar * 25}%`,
                                animationDuration: `${0.5 + (i % 3) * 0.1}s`,
                                animationDelay: `${i * 0.05}s`
                              }} />
                          ))}
                        </div>
                      </div>
                    )}

                    {speechState === "verifying" && (
                      <div className="flex flex-col items-center justify-center py-2 mb-3">
                        <div className="w-4 h-4 rounded-full border-2 border-t-indigo-500 animate-spin mb-1"
                          style={{ borderColor: "rgba(255,255,255,0.06)", borderTopColor: "var(--accent)" }} />
                        <p className="text-[10px] text-blue-400 animate-pulse font-semibold">
                          Ses analiz ediliyor...
                        </p>
                      </div>
                    )}

                    {speechState === "success" && (
                      <p className="text-xs font-semibold mb-3" style={{ color: "var(--success)" }}>
                        Doğrulama Başarılı! ✓
                      </p>
                    )}

                    {speechState === "failed" && (
                      <p className="text-xs font-semibold mb-3" style={{ color: "var(--danger)" }}>
                        Cümle eşleşmedi, tekrar deneyin. ✗
                      </p>
                    )}

                    {/* Transkript Gösterimi (Transkript ekranın altında yazsın) */}
                    {speechTranscript && (
                      <div className="w-full text-left py-2 px-3 rounded-lg mb-3"
                        style={{ background: "rgba(255,255,255,0.03)", border: "1px solid var(--border)" }}>
                        <span className="text-[9px] uppercase font-bold tracking-wider" style={{ color: "var(--text-muted)" }}>Söylenen (Duyulan):</span>
                        <p className="text-xs italic font-medium mt-0.5" style={{ color: "var(--text-primary)" }}>“{speechTranscript}”</p>
                      </div>
                    )}

                    {/* Action buttons */}
                    <div className="w-full flex flex-col gap-2">
                      {speechState === "recording" ? (
                        <button onClick={stopSpeechRecordingEarly}
                          className="w-full py-2.5 rounded-xl text-xs font-semibold text-white transition-all"
                          style={{ background: "rgba(239,68,68,0.9)", cursor: "pointer" }}>
                          Kaydı Tamamla
                        </button>
                      ) : (
                        <button onClick={startSpeechRecording}
                          disabled={speechState === "verifying" || speechState === "success"}
                          className="w-full py-2.5 rounded-xl text-xs font-semibold text-white flex items-center justify-center gap-1.5 transition-all"
                          style={{
                            background: "linear-gradient(135deg, #059669, #10b981)",
                            cursor: (speechState === "verifying" || speechState === "success") ? "not-allowed" : "pointer",
                            opacity: (speechState === "verifying" || speechState === "success") ? 0.6 : 1
                          }}>
                          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M12 18.75a6 6 0 006-6v-1.5m-6 7.5a6 6 0 01-6-6v-1.5m6 7.5v3.75m-3.75 0h7.5M12 15.75a3 3 0 01-3-3V4.5a3 3 0 116 0v8.25a3 3 0 01-3 3z" />
                          </svg>
                          {speechState === "failed" ? "Tekrar Konuş" : "Konuşmaya Başla"}
                        </button>
                      )}

                      {speechState !== "recording" && speechState !== "verifying" && speechState !== "success" && (
                        <button onClick={handleSkipSpeech}
                          className="w-full py-2 rounded-xl text-xs font-semibold transition-all border"
                          style={{
                            background: "var(--bg-elevated)",
                            color: "var(--text-primary)",
                            borderColor: "var(--border)",
                            cursor: "pointer"
                          }}>
                          Şu an konuşamıyorum
                        </button>
                      )}
                    </div>
                  </>
                )}
              </div>
            ) : (
              <>
                <p className="font-semibold mb-4">{currentCh.instruction}</p>

                {progress && progress !== currentCh.instruction && (
                  <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-sm mb-3"
                    style={{ background: "rgba(16,185,129,0.1)", color: "#34d399" }}>
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 pulse-soft" />
                    {progress}
                  </div>
                )}
              </>
            )}

            {error && currentCh.name !== "speech" && <p className="text-sm mt-2" style={{ color: "#fca5a5" }}>{error}</p>}
            {error && currentCh.name === "speech" && speechState !== "recording" && <p className="text-xs mt-1.5 text-center" style={{ color: "#fca5a5" }}>{error}</p>}

            <div className="flex items-center justify-center gap-2 mt-3 text-xs" style={{ color: "var(--text-muted)" }}>
              <span className="w-2 h-2 rounded-full" style={{ background: "#34d399" }} />
              {currentCh.name === "speech" ? "Mikrofon ve Kamera aktif" : "Kamera aktif — hareketi gerçekleştirin"}
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
