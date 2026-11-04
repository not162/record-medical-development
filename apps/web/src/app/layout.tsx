import type { Metadata, Viewport } from "next";
import { Plus_Jakarta_Sans, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Providers } from "@/lib/providers";
import { PwaRegistration } from "@/components/PwaRegistration";
import BrandLoader from "@/components/BrandLoader";
import { THEME_INIT_SCRIPT } from "@/components/ThemeToggle";

const jakarta = Plus_Jakarta_Sans({
  variable: "--font-jakarta",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700", "800"],
  display: "swap",
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
  display: "swap",
});

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#2563eb" },
    { media: "(prefers-color-scheme: dark)", color: "#070b16" },
  ],
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL || "https://klinik-terpadu.vercel.app"),
  title: {
    default: "Web Klinik RSUKT | healthy with clinic and hospital",
    template: "%s | Web Klinik RSUKT",
  },
  description: "Web Klinik RSUKT: tanya seputar kesehatan dengan asisten AI, kapan saja.",
  manifest: "/manifest.json",
  appleWebApp: {
    capable: true,
    statusBarStyle: "default",
    title: "Web Klinik",
  },
  icons: {
    icon: [
      { url: "/icons/icon-192.png", sizes: "192x192", type: "image/png" },
      { url: "/icons/icon-512.png", sizes: "512x512", type: "image/png" },
    ],
    apple: "/icons/apple-touch-icon.png",
  },
  openGraph: {
    title: "Web Klinik RSUKT | Asisten Kesehatan AI",
    description: "Tanya seputar kesehatan dengan asisten AI, kapan saja.",
    url: "/",
    siteName: "Web Klinik RSUKT",
    locale: "id_ID",
    type: "website",
  },
  robots: {
    index: true,
    follow: true,
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="id" className={`${jakarta.variable} ${geistMono.variable} h-full antialiased`} suppressHydrationWarning>
      <head>
        {/* Terapkan tema sebelum render pertama agar tidak berkedip */}
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />
      </head>
      <body className="min-h-full flex flex-col bg-slate-50 text-slate-800 font-sans selection:bg-blue-600 selection:text-white">
        <Providers>
          <BrandLoader />
          <PwaRegistration />
          {children}
        </Providers>
        {/* 3.3 Structured Data (Schema.org / MedicalOrganization) */}
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify({
              "@context": "https://schema.org",
              "@type": "MedicalOrganization",
              "name": "Web Klinik RSUKT",
              "url": "https://klinik-terpadu.vercel.app",
              "logo": "https://klinik-terpadu.vercel.app/icons/icon-512.png",
              "slogan": "healthy with clinic and hospital",
              "description": "Layanan Konsultasi Triase Medis Berbasis Kecerdasan Artifisial & Rekam Medis Terverifikasi RSUKT",
              "address": {
                "@type": "PostalAddress",
                "addressCountry": "ID"
              },
              "medicalSpecialty": [
                "EmergencyMedicine",
                "Cardiovascular",
                "InternalMedicine"
              ]
            })
          }}
        />
      </body>
    </html>
  );
}
