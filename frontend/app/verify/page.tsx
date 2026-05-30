"use client";

import { useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import CameraFeed, { CameraFeedHandle } from "@/components/CameraFeed";
import * as api from "@/lib/api";
import type { RecognitionResponse } from "@/types/api";

type Status = "idle" | "scanning" | "done" | "error";

export default function VerifyPage() {
  const router    = useRouter();
  const cameraRef = useRef<CameraFeedHandle>(null);

  const [status,  setStatus]  = useState<Status>("idle");
  const [result,  setResult]  = useState<RecognitionResponse | null>(null);
  const [error,   setError]   = useState("");

  async function handleScan() {
    const frame = cameraRef.current?.capture();
    if (!frame) { setError("Kamera hazır değil."); return; }

    setStatus("scanning");
    setError("");
    setResult(null);

    try {
      const res = await api.recognize(frame);
      setResult(res);
      setStatus("done");

      if (res.recognized && res.user_id) {
        sessionStorage.setItem("verified_user", res.name ?? res.user_id);
        setTimeout(() => router.push("/dashboard"), 1500);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Bağlantı hatası");
      setStatus("error");
    }
  }

  function reset() {
    setStatus("idle");
    setResult(null);
    setError("");
  }

  const scanning = status === "scanning";

  return (
    <main className="relative min-h-screen flex flex-col items-center justify-center p-6 z-10">
      <div className="w-full max-w-sm slide-up">

        <Link href="/" className="inline-flex items-center gap-2 text-sm mb-8 transition-colors"
          style={{ color: "var(--text-muted)" }}>
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
          </svg>
          Geri
        </Link>

        <h1 className="text-2xl font-bold mb-6">Kimlik Doğrulama</h1>

        {/* Kamera */}
        <div className="rounded-2xl overflow-hidden mb-5"
          style={{ border: "1px solid var(--border)", height: "280px" }}>
          <CameraFeed ref={cameraRef} className="w-full h-full" />
        </div>

        {/* Sonuç */}
        {status === "done" && result && (
          <div className="rounded-2xl p-5 mb-4 text-center slide-up"
            style={{
              background: result.recognized ? "rgba(16,185,129,0.08)" : "rgba(239,68,68,0.08)",
              border: `1px solid ${result.recognized ? "rgba(16,185,129,0.3)" : "rgba(239,68,68,0.3)"}`,
            }}>
            <div className="w-14 h-14 rounded-2xl mx-auto mb-4 flex items-center justify-center"
              style={{ background: result.recognized ? "rgba(16,185,129,0.15)" : "rgba(239,68,68,0.15)" }}>
              {result.recognized
                ? <svg className="w-7 h-7" style={{ color: "var(--success)" }} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" /></svg>
                : <svg className="w-7 h-7" style={{ color: "var(--danger)" }} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
              }
            </div>

            <p className="font-semibold text-lg mb-1">
              {result.recognized ? `Hoşgeldin, ${result.name}` : "Tanınamadınız"}
            </p>

            {result.recognized && (
              <p className="text-xs mb-1" style={{ color: "var(--text-muted)" }}>
                Yönlendiriliyor…
              </p>
            )}

            {result.recognition_score > 0 && (
              <span className="inline-block px-3 py-1 rounded-full text-xs mt-1"
                style={{ background: "rgba(255,255,255,0.06)", color: "var(--text-muted)" }}>
                Güven: {(result.recognition_score * 100).toFixed(1)}%
              </span>
            )}

            {!result.face_detected && (
              <p className="text-sm mt-2" style={{ color: "#fca5a5" }}>Yüz tespit edilemedi.</p>
            )}
          </div>
        )}

        {/* Hata */}
        {(status === "error" || error) && (
          <p className="text-sm text-center mb-4 px-3 py-2 rounded-lg"
            style={{ background: "rgba(239,68,68,0.1)", color: "#fca5a5" }}>
            {error}
          </p>
        )}

        {/* Butonlar */}
        {status !== "done" || !result?.recognized ? (
          <button
            onClick={status === "error" ? reset : handleScan}
            disabled={scanning}
            className="w-full py-3 rounded-xl font-semibold text-white transition-all"
            style={{
              background: scanning ? "rgba(59,130,246,0.5)" : "var(--accent)",
              cursor: scanning ? "not-allowed" : "pointer",
              boxShadow: scanning ? "none" : "0 4px 20px var(--accent-glow)",
            }}>
            {scanning
              ? "Taranıyor…"
              : status === "error"
                ? "Tekrar Dene"
                : "Yüzünü Tara"}
          </button>
        ) : null}

        {status === "done" && !result?.recognized && (
          <button onClick={reset}
            className="w-full py-3 rounded-xl font-semibold transition-all mt-2"
            style={{ background: "var(--bg-elevated)", color: "var(--text-primary)", border: "1px solid var(--border)" }}>
            Tekrar Dene
          </button>
        )}

      </div>
    </main>
  );
}
