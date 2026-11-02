import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Providers } from "@/lib/providers";
import { PwaRegistration } from "@/components/PwaRegistration";
import BrandLoader from "@/components/BrandLoader";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
  display: "swap",
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
  display: "swap",
});

export const viewport: Viewport = {
  themeColor: "#0891b2",
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL || "https://klinik.rsukt.go.id"),
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
    apple: "/icons/icon-192.png",
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
    <html lang="id" className={`${geistSans.variable} ${geistMono.variable} h-full antialiased light`}>
      <body className="min-h-full flex flex-col bg-slate-50 text-slate-800 selection:bg-cyan-600 selection:text-white">
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
              "url": "https://klinik.rsukt.go.id",
              "logo": "https://klinik.rsukt.go.id/icons/icon-512.png",
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
