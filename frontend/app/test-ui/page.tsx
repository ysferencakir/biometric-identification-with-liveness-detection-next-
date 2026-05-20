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

export default function TestUIPage() {
  const cameraRef  = useRef<CameraFeedHandle>(null);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const sessionRef = useRef("");

  const [challenges,        setChallenges]        = useState<string[]>([]);
  const [selected,          setSelected]          = useState("");
  const [results,           setResults]           = useState<TestResult[]>([]);
  const [running,           setRunning]           = useState(false);
  const [progress,          setProgress]          = useState("");
  const [error,             setError]             = useState("");

  useEffect(() => {
    api.getAvailableDetectors()
      .then(r => { const n = r.detectors.map(d => d.name); setChallenges(n); if (n.length) setSelected(n[0]); })
      .catch(() => {});
    return () => stopPolling();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const stopPolling = useCallback(() => {
    if (pollingRef.current) { clearInterval(pollingRef.current); pollingRef.current = null; }
    sessionRef.current = "";
    setRunning(false);
    setProgress("");
  }, []);

  async function startTest() {
    if (running) { stopPolling(); return; }
    setError(""); setProgress("Session açılıyor…");
    try {
      const sess = await api.createSession();
      sessionRef.current = sess.session_id;
      setRunning(true);
      setProgress("Hareketi yapın…");

      pollingRef.current = setInterval(async () => {
        const frame = cameraRef.current?.capture();
        if (!frame) return;
        const t0 = performance.now();
        try {
          const res = await api.submitLiveness({ session_id: sessionRef.current, challenge_name: selected, frame });
          const ms  = Math.round(performance.now() - t0);
          setProgress(res.instruction || "…");
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
    } catch (e) { setError(e instanceof Error ? e.message : "Session hatası"); setRunning(false); setProgress(""); }
  }

  const passCount = results.filter(r => r.passed).length;
  const avgMs     = results.length ? Math.round(results.reduce((s, r) => s + r.latencyMs, 0) / results.length) : 0;

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
                    {ch}
                  </button>
                ))}
                {challenges.length === 0 && (
                  <p className="text-xs" style={{ color: "var(--text-muted)" }}>Backend'e bağlanılamıyor…</p>
                )}
              </div>

              {running && progress && (
                <div className="flex items-center gap-2 mb-3 px-3 py-2 rounded-lg text-sm"
                  style={{ background: "rgba(59,130,246,0.08)", color: "#93c5fd" }}>
                  <span className="w-1.5 h-1.5 rounded-full bg-blue-400 flex-shrink-0 pulse-soft" />
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
