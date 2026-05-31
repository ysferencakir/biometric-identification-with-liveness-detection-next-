"use client";

import { useRef, useState, useEffect, useCallback } from "react";
import Link from "next/link";
import CameraFeed, { CameraFeedHandle } from "@/components/CameraFeed";
import * as api from "@/lib/api";

interface TestResult {
  challenge: string;
  passed: boolean;
  confidence: number;
  latencyMs: number;
  timestamp: string;
}

const POLL_MS = 150;

// Parmak görseli: kaç parmak kaldırılacağını gösterir
function FingerDisplay({ target, detected }: { target: number; detected: number | null }) {
  return (
    <div className="flex flex-col items-center gap-3">
      {/* Hedef büyük rakam */}
      <div
        className="w-24 h-24 rounded-2xl flex items-center justify-center text-6xl font-black select-none"
        style={{
          background: "var(--accent)",
          boxShadow: "0 4px 24px var(--accent-glow)",
          color: "white",
          lineHeight: 1,
        }}
      >
        {target}
      </div>

      {/* 5 parmak indikatörü */}
      <div className="flex gap-1.5">
        {[1, 2, 3, 4, 5].map((n) => (
          <div
            key={n}
            className="w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold transition-all"
            style={{
              background: n <= target ? "var(--accent)" : "var(--bg-elevated)",
              color: n <= target ? "white" : "var(--text-muted)",
              border: n <= target ? "none" : "1px solid var(--border)",
              opacity: detected !== null && n === detected ? 0.6 : 1,
            }}
          >
            {n}
          </div>
        ))}
      </div>

      {/* Algılanan sayı (varsa) */}
      {detected !== null && (
        <p className="text-xs" style={{ color: detected === target ? "var(--success)" : "#fca5a5" }}>
          {detected === target ? "✓ Doğru!" : `Algılanan: ${detected}`}
        </p>
      )}
    </div>
  );
}

export default function TestUIPage() {
  const cameraRef  = useRef<CameraFeedHandle>(null);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const sessionRef = useRef("");

  const [challenges,   setChallenges]   = useState<string[]>([]);
  const [selected,     setSelected]     = useState("");
  const [results,      setResults]      = useState<TestResult[]>([]);
  const [running,      setRunning]      = useState(false);
  const [progress,     setProgress]     = useState("");
  const [error,        setError]        = useState("");

  // Parmak sayma challenge'ı için
  const [fingerTarget,   setFingerTarget]   = useState<number | null>(null);
  const [fingerDetected, setFingerDetected] = useState<number | null>(null);

  // Ses Liveness Test State'leri
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

  const stopPolling = useCallback(() => {
    if (pollingRef.current) { clearInterval(pollingRef.current); pollingRef.current = null; }
    sessionRef.current = "";
    setRunning(false);
    setProgress("");
    setFingerTarget(null);
    setFingerDetected(null);
    cleanupSpeechMedia();
    setSpeechState("idle");
    setSpeechTargetText("");
    setSpeechTranscript("");
  }, [cleanupSpeechMedia]);

  useEffect(() => {
    api.getAvailableDetectors()
      .then(r => { const n = r.detectors.map(d => d.name); setChallenges(n); if (n.length) setSelected(n[0]); })
      .catch(() => {});
    return () => stopPolling();
  }, [stopPolling]);

  // Instruction metninden hedef sayıyı parse et: "3 parmagunuzu..." → 3
  function parseFingerTarget(instruction: string): number | null {
    const match = instruction.match(/^(\d+)/);
    return match ? parseInt(match[1], 10) : null;
  }

  // Algılanan sayıyı parse et: "...algilanan: 2" → 2
  function parseFingerDetected(instruction: string): number | null {
    const match = instruction.match(/algilanan:\s*(\d+)/i);
    return match ? parseInt(match[1], 10) : null;
  }

  async function setupSpeechChallenge() {
    setSpeechState("loading");
    setSpeechTranscript("");
    setError("");
    setProgress("Cümle yükleniyor…");
    try {
      const res = await api.getSpeechChallenge();
      setSpeechChallengeId(res.challenge_id);
      setSpeechTargetText(res.target_text);
      setSpeechState("idle");
      setProgress("Lütfen aşağıdaki cümleyi sesli okuyun:");
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
      setError("Mikrofon izni alınamadı.");
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
    setProgress("Ses doğrulanıyor…");
    const t0 = performance.now();
    try {
      const res = await api.verifySpeechLiveness(speechChallengeId, blob, sessionRef.current);
      setSpeechTranscript(res.transcript);
      const ms = Math.round(performance.now() - t0);
      
      if (res.success) {
        setSpeechState("success");
        setProgress("Başarılı! Canlılık doğrulandı.");
        setTimeout(() => {
          stopPolling();
          setResults(prev => [{
            challenge: "speech", passed: true,
            confidence: res.similarity / 100.0, latencyMs: ms,
            timestamp: new Date().toLocaleTimeString(),
          }, ...prev.slice(0, 19)]);
        }, 1500);
      } else {
        setSpeechState("failed");
        setError("Cümle eşleşmedi, tekrar deneyin.");
        setProgress("Eşleşme başarısız.");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Doğrulama sunucu hatası.");
      setSpeechState("failed");
    }
  }

  async function startTest() {
    if (running) { stopPolling(); return; }
    setError(""); setProgress("Session açılıyor…");
    setFingerTarget(null);
    setFingerDetected(null);
    setSpeechState("idle");
    setSpeechTargetText("");
    setSpeechTranscript("");

    try {
      const sess = await api.createSession();
      sessionRef.current = sess.session_id;
      setRunning(true);
      
      if (selected === "speech") {
        setupSpeechChallenge();
      } else {
        setProgress("Hareketi yapın…");
        pollingRef.current = setInterval(async () => {
          const frame = cameraRef.current?.capture();
          if (!frame) return;
          const t0 = performance.now();
          try {
            const res = await api.submitLiveness({ session_id: sessionRef.current, challenge_name: selected, frame });
            const ms  = Math.round(performance.now() - t0);
            const instr = res.instruction || "…";
            setProgress(instr);

            // Parmak sayma challenge için hedef/algılanan güncelle
            if (selected === "finger_counting") {
              const t = parseFingerTarget(instr);
              const d = parseFingerDetected(instr);
              if (t !== null) setFingerTarget(t);
              if (d !== null) setFingerDetected(d);
              if (instr === "Tamamlandi!") setFingerDetected(fingerTarget);
            }

            if (res.passed) {
              stopPolling();
              setResults(prev => [{
                challenge: selected, passed: true,
                confidence: res.confidence, latencyMs: ms,
                timestamp: new Date().toLocaleTimeString(),
              }, ...prev.slice(0, 19)]);
            }
          } catch (e) { setError(e instanceof Error ? e.message : "Hata"); stopPolling(); }
        }, POLL_MS);
      }
    } catch (e) { setError(e instanceof Error ? e.message : "Session hatası"); setRunning(false); setProgress(""); }
  }

  const passCount = results.filter(r => r.passed).length;
  const avgMs     = results.length ? Math.round(results.reduce((s, r) => s + r.latencyMs, 0) / results.length) : 0;

  const isFingerChallenge = selected === "finger_counting";

  return (
    <main className="relative min-h-screen p-6 z-10">
      <div className="max-w-3xl mx-auto">

        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <Link href="/" className="inline-flex items-center gap-2 text-sm transition-colors" style={{ color: "var(--text-muted)" }}>
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
            </svg>
            Geri
          </Link>
          <div className="flex items-center gap-3">
            <span className="text-lg font-bold">🔬 Modül Testi</span>
            <span className="px-2 py-0.5 rounded-full text-xs font-medium"
              style={{ background: "rgba(59,130,246,0.15)", color: "#93c5fd" }}>Sprint 4</span>
          </div>
          <div className="w-20" />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">

          {/* Sol: Kamera + Kontroller */}
          <div className="flex flex-col gap-4">
            <div className="rounded-2xl overflow-hidden" style={{ border: "1px solid var(--border)", height: "280px" }}>
              <CameraFeed ref={cameraRef} className="w-full h-full" />
            </div>

            {/* Parmak sayma hedef göstergesi */}
            {isFingerChallenge && running && fingerTarget !== null && (
              <div className="rounded-2xl p-4 flex flex-col items-center gap-1"
                style={{ background: "var(--bg-surface)", border: "1px solid var(--accent)", boxShadow: "0 0 20px rgba(99,102,241,0.12)" }}>
                <p className="text-xs font-medium mb-2" style={{ color: "var(--text-muted)" }}>HEDEF SAYI</p>
                <FingerDisplay target={fingerTarget} detected={fingerDetected} />
              </div>
            )}

            {/* Modül seçimi */}
            <div className="rounded-2xl p-4" style={{ background: "var(--bg-surface)", border: "1px solid var(--border)" }}>
              <p className="text-xs font-medium mb-3" style={{ color: "var(--text-muted)" }}>MODÜL SEÇ</p>
              <div className="flex gap-2 flex-wrap mb-4">
                {challenges.map(ch => (
                  <button key={ch} onClick={() => { if (!running) setSelected(ch); }}
                    disabled={running}
                    className="px-3 py-1.5 rounded-lg text-sm font-medium transition-all"
                    style={{
                      background: selected === ch ? "var(--accent)" : "var(--bg-elevated)",
                      color: selected === ch ? "white" : "var(--text-muted)",
                      border: selected === ch ? "none" : "1px solid var(--border)",
                      boxShadow: selected === ch ? "0 2px 12px var(--accent-glow)" : "none",
                    }}>
                    {ch === "finger_counting" 
                      ? "✋ " + ch 
                      : ch === "new_blink" 
                        ? "👁️✨ " + ch 
                        : ch === "blink" 
                          ? "👁️ " + ch 
                          : ch === "speech"
                            ? "🎙️ " + ch
                            : ch}
                  </button>
                ))}
                {challenges.length === 0 && (
                  <p className="text-xs" style={{ color: "var(--text-muted)" }}>Backend&apos;e bağlanılamıyor…</p>
                )}
              </div>

              {/* Ses Canlılık Arayüzü (Test UI için Özel Bölüm) */}
              {running && selected === "speech" && (
                <div className="flex flex-col items-center py-3 px-1 border-t border-b mb-3" style={{ borderColor: "var(--border)" }}>
                  {speechState === "loading" ? (
                    <p className="text-xs pulse-soft py-2" style={{ color: "var(--text-muted)" }}>Cümle yükleniyor...</p>
                  ) : (
                    <div className="w-full text-center">
                      <span className="text-[10px] font-bold tracking-wider text-gray-400 block mb-1">OKUNACAK CÜMLE:</span>
                      <p className="text-xs md:text-sm font-bold p-2.5 rounded-xl mb-3 tracking-wide leading-snug"
                        style={{ background: "var(--bg-elevated)", border: "1px solid var(--border)", color: "var(--text-primary)" }}>
                        “{speechTargetText}”
                      </p>

                      {speechState === "recording" && (
                        <div className="flex flex-col items-center mb-3">
                          <p className="text-[11px] text-red-400 animate-pulse font-semibold">
                            Dinleniyor... ({speechTimeLeft.toFixed(1)} sn)
                          </p>
                          <div className="flex items-end gap-1 h-4 mt-1">
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
                        <div className="flex items-center justify-center gap-1.5 py-1 mb-2">
                          <div className="w-3.5 h-3.5 rounded-full border-2 border-t-indigo-500 animate-spin"
                            style={{ borderColor: "rgba(255,255,255,0.06)", borderTopColor: "var(--accent)" }} />
                          <span className="text-[11px] text-blue-400 font-semibold animate-pulse">Ses çözümleniyor...</span>
                        </div>
                      )}

                      {speechState === "success" && (
                        <p className="text-xs font-semibold mb-2" style={{ color: "var(--success)" }}>
                          Doğrulama Başarılı! ✓
                        </p>
                      )}

                      {speechState === "failed" && (
                        <p className="text-xs font-semibold mb-2" style={{ color: "var(--danger)" }}>
                          Cümle eşleşmedi, tekrar deneyin. ✗
                        </p>
                      )}

                      {/* Transkript Gösterimi (Transkript ekranın altında yazsın) */}
                      {speechTranscript && (
                        <div className="text-left py-2 px-3 rounded-lg mb-3"
                          style={{ background: "rgba(255,255,255,0.03)", border: "1px solid var(--border)" }}>
                          <span className="text-[9px] uppercase font-bold tracking-wider" style={{ color: "var(--text-muted)" }}>Söylenen (Duyulan):</span>
                          <p className="text-xs italic font-medium mt-0.5" style={{ color: "var(--text-primary)" }}>“{speechTranscript}”</p>
                        </div>
                      )}

                      {speechState === "recording" ? (
                        <button onClick={stopSpeechRecordingEarly}
                          className="w-full py-2 rounded-xl text-xs font-semibold text-white mb-1"
                          style={{ background: "rgba(239,68,68,0.9)", cursor: "pointer" }}>
                          Kaydı Bitir
                        </button>
                      ) : (
                        <button onClick={startSpeechRecording}
                          disabled={speechState === "verifying" || speechState === "success"}
                          className="w-full py-2 rounded-xl text-xs font-semibold text-white flex items-center justify-center gap-1 mb-1"
                          style={{
                            background: "var(--accent)",
                            cursor: (speechState === "verifying" || speechState === "success") ? "not-allowed" : "pointer",
                            opacity: (speechState === "verifying" || speechState === "success") ? 0.6 : 1
                          }}>
                          🎙 {speechState === "failed" ? "Tekrar Konuş" : "Konuşmaya Başla"}
                        </button>
                      )}
                    </div>
                  )}
                </div>
              )}

              {running && progress && (
                <div className="flex items-center gap-2 mb-3 px-3 py-2 rounded-lg text-sm"
                  style={{ background: "rgba(59,130,246,0.08)", color: "#93c5fd" }}>
                  <span className="w-1.5 h-1.5 rounded-full bg-blue-400 shrink-0 pulse-soft" />
                  {progress}
                </div>
              )}
              {error && <p className="text-xs mb-3" style={{ color: "#fca5a5" }}>{error}</p>}

              <button onClick={startTest}
                className="w-full py-2.5 rounded-xl font-semibold text-sm text-white transition-all"
                style={{
                  background: running ? "rgba(239,68,68,0.8)" : "var(--accent)",
                  boxShadow: running ? "none" : "0 2px 16px var(--accent-glow)",
                }}>
                {running ? "⏹ Durdur" : "▶ Test Başlat"}
              </button>
            </div>
          </div>

          {/* Sağ: Sonuçlar */}
          <div className="flex flex-col gap-4">

            {/* İstatistik */}
            <div className="grid grid-cols-3 gap-3">
              {[
                { label: "Geçti", value: passCount, color: "var(--success)" },
                { label: "Test", value: results.length, color: "var(--text-primary)" },
                { label: "Ort. ms", value: avgMs, color: "#60a5fa" },
              ].map(s => (
                <div key={s.label} className="rounded-xl p-3 text-center"
                  style={{ background: "var(--bg-surface)", border: "1px solid var(--border)" }}>
                  <p className="text-2xl font-bold" style={{ color: s.color }}>{s.value}</p>
                  <p className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>{s.label}</p>
                </div>
              ))}
            </div>

            {/* Son sonuç */}
            {results[0] && (
              <div className="rounded-2xl p-4 slide-up"
                style={{ background: "rgba(16,185,129,0.08)", border: "1px solid rgba(16,185,129,0.2)" }}>
                <div className="flex items-center gap-3 mb-2">
                  <div className="w-9 h-9 rounded-xl flex items-center justify-center text-lg"
                    style={{ background: "rgba(16,185,129,0.15)" }}>✅</div>
                  <div>
                    <p className="font-semibold text-sm">{results[0].challenge} — Geçti</p>
                    <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                      {(results[0].confidence * 100).toFixed(0)}% güven · {results[0].latencyMs}ms
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Geçmiş */}
            <div className="rounded-2xl overflow-hidden" style={{ background: "var(--bg-surface)", border: "1px solid var(--border)" }}>
              <div className="px-4 py-3 border-b" style={{ borderColor: "var(--border)" }}>
                <p className="text-xs font-medium" style={{ color: "var(--text-muted)" }}>GEÇMİŞ</p>
              </div>
              <div className="overflow-y-auto max-h-56 flex flex-col">
                {results.length === 0 && (
                  <p className="text-center text-xs py-8" style={{ color: "var(--text-muted)" }}>
                    Henüz test yapılmadı
                  </p>
                )}
                {results.map((r, i) => (
                  <div key={i} className="flex items-center justify-between px-4 py-2.5 text-sm border-t" style={{ borderColor: "var(--border)" }}>
                    <div className="flex items-center gap-2">
                      <span style={{ color: r.passed ? "var(--success)" : "var(--danger)" }}>
                        {r.passed ? "✓" : "✗"}
                      </span>
                      <span style={{ color: "var(--text-primary)" }}>{r.challenge}</span>
                    </div>
                    <div className="flex items-center gap-3 text-xs" style={{ color: "var(--text-muted)" }}>
                      <span>{(r.confidence * 100).toFixed(0)}%</span>
                      <span>{r.latencyMs}ms</span>
                      <span>{r.timestamp}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

          </div>
        </div>
      </div>
    </main>
  );
}
