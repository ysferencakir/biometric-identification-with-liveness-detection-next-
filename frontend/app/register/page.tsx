"use client";

import { useRef, useState } from "react";
import Link from "next/link";
import CameraFeed, { CameraFeedHandle } from "@/components/CameraFeed";
import { captureFrames } from "@/lib/camera";
import * as api from "@/lib/api";

const REQUIRED_FRAMES = 5;

export default function RegisterPage() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const cameraRef = useRef<CameraFeedHandle>(null);
  const [name, setName] = useState("");
  const [status, setStatus] = useState<"idle" | "capturing" | "uploading" | "done" | "error">("idle");
  const [message, setMessage] = useState("");
  const [userId, setUserId] = useState("");

  async function handleRegister() {
    if (!name.trim()) { setMessage("İsim girin."); return; }
    setStatus("capturing");
    setMessage(`${REQUIRED_FRAMES} kare yakalanıyor…`);

    // CameraFeed'in arkasındaki video elementine ulaş
    const videoEl = document.querySelector("video") as HTMLVideoElement | null;
    if (!videoEl) { setMessage("Kamera hazır değil."); setStatus("error"); return; }

    const frames = await captureFrames(videoEl, REQUIRED_FRAMES, 400);
    if (frames.length < REQUIRED_FRAMES) {
      setMessage(`Yeterli kare yakalanamadı (${frames.length}/${REQUIRED_FRAMES}). Işığı kontrol edin.`);
      setStatus("error");
      return;
    }

    setStatus("uploading");
    setMessage("Kaydediliyor…");
    try {
      const res = await api.register({ name: name.trim(), frames });
      setUserId(res.user_id ?? "");
      setMessage(res.message);
      setStatus("done");
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Kayıt başarısız");
      setStatus("error");
    }
  }

  return (
    <main className="min-h-screen bg-gray-950 text-white flex flex-col items-center justify-center p-6 gap-6">
      <Link href="/" className="self-start text-gray-400 hover:text-white text-sm">← Geri</Link>
      <h1 className="text-2xl font-bold">Yeni Kullanıcı Kaydı</h1>

      {status !== "done" && (
        <>
          <CameraFeed ref={cameraRef} className="w-80 h-60" />
          <div className="flex flex-col gap-3 w-full max-w-xs">
            <input
              type="text"
              placeholder="Adınızı girin"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="px-4 py-3 bg-gray-800 border border-gray-600 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
            />
            {message && (
              <p className={`text-sm text-center ${status === "error" ? "text-red-400" : "text-gray-400"}`}>
                {message}
              </p>
            )}
            <button
              onClick={handleRegister}
              disabled={status === "capturing" || status === "uploading"}
              className="px-6 py-3 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-xl font-medium transition"
            >
              {status === "capturing" ? "Kare yakalanıyor…" : status === "uploading" ? "Kaydediliyor…" : "Kaydet"}
            </button>
          </div>
        </>
      )}

      {status === "done" && (
        <div className="flex flex-col items-center gap-4 text-center">
          <p className="text-5xl">✅</p>
          <p className="text-xl font-bold">Kayıt Başarılı</p>
          <p className="text-gray-300">{name} sisteme eklendi.</p>
          {userId && <p className="text-gray-500 text-xs">ID: {userId}</p>}
          <div className="flex gap-3 mt-2">
            <button
              onClick={() => { setStatus("idle"); setName(""); setMessage(""); setUserId(""); }}
              className="px-5 py-2 bg-gray-700 hover:bg-gray-600 rounded-xl text-sm transition"
            >
              Yeni Kayıt
            </button>
            <Link href="/verify"
              className="px-5 py-2 bg-blue-600 hover:bg-blue-700 rounded-xl text-sm transition">
              Doğrula
            </Link>
          </div>
        </div>
      )}
    </main>
  );
}
