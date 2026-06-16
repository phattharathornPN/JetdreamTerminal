#!/bin/bash
cd "$(dirname "$(readlink -f "$0")")"
source .venv/bin/activate
exec python3 main.py "$@"
