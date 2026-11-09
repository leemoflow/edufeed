#!/usr/bin/env python3
import json, sys, re
from pathlib import Path
from datetime import date, timedelta

hist_path = Path.home() / "daylog/_youtube_history.json"
if not hist_path.exists():
    print("No _youtube_history.json — run the YouTube parser first"); sys.exit(1)
hist = json.load(open(hist_path))
days = hist["days"]

def set_field(text, field, value):
    if re.search(rf"^{field}:.*$", text, re.MULTILINE):
        return re.sub(rf"^{field}:.*$", f"{field}: {value}", text, flags=re.MULTILINE)
    m = re.match(r"^(---\n.*?\n)(---\n)", text, re.DOTALL)
    if not m: return text
    return m.group(1) + f"{field}: {value}\n" + m.group(2) + text[m.end():]

n = int(sys.argv[1]) if len(sys.argv) > 1 else 7
today = date.today()
for i in range(n):
    d = (today - timedelta(days=i)).isoformat()
    day_data = days.get(d, {"video_count": 0})
    note = Path.home() / "daylog" / f"{d}.md"
    if not note.exists(): note.write_text(f"---\ndate: {d}\n---\n\n## Notes\n\n")
    text = note.read_text()
    text = set_field(text, "youtube_videos", day_data["video_count"])
    note.write_text(text)
    print(f"{d}: {day_data['video_count']} videos")
