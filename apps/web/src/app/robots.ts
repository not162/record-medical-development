import type { MetadataRoute } from "next";

export default function robots(): MetadataRoute.Robots {
  const baseUrl = process.env.NEXT_PUBLIC_SITE_URL || "https://klinik.rsukt.go.id";

  return {
    rules: [
      {
        userAgent: "*",
        allow: ["/", "/chat", "/login", "/register", "/forgot-password"],
        disallow: ["/admin/", "/api/"],
      },
    ],
    sitemap: `${baseUrl}/sitemap.xml`,
  };
}
