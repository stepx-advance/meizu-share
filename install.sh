#!/bin/sh
cd "$(dirname "$0")" || exit 1
if ! command -v python3 >/dev/null 2>&1; then
    printf '%s\n' 'Python 3.9+ is required. Install Python, then run this launcher again.' >&2
    exit 127
fi
exec python3 tools/quick_setup.py "$@"
