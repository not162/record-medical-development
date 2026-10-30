import urllib.request
import re

scripts = [
  "/_next/static/immutable/chunks/3nmkkg8hnh-c4.js",
  "/_next/static/immutable/chunks/42oqdbmkmpoww.js",
  "/_next/static/immutable/chunks/1p3b6wylffo5h.js",
  "/_next/static/immutable/chunks/turbopack-1cvbnb3nlabgn.js",
  "/_next/static/immutable/chunks/01rliffuq2x_-.js",
  "/_next/static/immutable/chunks/3vlyk0_ucxnmi.js",
  "/_next/static/immutable/chunks/1acldsx504dny.js",
  "/_next/static/immutable/chunks/0c0hxoamwjsbw.js",
  "/_next/static/immutable/chunks/3fc8vsu2nqg09.js"
]

for s in scripts:
    url = f"https://halo-skut.vercel.app{s}"
    content = urllib.request.urlopen(url).read().decode("utf-8")
    if "auth/login" in content or "API_BASE_URL" in content or "/api/v1" in content:
        print(f"Found matches in {s}:")
        for match in re.finditer(r".{0,50}(?:auth/login|/api/v1).{0,50}", content):
            print("  ...", match.group(0), "...")

