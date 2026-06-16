#!/bin/bash
cd /home/jetdream/HHD-Dream/JetdreamTerminal
source .venv/bin/activate
exec python3 main.py "$@"
