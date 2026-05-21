import Link from "next/link";
import Image from "next/image";
import { ThemeToggle } from "@/components/ThemeProvider";

export default function Home() {
  return (
    <main className="min-h-screen flex items-center justify-center p-4 relative"
      style={{ background: "linear-gradient(135deg, var(--bg-base) 0%, var(--bg-surface) 100%)" }}>

      {/* Tema toggle — sağ üst */}
      <div className="absolute top-4 right-4 z-20">
        <ThemeToggle />
      </div>

      <div className="w-full max-w-4xl flex rounded-2xl overflow-hidden shadow-2xl"
        style={{ background: "var(--bg-surface)", border: "1px solid var(--border)", minHeight: 480 }}>

        {/* SOL — Giriş Paneli */}
        <div className="flex-1 flex flex-col items-center justify-center p-10 gap-7"
          style={{ borderRight: "1px solid var(--border)" }}>

          {/* Logo */}
          <div className="flex flex-col items-center gap-4">
            <div className="w-24 h-24 relative">
              <Image src="/emu-dau-logo.png" alt="DAÜ Logo" fill className="object-contain" priority />
            </div>
            <div className="text-center">
              <p className="text-xs font-semibold tracking-widest uppercase mb-1"
                style={{ color: "var(--text-muted)" }}>
                Doğu Akdeniz Üniversitesi
              </p>
              <h1 className="text-xl font-bold" style={{ color: "var(--text-primary)" }}>
                Öğrenci Portalı
              </h1>
            </div>
          </div>

          {/* Ana Giriş Butonu */}
          <Link href="/verify"
            className="w-full flex items-center justify-center gap-3 py-4 px-6 rounded-xl font-semibold text-white transition-all duration-200 hover:scale-[1.02] active:scale-[0.98]"
            style={{
              background: "linear-gradient(135deg, #1a3a6b 0%, #1d4ed8 100%)",
              boxShadow: "0 4px 20px rgba(29,78,216,0.35)",
            }}>
            <svg className="w-5 h-5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round"
                d="M7.864 4.243A7.5 7.5 0 0119.5 10.5c0 2.92-.556 5.709-1.568 8.268M5.742 6.364A7.465 7.465 0 004.5 10.5a7.464 7.464 0 01-1.15 3.993m1.989 3.559A11.209 11.209 0 008.25 10.5a3.75 3.75 0 117.5 0c0 .527-.021 1.049-.064 1.565M12 18.75a.75.75 0 110-1.5.75.75 0 010 1.5z" />
            </svg>
            Biometric ID ile Giriş Yap
          </Link>

          <p className="text-xs text-center" style={{ color: "var(--text-muted)" }}>
            Yüz tanıma ve canlılık tespiti ile güvenli giriş
          </p>

          {/* Ayırıcı */}
          <div className="w-full flex items-center gap-3">
            <div className="flex-1 h-px" style={{ background: "var(--border)" }} />
            <span className="text-xs" style={{ color: "var(--text-faint)" }}>veya</span>
            <div className="flex-1 h-px" style={{ background: "var(--border)" }} />
          </div>

          <Link href="/ogrenci-isleri"
            className="text-xs transition-all duration-200 hover:underline"
            style={{ color: "var(--text-faint)" }}>
            Personel / Öğrenci İşleri Girişi
          </Link>
        </div>

        {/* SAĞ — Haberler Paneli */}
        <div className="w-80 flex flex-col p-6 gap-4" style={{ background: "var(--bg-elevated)" }}>
          <div className="px-3 py-2 rounded-lg font-semibold text-sm"
            style={{ background: "rgba(29,78,216,0.15)", color: "#60a5fa" }}>
            Sistem Bilgisi
          </div>

          <div className="flex flex-col gap-3 flex-1">
            {[
              { tag: "Güvenlik", tagColor: "#f59e0b", tagBg: "rgba(245,158,11,0.15)", date: "2026",
                text: "Çift aşamalı liveness doğrulama aktif — BlinkDetector + HeadMovement" },
              { tag: "Güvenlik", tagColor: "#f59e0b", tagBg: "rgba(245,158,11,0.15)", date: "2026",
                text: "TextureAnalyzer (FFT + LBP + Glare) ile sahte saldırı koruması güncellendi" },
              { tag: "Sistem",   tagColor: "#10b981", tagBg: "rgba(16,185,129,0.15)", date: "2026",
                text: "MediaPipe Face Landmarker entegrasyonu tamamlandı — 478 nokta hassasiyeti" },
              { tag: "Bilgi",    tagColor: "#94a3b8", tagBg: "rgba(148,163,184,0.1)", date: "2026",
                text: "BLGM 405 — Biometric Identification with Liveness Detection projesi" },
              { tag: "Bilgi",    tagColor: "#94a3b8", tagBg: "rgba(148,163,184,0.1)", date: "2025",
                text: "InsightFace ArcFace modeli ile yüz tanıma başarım oranı %99.1" },
            ].map((item, i) => (
              <div key={i} className="flex flex-col gap-1 py-3"
                style={{ borderBottom: "1px solid var(--border)" }}>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold px-2 py-0.5 rounded"
                    style={{ background: item.tagBg, color: item.tagColor }}>
                    {item.tag}
                  </span>
                  <span className="text-xs" style={{ color: "var(--text-faint)" }}>{item.date}</span>
                </div>
                <p className="text-xs leading-relaxed" style={{ color: "var(--text-primary)", opacity: 0.85 }}>
                  {item.text}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </main>
  );
}
