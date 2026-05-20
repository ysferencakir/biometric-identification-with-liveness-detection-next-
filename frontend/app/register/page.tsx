"use client";

import { useRef, useState } from "react";
import Link from "next/link";
import CameraFeed, { CameraFeedHandle } from "@/components/CameraFeed";
import { captureFrames } from "@/lib/camera";
import * as api from "@/lib/api";

const REQUIRED_FRAMES = 5;

type Status = "idle" | "capturing" | "uploading" | "done" | "error";

export default function RegisterPage() {
  const cameraRef = useRef<CameraFeedHandle>(null);
  const [name, setName]       = useState("");
  const [status, setStatus]   = useState<Status>("idle");
  const [message, setMessage] = useState("");
  const [userId, setUserId]   = useState("");

  async function handleRegister() {
    if (!name.trim()) { setMessage("Lütfen adınızı girin."); return; }
    setStatus("capturing");
    setMessage(`${REQUIRED_FRAMES} kare yakalanıyor…`);

    const videoEl = document.querySelector("video") as HTMLVideoElement | null;
    if (!videoEl) { setMessage("Kamera hazır değil."); setStatus("error"); return; }

    const frames = await captureFrames(videoEl, REQUIRED_FRAMES, 400);
    if (frames.length < REQUIRED_FRAMES) {
      setMessage(`Yeterli kare yakalanamadı (${frames.length}/${REQUIRED_FRAMES}). Işığı kontrol edin.`);
      setStatus("error");
      return;
    }

    setStatus("uploading");
    setMessage("Profil oluşturuluyor…");
    try {
      const res = await api.register({ name: name.trim(), frames });
      setUserId(res.user_id ?? "");
      setStatus("done");
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Kayıt başarısız");
      setStatus("error");
    }
  }

  const busy = status === "capturing" || status === "uploading";

  return (
    <main className="relative min-h-screen flex flex-col items-center justify-center p-6 z-10">
      <div className="w-full max-w-md slide-up">

        {/* Geri */}
        <Link href="/" className="inline-flex items-center gap-2 text-sm mb-8 transition-colors"
          style={{ color: "var(--text-muted)" }}>
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
          </svg>
          Geri
        </Link>

        {status !== "done" ? (
          <div className="rounded-2xl p-6" style={{ background: "var(--bg-surface)", border: "1px solid var(--border)" }}>
            <h1 className="text-2xl font-bold mb-1">Yeni Kullanıcı</h1>
            <p className="text-sm mb-6" style={{ color: "var(--text-muted)" }}>
              Kameraya bakın, adınızı girin ve kayıt butonuna basın.
            </p>

            <div className="w-full rounded-xl overflow-hidden mb-5" style={{ aspectRatio: "4/3" }}>
              <CameraFeed ref={cameraRef} className="w-full h-full" />
            </div>

            <div className="flex flex-col gap-3">
              <input
                type="text"
                placeholder="Adınız Soyadınız"
                value={name}
                onChange={(e) => setName(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && !busy && handleRegister()}
                className="w-full px-4 py-3 rounded-xl text-sm outline-none transition-all"
                style={{
                  background: "var(--bg-elevated)",
                  border: "1px solid var(--border)",
                  color: "var(--text-primary)",
                }}
              />

              {(message && status !== "idle") && (
                <p className="text-sm text-center py-2 px-3 rounded-lg"
                  style={{
                    background: status === "error" ? "rgba(239,68,68,0.1)" : "rgba(59,130,246,0.1)",
                    color: status === "error" ? "#fca5a5" : "#93c5fd",
                  }}>
                  {status === "capturing" || status === "uploading"
                    ? <span className="pulse-soft">{message}</span>
                    : message}
                </p>
              )}

              <button onClick={handleRegister} disabled={busy}
                className="w-full py-3 rounded-xl font-semibold text-white transition-all"
                style={{
                  background: busy ? "rgba(59,130,246,0.5)" : "var(--accent)",
                  cursor: busy ? "not-allowed" : "pointer",
                }}>
                {status === "capturing" ? "Kare yakalanıyor…"
                  : status === "uploading" ? "Kaydediliyor…"
                  : "Kaydet"}
              </button>
            </div>
          </div>

        ) : (
          <div className="rounded-2xl p-8 text-center slide-up"
            style={{ background: "var(--bg-surface)", border: "1px solid rgba(16,185,129,0.3)" }}>
            <div className="w-16 h-16 rounded-2xl mx-auto mb-5 flex items-center justify-center"
              style={{ background: "rgba(16,185,129,0.15)" }}>
              <svg className="w-8 h-8" style={{ color: "var(--success)" }} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
              </svg>
            </div>
            <h2 className="text-xl font-bold mb-2">Kayıt Başarılı</h2>
            <p className="mb-1" style={{ color: "var(--text-muted)" }}>
              <span className="font-semibold" style={{ color: "var(--text-primary)" }}>{name}</span> sisteme eklendi.
            </p>
            {userId && <p className="text-xs mb-6" style={{ color: "var(--text-muted)" }}>ID: {userId.slice(0, 8)}…</p>}

            <div className="flex gap-3 justify-center">
              <button onClick={() => { setStatus("idle"); setName(""); setMessage(""); setUserId(""); }}
                className="px-5 py-2.5 rounded-xl text-sm font-medium transition-all"
                style={{ background: "var(--bg-elevated)", color: "var(--text-primary)", border: "1px solid var(--border)" }}>
                Yeni Kayıt
              </button>
              <Link href="/verify"
                className="px-5 py-2.5 rounded-xl text-sm font-semibold text-white transition-all"
                style={{ background: "var(--accent)" }}>
                Doğrula
              </Link>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
