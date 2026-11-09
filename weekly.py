#!/usr/bin/env python3
import sys, os, subprocess, time
from pathlib import Path
from datetime import date, timedelta

DAYLOG = Path.home() / "daylog"
DAYS = int(sys.argv[1]) if len(sys.argv) > 1 else 14
cutoff = date.today() - timedelta(days=DAYS)
print(f"Cutoff: {cutoff}", flush=True)

print("Syncing YouTube...", flush=True)
sync = DAYLOG / "sync_youtube.py"
if sync.exists():
    try:
        subprocess.run([sys.executable, str(sync), str(DAYS)],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
        print("  done", flush=True)
    except subprocess.TimeoutExpired:
        print("  timed out, continuing", flush=True)

print("Collecting data...", flush=True)
real_days = []
for f in sorted(DAYLOG.glob("*.md")):
    try:
        fdate = date.fromisoformat(f.stem)
    except ValueError:
        continue
    if fdate < cutoff:
        continue
    try:
        text = f.read_text()
    except Exception:
        continue
    if "deep_work_hours:" in text or "sleep_quality:" in text:
        real_days.append((f.stem, text))
        print(f"  added: {f.stem}", flush=True)

print(f"{len(real_days)} days with real data", flush=True)

if len(real_days) < 3:
    print()
    print(f"Need at least 3 days. You have {len(real_days)}.")
    print("Log daily:")
    print("  dlog sleep_quality 3")
    print("  dlog deep_work_hours 2.5")
    print("Re-run: weekly 14")
    sys.exit(0)

combined = "\n".join(f"--- {d} ---\n{t}" for d, t in real_days)

print("Starting AI...", flush=True)
env = {**os.environ, "OLLAMA_FLASH_ATTENTION": "1", "OLLAMA_KV_CACHE_TYPE": "q8_0"}
server = subprocess.Popen(["ollama", "serve"], env=env,
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(4)

prompt = """Analyze logs. 3 questions, under 150 words.
RULES: Only cite visible numbers. No fabricated averages. Missing fields -> insufficient data. Claims about this person are UNPROVEN.
(a) Pattern linking sleep_quality, energy, steps.
(b) Highest deep_work_hours day, and what preceded it.
(c) ONE change to test next week."""

try:
    result = subprocess.run(
        ["ollama", "run", "llama3.2", "--temperature", "0.2", prompt],
        input=combined, text=True, capture_output=True, timeout=180
    )
    print(result.stdout)
finally:
    server.terminate()
    try: server.wait(timeout=5)
    except Exception: server.kill()

print("")
print("DONE")
