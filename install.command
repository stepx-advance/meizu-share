#!/bin/sh
cd "$(dirname "$0")" || exit 1
if command -v python3 >/dev/null 2>&1; then
    python3 tools/quick_setup.py "$@"
    result=$?
else
    echo 'Python 3.9+ is required. Install Python, then run this launcher again.'
    result=1
fi
printf '\nPress Enter to close. '
read -r reply
exit "$result"
