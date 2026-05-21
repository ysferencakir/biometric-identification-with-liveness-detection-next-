"use client";

import Link from "next/link";
import { useState } from "react";

const ADMIN_PASSWORD = "dau2026";

type MenuItem = {
  label: string;
  desc: string;
  href: string;
  highlight?: boolean;
  dev?: boolean;
};

type MenuSection = {
  category: string;
  items: MenuItem[];
};

const MENU_ITEMS: MenuSection[] = [
  {
    category: "Kayıt & Kimlik",
    items: [
      { label: "Biyometrik Kimlik Kaydı", desc: "Yüz tanıma sistemi için profil oluştur", href: "/register", highlight: true },
      { label: "Öğrenci Kimlik Kartı", desc: "Kayıp / yenileme başvurusu", href: "#" },
      { label: "Adres Güncelleme", desc: "İletişim ve ikamet bilgilerini düzenle", href: "#" },
    ],
  },
  {
    category: "Akademik İşlemler",
    items: [
      { label: "Ders Kayıt", desc: "Dönem ders seçimi ve onay", href: "#" },
      { label: "Transkript Talebi", desc: "Resmi not belgesi oluştur", href: "#" },
      { label: "Mezuniyet Başvurusu", desc: "Mezuniyet koşullarını kontrol et", href: "#" },
    ],
  },
  {
    category: "Mali İşlemler",
    items: [
      { label: "Harç Ödeme", desc: "Dönem ücreti ve burs sorgulama", href: "#" },
      { label: "Burs Başvurusu", desc: "Mevcut burs programlarına başvur", href: "#" },
    ],
  },
  {
    category: "Sistem & Destek",
    items: [
      { label: "Liveness Modül Testi", desc: "Biyometrik sistem geliştirici arayüzü", href: "/test-ui", dev: true },
    ],
  },
];

export default function OgrenciIsleriPage() {
  const [password, setPassword] = useState("");
  const [authenticated, setAuthenticated] = useState(false);
  const [error, setError] = useState(false);

  function handleLogin(e: React.SyntheticEvent) {
    e.preventDefault();
    if (password === ADMIN_PASSWORD) {
      setAuthenticated(true);
      setError(false);
    } else {
      setError(true);
      setPassword("");
    }
  }

  if (!authenticated) {
    return (
      <main className="min-h-screen flex items-center justify-center p-4"
        style={{ background: "linear-gradient(135deg, #0d1b2e 0%, #0b1628 50%, #0d1f35 100%)" }}>
        <div className="w-full max-w-sm flex flex-col gap-6 p-8 rounded-2xl"
          style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)" }}>

          <div className="flex flex-col items-center gap-3 text-center">
            <div className="w-12 h-12 rounded-full flex items-center justify-center"
              style={{ background: "rgba(59,130,246,0.12)", border: "1px solid rgba(59,130,246,0.3)" }}>
              <svg className="w-6 h-6 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round"
                  d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z" />
              </svg>
            </div>
            <div>
              <p className="text-xs font-semibold tracking-widest uppercase mb-1" style={{ color: "var(--text-muted)" }}>
                Doğu Akdeniz Üniversitesi
              </p>
              <h1 className="text-lg font-bold" style={{ color: "var(--text-primary)" }}>Öğrenci İşleri</h1>
              <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
                Bu alana yalnızca yetkili personel erişebilir.
              </p>
            </div>
          </div>

          <form onSubmit={handleLogin} className="flex flex-col gap-3">
            <input
              type="password"
              placeholder="Personel şifresi"
              value={password}
              onChange={(e) => { setPassword(e.target.value); setError(false); }}
              className="w-full px-4 py-3 rounded-xl text-sm outline-none"
              style={{
                background: "rgba(255,255,255,0.05)",
                border: `1px solid ${error ? "rgba(239,68,68,0.6)" : "rgba(255,255,255,0.1)"}`,
                color: "var(--text-primary)",
              }}
              autoFocus
            />
            {error && (
              <p className="text-xs text-center" style={{ color: "#ef4444" }}>
                Şifre hatalı. Yetkisiz erişim denendi.
              </p>
            )}
            <button type="submit"
              className="w-full py-3 rounded-xl text-sm font-semibold text-white transition-all duration-200 hover:opacity-90"
              style={{ background: "linear-gradient(135deg, #1d4ed8, #2563eb)" }}>
              Giriş Yap
            </button>
          </form>

          <Link href="/"
            className="text-xs text-center transition-all hover:underline"
            style={{ color: "rgba(148,163,184,0.4)" }}>
            ← Öğrenci girişine dön
          </Link>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen p-6 md:p-10"
      style={{ background: "linear-gradient(135deg, #0d1b2e 0%, #0b1628 50%, #0d1f35 100%)" }}>

      <div className="max-w-4xl mx-auto mb-8 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full flex items-center justify-center"
            style={{ background: "rgba(59,130,246,0.15)", border: "1px solid rgba(59,130,246,0.3)" }}>
            <svg className="w-5 h-5 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round"
                d="M12 21v-8.25M15.75 21v-8.25M8.25 21v-8.25M3 9l9-6 9 6m-1.5 12V10.332A48.36 48.36 0 0012 9.75c-2.551 0-5.056.2-7.5.582V21" />
            </svg>
          </div>
          <div>
            <p className="text-xs font-semibold tracking-widest uppercase" style={{ color: "var(--text-muted)" }}>
              Doğu Akdeniz Üniversitesi
            </p>
            <h1 className="text-lg font-bold" style={{ color: "var(--text-primary)" }}>Öğrenci İşleri Portalı</h1>
          </div>
        </div>
        <button
          onClick={() => setAuthenticated(false)}
          className="flex items-center gap-1.5 text-sm px-4 py-2 rounded-lg transition-all duration-200 hover:bg-white/5"
          style={{ color: "var(--text-muted)", border: "1px solid rgba(255,255,255,0.08)" }}>
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round"
              d="M15.75 9V5.25A2.25 2.25 0 0013.5 3h-6a2.25 2.25 0 00-2.25 2.25v13.5A2.25 2.25 0 007.5 21h6a2.25 2.25 0 002.25-2.25V15m3 0l3-3m0 0l-3-3m3 3H9" />
          </svg>
          Çıkış
        </button>
      </div>

      <div className="max-w-4xl mx-auto flex flex-col gap-8">
        {MENU_ITEMS.map((section) => (
          <div key={section.category}>
            <p className="text-xs font-semibold tracking-widest uppercase mb-3" style={{ color: "var(--text-muted)" }}>
              {section.category}
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
              {section.items.map((item) => (
                <Link key={item.label} href={item.href}
                  className="group flex flex-col gap-1.5 p-4 rounded-xl transition-all duration-200 hover:scale-[1.02]"
                  style={{
                    background: item.highlight
                      ? "linear-gradient(135deg, rgba(29,78,216,0.35), rgba(37,99,235,0.2))"
                      : "rgba(255,255,255,0.03)",
                    border: item.highlight
                      ? "1px solid rgba(59,130,246,0.4)"
                      : "1px solid rgba(255,255,255,0.07)",
                    opacity: item.href === "#" ? 0.5 : 1,
                    pointerEvents: item.href === "#" ? "none" : "auto",
                  }}>
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-semibold"
                      style={{ color: item.highlight ? "#93c5fd" : "var(--text-primary)" }}>
                      {item.label}
                    </span>
                    {item.dev && (
                      <span className="text-xs px-1.5 py-0.5 rounded font-mono"
                        style={{ background: "rgba(16,185,129,0.15)", color: "#34d399" }}>
                        DEV
                      </span>
                    )}
                    {item.highlight && (
                      <svg className="w-4 h-4 text-blue-400 group-hover:translate-x-0.5 transition-transform"
                        fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
                      </svg>
                    )}
                  </div>
                  <p className="text-xs" style={{ color: "var(--text-muted)" }}>{item.desc}</p>
                </Link>
              ))}
            </div>
          </div>
        ))}
      </div>

      <p className="text-center text-xs mt-12" style={{ color: "rgba(148,163,184,0.25)" }}>
        BLGM 405 · Biometric Identification with Liveness Detection · 2025–2026
      </p>
    </main>
  );
}
