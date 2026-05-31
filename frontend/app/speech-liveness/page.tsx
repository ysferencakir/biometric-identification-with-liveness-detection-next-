"use client";

import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import * as api from "@/lib/api";
import type { SpeechLivenessResponse } from "@/types/api";

type State = "idle" | "loading_challenge" | "ready" | "requesting_mic" | "recording" | "verifying" | "success" | "failed" | "error";

export default function SpeechLivenessPage() {
  const [state, setState] = useState<State>("idle");
  const [challengeId, setChallengeId] = useState("");
  const [targetText, setTargetText] = useState("");
  const [result, setResult] = useState<SpeechLivenessResponse | null>(null);
  const [error, setError] = useState("");
  const [recordTimeLeft, setRecordTimeLeft] = useState(25.0);

  // References for media recording
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const countdownIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  // Automatically fetch challenge on mount
  useEffect(() => {
    fetchNewChallenge();
    return () => {
      cleanupMedia();
    };
  }, []);

  const cleanupMedia = () => {
    if (countdownIntervalRef.current) {
      clearInterval(countdownIntervalRef.current);
      countdownIntervalRef.current = null;
    }
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
      mediaRecorderRef.current.stop();
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
  };

  const fetchNewChallenge = async () => {
    cleanupMedia();
    setState("loading_challenge");
    setError("");
    setResult(null);
    try {
      const res = await api.getSpeechChallenge();
      setChallengeId(res.challenge_id);
      setTargetText(res.target_text);
      setState("ready");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Yeni cümle alınırken bir hata oluştu.");
      setState("error");
    }
  };

  const startRecording = async () => {
    setError("");
    cleanupMedia();
    setState("requesting_mic");

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      
      const mediaRecorder = new MediaRecorder(stream, { mimeType: "audio/webm" });
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: "audio/webm" });
        await verifyAudio(audioBlob);
      };

      // Start recording
      mediaRecorder.start();
      setState("recording");
      setRecordTimeLeft(25.0);

      // Countdown limit to 25 seconds
      const interval = setInterval(() => {
        setRecordTimeLeft((prev) => {
          if (prev <= 0.1) {
            clearInterval(interval);
            if (mediaRecorder.state === "recording") {
              mediaRecorder.stop();
              setState("verifying");
            }
            return 0;
          }
          return Number((prev - 0.1).toFixed(1));
        });
      }, 100);
      countdownIntervalRef.current = interval;

    } catch (err) {
      setError("Mikrofon izni alınamadı veya mikrofon bulunamadı. Lütfen tarayıcı ayarlarından mikrofon izni verin.");
      setState("error");
    }
  };

  const stopRecordingEarly = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
      mediaRecorderRef.current.stop();
      setState("verifying");
    }
    cleanupMedia();
  };

  const verifyAudio = async (blob: Blob) => {
    setState("verifying");
    try {
      const res = await api.verifySpeechLiveness(challengeId, blob);
      setResult(res);
      if (res.success) {
        setState("success");
      } else {
        setState("failed");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ses doğrulama sunucu hatası.");
      setState("error");
    } finally {
      // Release microphone
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
        streamRef.current = null;
      }
    }
  };

  return (
    <main className="relative min-h-screen flex flex-col items-center justify-center p-4 md:p-6 z-10"
      style={{ background: "linear-gradient(135deg, var(--bg-base) 0%, var(--bg-surface) 100%)" }}>
      
      <div className="w-full max-w-xl slide-up">
        
        {/* Navigation back */}
        <Link href="/" className="inline-flex items-center gap-2 text-sm mb-6 transition-colors"
          style={{ color: "var(--text-muted)" }}>
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
          </svg>
          Geri Dön
        </Link>

        {/* Title Card */}
        <div className="text-center mb-6">
          <span className="text-xs font-semibold tracking-widest uppercase px-3 py-1 rounded-full"
            style={{ background: "rgba(59,130,246,0.1)", color: "#60a5fa", border: "1px solid rgba(59,130,246,0.15)" }}>
            Aktif Liveness Modülü
          </span>
          <h1 className="text-2xl font-bold mt-2.5" style={{ color: "var(--text-primary)" }}>
            Sesli Canlılık Doğrulaması
          </h1>
        </div>

        {/* Main interactive container */}
        <div className="rounded-2xl p-6 md:p-8 flex flex-col items-center shadow-2xl relative overflow-hidden"
          style={{ background: "var(--bg-surface)", border: "1px solid var(--border)", minHeight: "360px" }}>
          
          {/* Glassmorphic glowing circles in background */}
          <div className="absolute top-0 right-0 w-32 h-32 rounded-full filter blur-[60px] opacity-10"
            style={{ background: "var(--accent)" }} />
          <div className="absolute bottom-0 left-0 w-32 h-32 rounded-full filter blur-[60px] opacity-10"
            style={{ background: "var(--success)" }} />

          {/* STATE: LOADING CHALLENGE */}
          {state === "loading_challenge" && (
            <div className="flex-1 flex flex-col items-center justify-center py-12">
              <div className="w-12 h-12 rounded-full border-4 border-t-blue-500 animate-spin mb-4"
                style={{ borderColor: "rgba(255,255,255,0.06)", borderTopColor: "var(--accent)" }} />
              <p className="text-sm font-medium" style={{ color: "var(--text-muted)" }}>
                Yeni Türkçe cümle üretiliyor…
              </p>
            </div>
          )}

          {/* STATE: ERROR */}
          {state === "error" && (
            <div className="flex-1 flex flex-col items-center justify-center text-center py-6">
              <div className="w-16 h-16 rounded-2xl flex items-center justify-center mb-4 text-3xl"
                style={{ background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.2)" }}>
                ⚠️
              </div>
              <p className="font-semibold text-lg mb-2" style={{ color: "var(--text-primary)" }}>İşlem Başarısız</p>
              <p className="text-sm max-w-sm mb-6 leading-relaxed" style={{ color: "#fca5a5" }}>
                {error || "Canlılık testi başlatılırken bir bağlantı sorunuyla karşılaşıldı."}
              </p>
              <button onClick={fetchNewChallenge}
                className="px-6 py-2.5 rounded-xl font-semibold text-white transition-all duration-200"
                style={{ background: "var(--accent)", boxShadow: "0 4px 15px var(--accent-glow)" }}>
                Tekrar Dene
              </button>
            </div>
          )}

          {/* STATES: READY / RECORDING / VERIFYING */}
          {(state === "ready" || state === "requesting_mic" || state === "recording" || state === "verifying") && (
            <div className="w-full flex-1 flex flex-col items-center justify-between">
              
              {/* Target Sentence Box */}
              <div className="w-full text-center py-6 px-4 rounded-2xl mb-8 flex flex-col items-center justify-center transition-all"
                style={{ background: "var(--bg-elevated)", border: "1px solid var(--border)" }}>
                <p className="text-xs font-semibold tracking-wider uppercase mb-3" style={{ color: "var(--text-muted)" }}>
                  LÜTFEN BU CÜMLEYİ OKUYUN:
                </p>
                <h2 className="text-2xl md:text-3xl font-bold px-2 tracking-wide leading-snug"
                  style={{ color: "var(--text-primary)" }}>
                  “{targetText}”
                </h2>
              </div>

              {/* Status information */}
              <div className="text-center mb-6">
                {state === "ready" && (
                  <p className="text-xs leading-relaxed max-w-xs" style={{ color: "var(--text-muted)" }}>
                    Cümleyi sesli olarak okumaya hazır olduğunuzda mikrofon butonuna basın. Süreniz <strong>25 saniyedir</strong>.
                  </p>
                )}
                {state === "requesting_mic" && (
                  <div className="flex items-center gap-2 text-xs" style={{ color: "var(--text-muted)" }}>
                    <span className="w-1.5 h-1.5 rounded-full bg-yellow-400 animate-ping" />
                    Mikrofon izin penceresi bekleniyor...
                  </div>
                )}
                {state === "recording" && (
                  <div className="flex flex-col items-center gap-2">
                    <div className="flex items-center gap-2 text-sm font-semibold text-red-400">
                      <span className="w-2.5 h-2.5 rounded-full bg-red-500 animate-ping" />
                      Dinleniyor… ({recordTimeLeft.toFixed(1)} sn)
                    </div>
                    {/* Bouncing audio wave animation */}
                    <div className="flex items-end gap-1 h-8 mt-2 justify-center">
                      {[1, 2, 3, 4, 5, 4, 3, 2, 1].map((bar, i) => (
                        <div key={i} className="w-1 bg-red-500 rounded-full animate-bounce"
                          style={{
                            height: `${bar * 20}%`,
                            animationDuration: `${0.6 + (i % 3) * 0.15}s`,
                            animationDelay: `${i * 0.05}s`
                          }} />
                      ))}
                    </div>
                  </div>
                )}
                {state === "verifying" && (
                  <div className="flex flex-col items-center gap-3">
                    <div className="w-8 h-8 rounded-full border-3 border-t-indigo-500 animate-spin"
                      style={{ borderColor: "rgba(255,255,255,0.06)", borderTopColor: "var(--accent)" }} />
                    <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                      Ses analizi yapılıyor ve doğrulanıyor…
                    </p>
                  </div>
                )}
              </div>

              {/* Action Buttons */}
              <div className="w-full">
                {state === "ready" && (
                  <button onClick={startRecording}
                    className="w-full py-4 rounded-xl font-semibold text-white flex items-center justify-center gap-3 transition-all active:scale-95"
                    style={{
                      background: "var(--accent)",
                      boxShadow: "0 4px 20px var(--accent-glow)",
                      cursor: "pointer"
                    }}>
                    <svg className="w-5 h-5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M12 18.75a6 6 0 006-6v-1.5m-6 7.5a6 6 0 01-6-6v-1.5m6 7.5v3.75m-3.75 0h7.5M12 15.75a3 3 0 01-3-3V4.5a3 3 0 116 0v8.25a3 3 0 01-3 3z" />
                    </svg>
                    Konuşmaya Başla
                  </button>
                )}

                {state === "recording" && (
                  <button onClick={stopRecordingEarly}
                    className="w-full py-4 rounded-xl font-semibold text-white flex items-center justify-center gap-3 transition-all active:scale-95 animate-pulse"
                    style={{
                      background: "rgba(239, 68, 68, 0.9)",
                      boxShadow: "0 4px 15px rgba(239, 68, 68, 0.3)",
                      cursor: "pointer"
                    }}>
                    <svg className="w-5 h-5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 9.75l4.5 4.5m0-4.5l-4.5 4.5M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    Kaydı Tamamla
                  </button>
                )}

                {(state === "requesting_mic" || state === "verifying") && (
                  <button disabled
                    className="w-full py-4 rounded-xl font-semibold text-white/50 flex items-center justify-center gap-3 transition-all cursor-not-allowed"
                    style={{ background: "var(--bg-elevated)", border: "1px solid var(--border)" }}>
                    Lütfen bekleyin...
                  </button>
                )}
              </div>

            </div>
          )}

          {/* STATES: SUCCESS / FAILED */}
          {(state === "success" || state === "failed") && result && (
            <div className="w-full flex-1 flex flex-col items-center slide-up">
              
              {/* Circular Success / Failure Indicator */}
              <div className="w-16 h-16 rounded-full flex items-center justify-center mb-4 border text-2xl shadow-lg transition-transform"
                style={{
                  background: state === "success" ? "rgba(16,185,129,0.12)" : "rgba(239,68,68,0.12)",
                  borderColor: state === "success" ? "rgba(16,185,129,0.3)" : "rgba(239,68,68,0.3)",
                  color: state === "success" ? "var(--success)" : "var(--danger)"
                }}>
                {state === "success" ? "✓" : "✗"}
              </div>

              <h2 className="text-xl font-bold mb-1"
                style={{ color: state === "success" ? "var(--success)" : "var(--danger)" }}>
                {state === "success" ? "Doğrulama Başarılı!" : "Canlılık Doğrulanamadı"}
              </h2>

              <p className="text-xs mb-6 text-center max-w-sm" style={{ color: "var(--text-muted)" }}>
                {state === "success" 
                  ? "Ses karakterleri ve okunan cümle başarıyla eşleşti. Canlılık testi geçildi." 
                  : "Okunan cümle sistemdeki hedef cümleyle yeterli oranda eşleşmedi."}
              </p>

              {/* Breakdown Metric Card */}
              <div className="w-full rounded-xl p-4 mb-6 text-left flex flex-col gap-3.5"
                style={{ background: "var(--bg-elevated)", border: "1px solid var(--border)" }}>
                
                <div className="flex justify-between items-center pb-2 border-b" style={{ borderColor: "var(--border)" }}>
                  <span className="text-xs font-semibold" style={{ color: "var(--text-muted)" }}>ANALİZ PARAMETRESİ</span>
                  <span className="text-xs font-semibold" style={{ color: "var(--text-muted)" }}>DEĞER</span>
                </div>

                <div className="flex justify-between text-sm">
                  <span style={{ color: "var(--text-muted)" }}>Hedef Cümle</span>
                  <span className="font-semibold text-right" style={{ color: "var(--text-primary)" }}>“{result.target_text}”</span>
                </div>

                <div className="flex justify-between text-sm">
                  <span style={{ color: "var(--text-muted)" }}>Söylenen (Duyulan)</span>
                  <span className="font-semibold text-right italic" style={{ color: "var(--text-primary)" }}>“{result.transcript}”</span>
                </div>

                <div className="flex justify-between text-sm items-center">
                  <span style={{ color: "var(--text-muted)" }}>Karakter Benzerliği</span>
                  <div className="flex items-center gap-2">
                    <div className="w-20 bg-gray-700 h-2 rounded-full overflow-hidden">
                      <div className="h-full rounded-full"
                        style={{
                          width: `${result.similarity}%`,
                          background: result.similarity >= result.threshold ? "var(--success)" : "var(--danger)"
                        }} />
                    </div>
                    <span className="font-bold text-xs" style={{ color: result.similarity >= result.threshold ? "var(--success)" : "var(--danger)" }}>
                      {result.similarity.toFixed(1)}% (Baraj: {result.threshold}%)
                    </span>
                  </div>
                </div>

                <div className="flex justify-between text-sm">
                  <span style={{ color: "var(--text-muted)" }}>Kelime Eşleşme Oranı</span>
                  <span className="font-bold" style={{ color: "var(--text-primary)" }}>
                    {result.word_match_ratio.toFixed(0)}%
                  </span>
                </div>

                <div className="flex justify-between text-sm">
                  <span style={{ color: "var(--text-muted)" }}>Ses Kayıt Süresi</span>
                  <span className="font-semibold" style={{ color: "var(--text-primary)" }}>
                    {result.duration_seconds.toFixed(2)} sn (Maks: 25 sn)
                  </span>
                </div>
              </div>

              {/* Action Workflow Button */}
              <div className="w-full flex gap-3">
                <button onClick={fetchNewChallenge}
                  className="flex-1 py-3.5 rounded-xl font-semibold transition-all active:scale-95 text-sm"
                  style={{
                    background: state === "success" ? "var(--bg-elevated)" : "var(--accent)",
                    color: state === "success" ? "var(--text-primary)" : "white",
                    border: state === "success" ? "1px solid var(--border)" : "none",
                    boxShadow: state === "success" ? "none" : "0 4px 15px var(--accent-glow)"
                  }}>
                  {state === "success" ? "Tekrar Dene" : "Tekrar Dene"}
                </button>
                {state === "success" && (
                  <Link href="/"
                    className="flex-1 py-3.5 rounded-xl font-semibold text-white text-center flex items-center justify-center transition-all active:scale-95 text-sm"
                    style={{ background: "linear-gradient(135deg, #10b981 0%, #059669 100%)", boxShadow: "0 4px 15px rgba(16,185,129,0.3)" }}>
                    Tamamla ve Bitir
                  </Link>
                )}
              </div>

            </div>
          )}

        </div>

      </div>
    </main>
  );
}
