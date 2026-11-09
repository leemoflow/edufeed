#!/usr/bin/env python3
import sys, re
from pathlib import Path
from datetime import date

if len(sys.argv) != 3:
    print("Usage: customlog <field> <value>"); sys.exit(1)

field, value = sys.argv[1], sys.argv[2]
p = Path.home() / "daylog" / f"{date.today()}.md"
text = p.read_text() if p.exists() else f"---\ndate: {date.today()}\n---\n\n## Notes\n\n"

m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.DOTALL)
if not m: print("No frontmatter"); sys.exit(1)
fm, body = m.group(1), m.group(2)

lines = fm.split("\n")
found = False
for i, line in enumerate(lines):
    if line.startswith(f"{field}:"):
        lines[i] = f"{field}: {value}"; found = True; break
if not found: lines.append(f"{field}: {value}")

p.write_text("---\n" + "\n".join(lines) + "\n---\n" + body)
print(f"Set {field} = {value} in {p}")
