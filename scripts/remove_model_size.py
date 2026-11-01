path = r"apps/web/src/app/chat/page.tsx"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

target = '  const modelSize = reasoningMode === "thinking" ? "70b" : "8b";\n'
if target in text:
    text = text.replace(target, '')
else:
    target_crlf = '  const modelSize = reasoningMode === "thinking" ? "70b" : "8b";\r\n'
    text = text.replace(target_crlf, '')

with open(path, "w", encoding="utf-8") as f:
    f.write(text)

print("modelSize cleaned!")
