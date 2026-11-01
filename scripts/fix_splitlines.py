path = r"services/ai-api/app/routes/chat.py"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

# Replace broken multi-line split
bad_block = '''    if session.title == "Konsultasi Klinis Baru":
        snippet = clean_content.split("
")[0][:45]'''

good_block = '''    if session.title == "Konsultasi Klinis Baru":
        snippet = clean_content.splitlines()[0][:45]'''

if bad_block in text:
    text = text.replace(bad_block, good_block)
    print("Replaced bad block 1")
else:
    # Try normalized
    text = text.replace('clean_content.split("\n")', 'clean_content.splitlines()')
    text = text.replace('clean_content.split("\r\n")', 'clean_content.splitlines()')

# Also check session upgrade snippet
text = text.replace('req.messages[0]["content"].strip().split("\n")[0][:40]', 'req.messages[0]["content"].strip().splitlines()[0][:40]')
text = text.replace('req.messages[0]["content"].strip().split("\r\n")[0][:40]', 'req.messages[0]["content"].strip().splitlines()[0][:40]')

with open(path, "w", encoding="utf-8") as f:
    f.write(text)

print("chat.py string syntax fixed!")
