#!/bin/zsh
DAYLOG=~/daylog
DAYS=${1:-14}
CUTOFF=$(date -v-${DAYS}d +%Y-%m-%d)
echo "▶ Cutoff: $CUTOFF"

echo "▶ Syncing YouTube..."
python3 ~/daylog/sync_youtube.py "$DAYS" > /tmp/yt_sync.log 2>&1
echo "  done"

echo "▶ Collecting data..."
FILTERED=/tmp/weekly_input.txt
> $FILTERED
COUNT=0

# Small glob: only Oct/Nov/Dec 2026 — ~40 files, not 626
for f in "$DAYLOG"/2026-1*.md; do
    [ -f "$f" ] || continue
    fname="${f##*/}"
    fname="${fname%.md}"
    [[ "$fname" < "$CUTOFF" ]] && continue
    grep -qE "^(deep_work_hours|sleep_quality):" "$f" 2>/dev/null || continue
    {
        echo "--- $fname ---"
        cat "$f"
    } >> "$FILTERED"
    COUNT=$((COUNT+1))
    echo "  added: $fname"
done

echo "▶ $COUNT days with real data"

if [ "$COUNT" -lt 3 ]; then
    echo ""
    echo "⚠ Need at least 3 days. You have $COUNT."
    echo "  Log daily:"
    echo "    dlog sleep_quality 3"
    echo "    dlog deep_work_hours 2.5"
    echo "  Re-run when you have 3+: weekly 14"
    exit 0
fi

echo "▶ Starting AI..."
OLLAMA_FLASH_ATTENTION="1" OLLAMA_KV_CACHE_TYPE="q8_0" ollama serve > /tmp/ollama.log 2>&1 &
SPID=$!
sleep 4
trap "kill $SPID 2>/dev/null" EXIT

PROMPT='Analyze logs. 3 questions, under 150 words.
RULES: Only cite visible numbers. No fabricated averages. Missing fields → "insufficient data". Claims about this person are UNPROVEN.
(a) Pattern linking sleep_quality, energy, steps — cite specific days.
(b) Highest deep_work_hours day, and what preceded it.
(c) ONE change to test next week.'

cat $FILTERED | ollama run llama3.2 --temperature 0.2 "$PROMPT" 2>&1
echo ""
echo "═══════════════════════════════════════"
