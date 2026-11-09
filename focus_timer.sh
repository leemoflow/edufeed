#!/bin/zsh
FIELD=~/daylog/.focus_start
CMD=$1
if [ "$CMD" = "start" ]; then
    date +%s > "$FIELD"
    echo "Focus started at $(date +%H:%M)"
elif [ "$CMD" = "stop" ]; then
    [ -f "$FIELD" ] || { echo "No start recorded"; exit 0; }
    START=$(cat "$FIELD")
    NOW=$(date +%s)
    MINUTES=$(( (NOW - START) / 60 ))
    HOURS=$(echo "scale=2; $MINUTES / 60" | bc)
    rm "$FIELD"
    if [ "$MINUTES" -lt 5 ]; then echo "Skipped (<5 min)"; exit 0; fi
    # Read existing value and add
    TODAY=$(date +%Y-%m-%d)
    FILE=~/daylog/$TODAY.md
    EXISTING=$(grep "^deep_work_hours:" "$FILE" 2>/dev/null | awk '{print $2}')
    EXISTING=${EXISTING:-0}
    TOTAL=$(echo "scale=2; $EXISTING + $HOURS" | bc)
    python3 ~/daylog/customlog.py deep_work_hours "$TOTAL"
    echo "Added $HOURS h (total: $TOTAL h)"
fi
