path = r"apps/web/src/app/layout.tsx"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

# 1. Add BrandLoader import
text = text.replace(
    'import { PwaRegistration } from "@/components/PwaRegistration";',
    'import { PwaRegistration } from "@/components/PwaRegistration";\nimport BrandLoader from "@/components/BrandLoader";'
)

# 2. Add BrandLoader inside body
text = text.replace(
    '<Providers>\n          <PwaRegistration />',
    '<Providers>\n          <BrandLoader />\n          <PwaRegistration />'
)

# 3. Add JSON-LD schema
json_ld = """        {/* 3.3 Structured Data (Schema.org / MedicalOrganization) */}
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
"""

text = text.replace('      </body>', json_ld + '      </body>')

with open(path, "w", encoding="utf-8") as f:
    f.write(text)

print("layout.tsx updated with BrandLoader and Schema.org JSON-LD!")
