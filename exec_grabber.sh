#!/bin/bash
set -euo pipefail

echo "=== Installing Python dependencies ==="
python3 -m pip install --upgrade pip
python3 -m pip install -U yt-dlp
python3 -m pip install requests lxml pytz beautifulsoup4

echo "=== Running grabber.py at $(date) ==="
python3 grabber.py

echo "=== Grabber finished at $(date) ==="
