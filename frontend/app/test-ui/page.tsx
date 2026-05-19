"use client";

import { useRef, useState } from "react";
import Link from "next/link";
import CameraFeed, { CameraFeedHandle } from "@/components/CameraFeed";
import * as api from "@/lib/api";
import type { LivenessSubmitResponse } from "@/types/api";

interface TestResult {
  challenge: string;
  passed: boolean;
  confidence: number;
  latencyMs: number;
  timestamp: string;
}

const MOCK_CHALLENGES = ["blink", "head_movement", "texture"];

export default function TestUIPage() {
  const cameraRef = useRef<CameraFeedHandle>(null);
  const [selectedChallenge, setSelectedChallenge] = useState("blink");
  const [sessionId, setSessionId] = useState("");
  const [results, setResults] = useState<TestResult[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [lastResponse, setLastResponse] = useState<LivenessSubmitResponse | null>(null);

  async function ensureSession() {
    if (sessionId) return sessionId;
    const session = await api.createSession();
    setSessionId(session.session_id);
    return session.session_id;
  }

  async function runTest() {
    const frame = cameraRef.current?.capture();
    if (!frame) { setError("Kare yakalanamadı."); return; }
    setBusy(true);
    setError("");
    const t0 = performance.now();
    try {
      const sid = await ensureSession();
      const res = await api.submitLiveness({ session_id: sid, challenge_name: selectedChallenge, frame });
      const latencyMs = Math.round(performance.now() - t0);
      setLastResponse(res);
      setResults((prev) => [
        {
          challenge: selectedChallenge,
          passed: res.passed,
          confidence: res.confidence,
          latencyMs,
          timestamp: new Date().toLocaleTimeString(),
        },
        ...prev.slice(0, 19),
      ]);
      // Her testten sonra yeni session aç (tekrar test edebilmek için)
      setSessionId("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Hata");
    } finally {
      setBusy(false);
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
        {/* Sol: Kamera + Kontroller */}
        <div className="flex flex-col gap-4">
          <CameraFeed ref={cameraRef} className="w-full aspect-video" />

          <div className="flex flex-col gap-3">
            <label className="text-sm text-gray-400">Modül Seç</label>
            <div className="flex gap-2 flex-wrap">
              {MOCK_CHALLENGES.map((ch) => (
                <button
                  key={ch}
                  onClick={() => setSelectedChallenge(ch)}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition border
                    ${selectedChallenge === ch
                      ? "bg-blue-600 border-blue-600 text-white"
                      : "border-gray-600 text-gray-400 hover:border-gray-400"}`}
                >
                  {ch}
                </button>
              ))}
            </div>

            {error && <p className="text-red-400 text-sm">{error}</p>}

            <button
              onClick={runTest}
              disabled={busy}
              className="px-6 py-3 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-xl font-semibold transition"
            >
              {busy ? "Test ediliyor…" : "▶ Test Başlat"}
            </button>
          </div>
        </div>

        {/* Sağ: Sonuç */}
        <div className="flex flex-col gap-4">
          {/* Son sonuç kartı */}
          {lastResponse && (
            <div className={`rounded-xl p-4 border ${lastResponse.passed ? "border-green-600 bg-green-900/30" : "border-red-600 bg-red-900/30"}`}>
              <p className="text-xs text-gray-400 mb-2">Son Test — {selectedChallenge}</p>
              <div className="flex items-center gap-3">
                <span className="text-3xl">{lastResponse.passed ? "✅" : "❌"}</span>
                <div>
                  <p className="font-semibold">{lastResponse.passed ? "Geçti" : "Başarısız"}</p>
                  <p className="text-gray-400 text-sm">Güven: {(lastResponse.confidence * 100).toFixed(1)}%</p>
                </div>
              </div>
              <p className="text-gray-500 text-xs mt-2">{lastResponse.instruction}</p>
            </div>
          )}

          {/* İstatistik */}
          {results.length > 0 && (
            <div className="bg-gray-800 rounded-xl p-4 flex gap-6 text-center">
              <div>
                <p className="text-2xl font-bold text-green-400">{passCount}</p>
                <p className="text-xs text-gray-400">Geçti</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-red-400">{results.length - passCount}</p>
                <p className="text-xs text-gray-400">Başarısız</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-blue-400">
                  {Math.round(results.reduce((s, r) => s + r.latencyMs, 0) / results.length)}ms
                </p>
                <p className="text-xs text-gray-400">Ort. Gecikme</p>
              </div>
            </div>
          )}

          {/* Geçmiş */}
          <div className="flex flex-col gap-1 max-h-64 overflow-y-auto">
            {results.length === 0 && (
              <p className="text-gray-600 text-sm text-center py-4">Henüz test yapılmadı.</p>
            )}
            {results.map((r, i) => (
              <div key={i} className="flex items-center justify-between bg-gray-800 rounded-lg px-3 py-2 text-sm">
                <span className={r.passed ? "text-green-400" : "text-red-400"}>
                  {r.passed ? "✓" : "✗"} {r.challenge}
                </span>
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
