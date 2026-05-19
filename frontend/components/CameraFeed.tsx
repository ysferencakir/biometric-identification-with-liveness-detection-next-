"use client";

import { useEffect, useRef, useState, useCallback, forwardRef, useImperativeHandle } from "react";
import { startCamera, stopCamera, captureFrame } from "@/lib/camera";

export interface CameraFeedHandle {
  capture: () => string | null;
}

interface CameraFeedProps {
  /** Aktif kamera akışı başladığında tetiklenir. */
  onReady?: () => void;
  /** Kamera izni reddedildi veya başlatma hatası oluştu. */
  onError?: (msg: string) => void;
  className?: string;
}

const CameraFeed = forwardRef<CameraFeedHandle, CameraFeedProps>(
  ({ onReady, onError, className = "" }, ref) => {
    const videoRef = useRef<HTMLVideoElement>(null);
    const streamRef = useRef<MediaStream | null>(null);
    const [status, setStatus] = useState<"idle" | "loading" | "active" | "error">("idle");
    const [errorMsg, setErrorMsg] = useState("");

    // Parent bileşen capture() çağırabilir
    useImperativeHandle(ref, () => ({
      capture: () => (videoRef.current ? captureFrame(videoRef.current) : null),
    }));

    const start = useCallback(async () => {
      if (!videoRef.current) return;
      setStatus("loading");
      try {
        const stream = await startCamera(videoRef.current);
        streamRef.current = stream;
        setStatus("active");
        onReady?.();
      } catch (err) {
        const msg =
          err instanceof Error ? err.message : "Kameraya erişilemiyor";
        setErrorMsg(msg);
        setStatus("error");
        onError?.(msg);
      }
    }, [onReady, onError]);

    useEffect(() => {
      start();
      return () => stopCamera(streamRef.current);
    }, [start]);

    return (
      <div className={`relative overflow-hidden rounded-xl bg-gray-900 ${className}`}>
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          className="w-full h-full object-cover scale-x-[-1]" // ayna görünümü
        />

        {status === "loading" && (
          <div className="absolute inset-0 flex items-center justify-center bg-gray-900/80">
            <span className="text-white text-sm animate-pulse">Kamera başlatılıyor…</span>
          </div>
        )}

        {status === "error" && (
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-gray-900/90 gap-3 p-4">
            <span className="text-red-400 text-sm text-center">{errorMsg}</span>
            <button
              onClick={start}
              className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition"
            >
              Tekrar Dene
            </button>
          </div>
        )}

        {/* Yüz kılavuz çerçevesi */}
        {status === "active" && (
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
            <div className="w-48 h-56 border-2 border-dashed border-white/40 rounded-full" />
          </div>
        )}
      </div>
    );
  }
);

CameraFeed.displayName = "CameraFeed";
export default CameraFeed;
