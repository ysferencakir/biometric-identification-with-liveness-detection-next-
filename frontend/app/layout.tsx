import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Biometric ID — Liveness Detection",
  description: "Yüz tanıma ve canlılık tespiti ile güvenli kimlik doğrulama sistemi",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="tr" className="h-full">
      <body className="min-h-full flex flex-col relative">
        {children}
      </body>
    </html>
  );
}
