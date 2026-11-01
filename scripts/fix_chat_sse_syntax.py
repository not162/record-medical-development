path = r"services/ai-api/app/routes/chat.py"
with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
skip_next = 0
for i, line in enumerate(lines):
    if skip_next > 0:
        skip_next -= 1
        continue
    # If line starts with yield f"data: and is broken
    if 'yield f"data: ' in line and not line.rstrip().endswith(('\\n\\n"', ')\n', ')\\n\\n"')):
        # Check if next lines are quotes
        combined = line.rstrip()
        lookahead = 1
        while lookahead < 4 and i + lookahead < len(lines):
            next_l = lines[i + lookahead]
            if next_l.strip() in ('"', '""', "'''"):
                skip_next = lookahead
                combined += '\\n\\n"'
                break
            lookahead += 1
        new_lines.append(combined + "\n")
    else:
        new_lines.append(line)

with open(path, "w", encoding="utf-8") as f:
    f.writelines(new_lines)

# Re-read and check compilation
with open(path, "r", encoding="utf-8") as f:
    code = f.read()

try:
    compile(code, path, "exec")
    print("chat.py compiled cleanly with NO syntax errors!")
except SyntaxError as e:
    print(f"SyntaxError at line {e.lineno}: {e}")
