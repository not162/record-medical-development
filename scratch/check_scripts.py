import urllib.request
import re

req = urllib.request.Request("https://halo-skut.vercel.app/login", headers={"User-Agent": "Mozilla/5.0"})
html = urllib.request.urlopen(req).read().decode("utf-8")
scripts = re.findall(r'src="([^"]+\.js)"', html)
print("Found scripts:", len(scripts))
for s in scripts:
    print(" ", s)

