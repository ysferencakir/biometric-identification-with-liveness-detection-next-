import Link from "next/link";

export default function Home() {
  return (
    <main className="relative min-h-screen flex flex-col items-center justify-center p-8 z-10">

      {/* Logo + Başlık */}
      <div className="text-center mb-12 slide-up">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl mb-6"
          style={{ background: "var(--accent-glow)", border: "1px solid rgba(59,130,246,0.3)" }}>
          <svg className="w-8 h-8 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round"
              d="M7.864 4.243A7.5 7.5 0 0119.5 10.5c0 2.92-.556 5.709-1.568 8.268M5.742 6.364A7.465 7.465 0 004.5 10.5a7.464 7.464 0 01-1.15 3.993m1.989 3.559A11.209 11.209 0 008.25 10.5a3.75 3.75 0 117.5 0c0 .527-.021 1.049-.064 1.565" />
          </svg>
        </div>
        <h1 className="text-4xl font-bold tracking-tight mb-3" style={{ color: "var(--text-primary)" }}>
          Biometric ID
        </h1>
        <p className="text-lg max-w-md mx-auto leading-relaxed" style={{ color: "var(--text-muted)" }}>
          Liveness detection ile güçlendirilmiş güvenli kimlik doğrulama
        </p>
      </div>

      {/* Kartlar */}
      <div className="w-full max-w-sm flex flex-col gap-3 slide-up">

        <Link href="/verify"
          className="group flex items-center gap-4 p-4 rounded-2xl transition-all duration-200"
          style={{
            background: "var(--accent)",
            boxShadow: "0 4px 24px var(--accent-glow)",
          }}>
          <div className="w-10 h-10 rounded-xl bg-white/20 flex items-center justify-center flex-shrink-0">
            <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div>
            <p className="font-semibold text-white">Kimlik Doğrula</p>
            <p className="text-sm text-blue-100">Liveness + Yüz tanıma</p>
          </div>
          <svg className="w-5 h-5 text-white/70 ml-auto group-hover:translate-x-1 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
          </svg>
        </Link>

        <Link href="/register"
          className="group flex items-center gap-4 p-4 rounded-2xl transition-all duration-200"
          style={{ background: "var(--bg-surface)", border: "1px solid var(--border)" }}>
          <div className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0"
            style={{ background: "var(--bg-elevated)" }}>
            <svg className="w-5 h-5 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M19 7.5v3m0 0v3m0-3h3m-3 0h-3m-2.25-4.125a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0zM4 19.235v-.11a6.375 6.375 0 0112.75 0v.109A12.318 12.318 0 0110.374 21c-2.331 0-4.512-.645-6.374-1.766z" />
            </svg>
          </div>
          <div>
            <p className="font-semibold" style={{ color: "var(--text-primary)" }}>Kullanıcı Kaydı</p>
            <p className="text-sm" style={{ color: "var(--text-muted)" }}>Yeni profil oluştur</p>
          </div>
          <svg className="w-5 h-5 ml-auto group-hover:translate-x-1 transition-transform" style={{ color: "var(--text-muted)" }} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
          </svg>
        </Link>

        <Link href="/test-ui"
          className="group flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200"
          style={{ color: "var(--text-muted)", border: "1px solid var(--border)" }}>
          <span className="text-sm">🔬 Liveness Modül Testi</span>
          <svg className="w-4 h-4 ml-auto group-hover:translate-x-1 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
          </svg>
        </Link>
      </div>

      {/* Alt bilgi */}
      <div className="mt-16 text-center">
        <p className="text-xs" style={{ color: "var(--text-muted)" }}>
          BLGM 405 · Biometric Identification with Liveness Detection · 2025-2026
        </p>
      </div>
    </main>
  );
}
