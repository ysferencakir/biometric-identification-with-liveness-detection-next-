import Link from "next/link";

export default function Home() {
  return (
    <main className="min-h-screen flex flex-col items-center justify-center bg-gray-950 text-white gap-8 p-8">
      <div className="text-center">
        <h1 className="text-3xl font-bold mb-2">Biometric Identification</h1>
        <p className="text-gray-400 text-sm">Liveness Detection ile Güvenli Kimlik Doğrulama</p>
      </div>

      <div className="flex flex-col gap-4 w-full max-w-xs">
        <Link
          href="/verify"
          className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-center font-medium transition"
        >
          Kimlik Doğrula
        </Link>
        <Link
          href="/register"
          className="px-6 py-3 bg-gray-700 hover:bg-gray-600 text-white rounded-xl text-center font-medium transition"
        >
          Yeni Kullanıcı Kaydı
        </Link>
        <Link
          href="/test-ui"
          className="px-6 py-3 border border-gray-600 hover:border-gray-400 text-gray-300 rounded-xl text-center text-sm transition"
        >
          🔬 Liveness Modül Testi
        </Link>
      </div>
    </main>
  );
}
