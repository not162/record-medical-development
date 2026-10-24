import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Providers } from "@/lib/providers";
import { PwaRegistration } from "@/components/PwaRegistration";
import { Analytics } from "@vercel/analytics/next";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const viewport: Viewport = {
  themeColor: "#0891b2",
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
  viewportFit: "cover",
};

export const metadata: Metadata = {
  title: "RSUKT Clinical AI Suite | Chatbot & Research Workspace",
  description: "Sistem Kecerdasan Buatan Medis Terpadu RS RSUKT: Evidence-Grounded RAG, Safety Guardrail, & Research Management",
  manifest: "/manifest.json",
  appleWebApp: {
    capable: true,
    statusBarStyle: "default",
    title: "RSUKT AI",
  },
  icons: {
    icon: "/icons/icon-192.png",
    apple: "/icons/icon-192.png",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="id" className={`${geistSans.variable} ${geistMono.variable} h-full antialiased light`}>
      <body className="min-h-full flex flex-col bg-slate-50 text-slate-800 selection:bg-cyan-600 selection:text-white">
        <Providers>
          <PwaRegistration />
          {children}
        </Providers>
        <Analytics />
      </body>
    </html>
  );
}
