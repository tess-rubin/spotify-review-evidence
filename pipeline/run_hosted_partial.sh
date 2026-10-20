#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
printf '%s\n' "$$" > data/hosted/runner.pid
python3 pipeline/hosted.py partial --execute-paid --spend-cap 4.90 --phase resume
python3 pipeline/hosted_complete.py
