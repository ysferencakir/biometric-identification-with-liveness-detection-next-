"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import Image from "next/image";
import { ThemeToggle } from "@/components/ThemeProvider";

const NAV_ITEMS = [
  { label: "Anasayfa",             icon: "M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" },
  { label: "Kişisel Bilgi",        icon: "M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" },
  { label: "Akademik",             icon: "M12 14l9-5-9-5-9 5 9 5zm0 0l6.16-3.422a12.083 12.083 0 01.665 6.479A11.952 11.952 0 0012 20.055a11.952 11.952 0 00-6.824-2.998 12.078 12.078 0 01.665-6.479L12 14z" },
  { label: "Finansal",             icon: "M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" },
  { label: "Başvurular",           icon: "M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" },
  { label: "Akademik Takvim",      icon: "M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" },
  { label: "Akademik İletişimlerim", icon: "M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" },
];

const COURSES = [
  { code: "BLGM405", name: "Biometric Identification Systems", instructor: "PROF. DR. GÜRCÜ ÖZ" },
  { code: "BLGM344", name: "Computer Networks",               instructor: "PROF. DR. GÜRCÜ ÖZ" },
  { code: "BLGM342", name: "Client/Server Programming",       instructor: "DOÇ. DR. YILTAN BİTİRİM" },
  { code: "BLGM312", name: "Software Engineering",            instructor: "MAHMUT SEVİNCE" },
  { code: "BLGM404", name: "Mezuniyet Projesi – II",          instructor: "DOÇ. DR. AHMET İ." },
];

const NEWS = [
  { title: "DAÜ'de Kampüs Güvenliğine Yönel...", source: "Doğu Akdeniz Üniversitesi (DAÜ) Güvenlik...", date: "18.5.2026" },
  { title: "Öğrenci Kulüpleri Seçimleri 2–8 Haz...", source: "Doğu Akdeniz Üniversitesi (DAÜ) Öğrenci...", date: "18.5.2026" },
  { title: "DAÜ Akademisyeninden Uluslararası...", source: "Doğu Akdeniz Üniversitesi (DAÜ) akademik pla...", date: "18.5.2026" },
  { title: "FEF 2025-2026 Bahar 2. Ara Sınav Prog...", source: "Doğu Akdeniz Üniversitesi (DAÜ) FEF...", date: "14.5.2026" },
];

const EMAILS = [
  { from: "DAÜ Techgirls Bilişim ve İletişim Te...", subject: "Public Relations Announc...", date: "21.5.2026" },
  { from: "Acil Kan İhtiyacı Duyurusu",             subject: "Public Relations Announc...", date: "21.5.2026" },
  { from: "Tabldot Günün Menüleri, A'la Cart...",   subject: "Emu Postmaster",            date: "21.5.2026" },
  { from: "Ahmet ÜNVEREN mentioned Bilgiş...",      subject: "Ahmet ÜNVEREN in Teams",    date: "21.5.2026" },
];

export default function DashboardPage() {
  const router  = useRouter();
  const [name,     setName]     = useState("Öğrenci");
  const [activeNav, setActiveNav] = useState("Anasayfa");

  const applyName = useCallback((n: string) => setName(n), []);

  useEffect(() => {
    const isDev = new URLSearchParams(window.location.search).get("dev") === "1";
    const newName = isDev ? "Geliştirici" : sessionStorage.getItem("verified_user");
    if (!isDev && !newName) { router.replace("/"); return; }
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (newName) applyName(newName);
  }, [router, applyName]);

  function handleLogout() {
    sessionStorage.removeItem("verified_user");
    router.push("/");
  }

  const initials = name.split(" ").map(w => w[0]).join("").slice(0, 2).toUpperCase();

  return (
    <div className="flex min-h-screen" style={{ background: "var(--bg-base)", color: "var(--text-primary)" }}>

      {/* SIDEBAR */}
      <aside className="w-56 shrink-0 flex flex-col"
        style={{ background: "var(--bg-sidebar)", borderRight: "1px solid var(--border)" }}>

        {/* Logo */}
        <div className="flex items-center gap-3 px-5 py-4"
          style={{ borderBottom: "1px solid var(--border)" }}>
          <div className="w-10 h-10 relative shrink-0">
            <Image src="/emu-dau-logo.png" alt="DAÜ" fill className="object-contain" />
          </div>
          <span className="text-sm font-bold leading-tight" style={{ color: "#93c5fd" }}>
            Öğrenci<br />Portalı
          </span>
        </div>

        {/* Kullanıcı */}
        <div className="flex items-center gap-3 px-5 py-4"
          style={{ borderBottom: "1px solid var(--border)" }}>
          <div className="w-9 h-9 rounded-full flex items-center justify-center shrink-0 text-xs font-bold"
            style={{ background: "linear-gradient(135deg,#1d4ed8,#2563eb)", color: "white" }}>
            {initials}
          </div>
          <div className="min-w-0">
            <p className="text-xs font-bold truncate uppercase" style={{ color: "var(--text-primary)" }}>{name}</p>
            <p className="text-xs" style={{ color: "var(--text-faint)" }}>Öğrenci</p>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex flex-col gap-0.5 px-3 py-4 flex-1">
          {NAV_ITEMS.map(item => (
            <button key={item.label}
              onClick={() => setActiveNav(item.label)}
              className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-left w-full text-xs font-medium transition-all duration-150"
              style={{
                background: activeNav === item.label ? "rgba(59,130,246,0.15)" : "transparent",
                color: activeNav === item.label ? "#93c5fd" : "#94a3b8",
              }}>
              <svg className="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d={item.icon} />
              </svg>
              {item.label}
            </button>
          ))}
        </nav>

        {/* Çıkış */}
        <button onClick={handleLogout}
          className="flex items-center gap-2 px-6 py-4 text-xs transition-colors hover:text-red-400"
          style={{ color: "#64748b", borderTop: "1px solid rgba(255,255,255,0.06)" }}>
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round"
              d="M15.75 9V5.25A2.25 2.25 0 0013.5 3h-6a2.25 2.25 0 00-2.25 2.25v13.5A2.25 2.25 0 007.5 21h6a2.25 2.25 0 002.25-2.25V15M12 9l-3 3m0 0l3 3m-3-3h12.75" />
          </svg>
          Çıkış Yap
        </button>
      </aside>

      {/* MAIN */}
      <div className="flex-1 flex flex-col min-w-0">

        {/* Topbar */}
        <header className="flex items-center justify-between px-6 py-3 shrink-0"
          style={{ borderBottom: "1px solid var(--border)", background: "var(--bg-sidebar)" }}>
          <div className="flex items-center gap-3">
            <svg className="w-5 h-5" style={{ color: "var(--text-faint)" }} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
            </svg>
            <svg className="w-5 h-5" style={{ color: "var(--text-faint)" }} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>
          <div className="flex items-center gap-3">
            <Link href="/banka"
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all"
              style={{ background: "rgba(16,185,129,0.12)", color: "#34d399", border: "1px solid rgba(16,185,129,0.25)" }}>
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M3 10.5L12 3l9 7.5V20.25a.75.75 0 01-.75.75H15a.75.75 0 01-.75-.75v-4.5a.75.75 0 00-.75-.75h-3a.75.75 0 00-.75.75v4.5a.75.75 0 01-.75.75H3.75a.75.75 0 01-.75-.75V10.5z" />
              </svg>
              Banka Girişi
            </Link>
            <ThemeToggle />
            <div className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold"
              style={{ background: "linear-gradient(135deg,#1d4ed8,#2563eb)", color: "white" }}>
              {initials}
            </div>
            <button onClick={handleLogout}>
              <svg className="w-5 h-5 hover:text-red-400 transition-colors" style={{ color: "var(--text-faint)" }} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round"
                  d="M15.75 9V5.25A2.25 2.25 0 0013.5 3h-6a2.25 2.25 0 00-2.25 2.25v13.5A2.25 2.25 0 007.5 21h6a2.25 2.25 0 002.25-2.25V15M12 9l-3 3m0 0l3 3m-3-3h12.75" />
              </svg>
            </button>
          </div>
        </header>

        {/* Grid */}
        <div className="flex-1 p-5 grid grid-cols-3 gap-4 auto-rows-min overflow-auto">

          {/* Dönem Dersleri */}
          <div className="rounded-xl p-4 flex flex-col gap-3"
            style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
            <p className="text-sm font-semibold" style={{ color: "#60a5fa" }}>Dönem Dersleri</p>
            <div className="flex flex-col gap-3">
              {COURSES.map(c => (
                <div key={c.code} className="flex flex-col gap-0.5">
                  <p className="text-xs font-medium" style={{ color: "#60a5fa" }}>{c.name}</p>
                  <p className="text-xs" style={{ color: "var(--text-faint)" }}>{c.code} · {c.instructor}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Haberler */}
          <div className="rounded-xl p-4 flex flex-col gap-3"
            style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
            <p className="text-sm font-semibold" style={{ color: "#60a5fa" }}>Haberler</p>
            <div className="flex flex-col gap-3">
              {NEWS.map((n, i) => (
                <div key={i} className="flex flex-col gap-0.5">
                  <div className="flex items-start justify-between gap-2">
                    <p className="text-xs font-medium leading-snug" style={{ color: "var(--text-primary)" }}>{n.title}</p>
                    <span className="text-xs shrink-0" style={{ color: "var(--text-faint)" }}>{n.date}</span>
                  </div>
                  <p className="text-xs" style={{ color: "var(--text-faint)" }}>{n.source}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Başvurular */}
          <div className="rounded-xl p-4 flex flex-col gap-3"
            style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
            <p className="text-sm font-semibold" style={{ color: "#60a5fa" }}>Başvurular</p>
            <p className="text-xs" style={{ color: "var(--text-faint)" }}>Aktif başvuru bulunmamaktadır.</p>
          </div>

          {/* E-postam */}
          <div className="rounded-xl p-4 flex flex-col gap-3"
            style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
            <p className="text-sm font-semibold" style={{ color: "#60a5fa" }}>E-postam</p>
            <div className="flex flex-col gap-3">
              {EMAILS.map((e, i) => (
                <div key={i} className="flex items-start gap-3">
                  <div className="w-7 h-7 rounded flex items-center justify-center shrink-0"
                    style={{ background: "rgba(59,130,246,0.15)" }}>
                    <svg className="w-3.5 h-3.5 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                    </svg>
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-xs truncate" style={{ color: "var(--text-muted)" }}>{e.from}</p>
                    <p className="text-xs font-medium truncate" style={{ color: "#60a5fa" }}>{e.subject}</p>
                  </div>
                  <span className="text-xs shrink-0" style={{ color: "var(--text-faint)" }}>{e.date}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Academic Status */}
          <div className="rounded-xl p-4 flex flex-col gap-3"
            style={{ background: "var(--bg-card)", border: "1px solid rgba(59,130,246,0.3)" }}>
            <div className="flex items-start justify-between">
              <p className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>Academic Status</p>
              <div className="text-right">
                <p className="text-xs" style={{ color: "var(--text-muted)" }}>CGPA</p>
                <p className="text-2xl font-bold" style={{ color: "var(--text-primary)" }}>—</p>
              </div>
            </div>
            <p className="text-xs" style={{ color: "var(--text-muted)" }}>Danışman: —</p>
            <span className="self-start text-xs px-2 py-0.5 rounded font-semibold"
              style={{ background: "rgba(16,185,129,0.2)", color: "#34d399" }}>
              AKTİF ÖĞRENCİ
            </span>
          </div>

          {/* Finansal */}
          <div className="rounded-xl p-4 flex flex-col gap-3"
            style={{ background: "var(--bg-card)", border: "1px solid rgba(239,68,68,0.3)" }}>
            <p className="text-sm font-semibold" style={{ color: "var(--danger)" }}>Finansal Durum</p>
            {[
              { label: "Geçmiş Borç", value: "—" },
              { label: "Yurt Borç",   value: "—" },
              { label: "Dönem Borcu", value: "—" },
            ].map(item => (
              <div key={item.label}>
                <p className="text-xs" style={{ color: "var(--text-muted)" }}>{item.label}</p>
                <p className="text-sm font-bold" style={{ color: "var(--text-primary)" }}>{item.value}</p>
              </div>
            ))}
          </div>

        </div>
      </div>
    </div>
  );
}
