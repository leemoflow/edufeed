#!/bin/zsh
echo "How rested do you feel? (1=exhausted, 5=great)"
read -r q
python3 ~/daylog/customlog.py sleep_quality "$q"
echo "Roughly when did you sleep/wake? (e.g. 11pm-6:30am, or press Enter to skip)"
read -r s
[ -n "$s" ] && python3 ~/daylog/customlog.py sleep "$s"
echo "Logged. Run 'daylog' to see the dashboard."
