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
  message: string;
}

const POLL_MS = 150;

export default function TestUIPage() {
  const cameraRef   = useRef<CameraFeedHandle>(null);
  const pollingRef  = useRef<ReturnType<typeof setInterval> | null>(null);
  const sessionRef  = useRef("");

  const [challenges,       setChallenges]       = useState<string[]>([]);
  const [selectedChallenge, setSelectedChallenge] = useState("");
  const [results,          setResults]          = useState<TestResult[]>([]);
  const [running,          setRunning]          = useState(false);
  const [progress,         setProgress]         = useState("");
  const [error,            setError]            = useState("");

  useEffect(() => {
    api.getAvailableDetectors()
      .then((r) => {
        const names = r.detectors.map((d) => d.name);
        setChallenges(names);
        if (names.length) setSelectedChallenge(names[0]);
      })
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
    setError("");
    setProgress("Session açılıyor…");
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
          const res = await api.submitLiveness({
            session_id: sessionRef.current,
            challenge_name: selectedChallenge,
            frame,
          });
          const latencyMs = Math.round(performance.now() - t0);
          setProgress(res.instruction || "…");

          if (res.passed) {
            stopPolling();
            setResults((prev) => [{
              challenge: selectedChallenge,
              passed: true,
              confidence: res.confidence,
              latencyMs,
              timestamp: new Date().toLocaleTimeString(),
              message: res.instruction,
            }, ...prev.slice(0, 19)]);
          }
        } catch (e) {
          setError(e instanceof Error ? e.message : "Hata");
          stopPolling();
        }
      }, POLL_MS);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Session hatası");
      setRunning(false);
      setProgress("");
    }
  }

  const passCount = results.filter((r) => r.passed).length;

  return (
    <main className="min-h-screen bg-gray-950 text-white p-6 flex flex-col gap-6 max-w-3xl mx-auto">
      <div className="flex items-center justify-between">
        <Link href="/" className="text-gray-400 hover:text-white text-sm">← Geri</Link>
        <h1 className="text-xl font-bold">🔬 Liveness Modül Testi</h1>
        <span className="text-xs text-gray-500">Sprint 2</span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Sol */}
        <div className="flex flex-col gap-4">
          <CameraFeed ref={cameraRef} className="w-full aspect-video" />

          <div className="flex flex-col gap-3">
            <label className="text-sm text-gray-400">Modül Seç</label>
            <div className="flex gap-2 flex-wrap">
              {challenges.map((ch) => (
                <button key={ch} onClick={() => { if (!running) setSelectedChallenge(ch); }}
                  disabled={running}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition border
                    ${selectedChallenge === ch
                      ? "bg-blue-600 border-blue-600 text-white"
                      : "border-gray-600 text-gray-400 hover:border-gray-400"}`}>
                  {ch}
                </button>
              ))}
            </div>

            {/* İlerleme */}
            {running && progress && (
              <p className="text-blue-300 text-sm animate-pulse">{progress}</p>
            )}
            {error && <p className="text-red-400 text-sm">{error}</p>}

            <button onClick={startTest}
              className={`px-6 py-3 rounded-xl font-semibold transition
                ${running
                  ? "bg-red-700 hover:bg-red-600"
                  : "bg-blue-600 hover:bg-blue-700"}`}>
              {running ? "⏹ Durdur" : "▶ Test Başlat"}
            </button>
          </div>
        </div>

        {/* Sağ */}
        <div className="flex flex-col gap-4">
          {results.length > 0 && (
            <>
              {/* Son sonuç */}
              <div className="rounded-xl p-4 border border-green-600 bg-green-900/30">
                <p className="text-xs text-gray-400 mb-2">Son Test — {results[0].challenge}</p>
                <div className="flex items-center gap-3">
                  <span className="text-3xl">✅</span>
                  <div>
                    <p className="font-semibold">Geçti</p>
                    <p className="text-gray-400 text-sm">Güven: {(results[0].confidence * 100).toFixed(1)}%</p>
                  </div>
                </div>
                <p className="text-gray-500 text-xs mt-1">{results[0].latencyMs}ms — {results[0].message}</p>
              </div>

              {/* İstatistik */}
              <div className="bg-gray-800 rounded-xl p-4 flex gap-6 text-center">
                <div>
                  <p className="text-2xl font-bold text-green-400">{passCount}</p>
                  <p className="text-xs text-gray-400">Geçti</p>
                </div>
                <div>
                  <p className="text-2xl font-bold text-blue-400">
                    {Math.round(results.reduce((s, r) => s + r.latencyMs, 0) / results.length)}ms
                  </p>
                  <p className="text-xs text-gray-400">Ort. Gecikme</p>
                </div>
              </div>
            </>
          )}

          {/* Geçmiş */}
          <div className="flex flex-col gap-1 max-h-64 overflow-y-auto">
            {results.length === 0 && (
              <p className="text-gray-600 text-sm text-center py-4">
                Modülü seç, hareketi yap, Test Başlat'a bas.
              </p>
            )}
            {results.map((r, i) => (
              <div key={i} className="flex items-center justify-between bg-gray-800 rounded-lg px-3 py-2 text-sm">
                <span className="text-green-400">✓ {r.challenge}</span>
                <span className="text-gray-400">{(r.confidence * 100).toFixed(0)}%</span>
                <span className="text-gray-500">{r.latencyMs}ms</span>
                <span className="text-gray-600 text-xs">{r.timestamp}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </main>
  );
}
