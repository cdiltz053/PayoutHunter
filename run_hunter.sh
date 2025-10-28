#!/bin/bash

# This script is designed to be run on your 24/7 self-hosted machine.
# It uses 'screen' to detach the process, allowing it to run even if you close your terminal.

# 1. Check if the screen session is already running
if screen -list | grep -q "payout-hunter"; then
    echo "Screen session 'payout-hunter' is already running. Attaching..."
    screen -r payout-hunter
    exit 0
fi

echo "Starting Payout Hunter in a detached screen session..."

# 2. Run the script inside a new detached screen session
# -S payout-hunter: names the session
# -d -m: runs the session in detached mode
# command: activates the virtual environment and runs the script

screen -S payout-hunter -d -m bash -c "
    source venv/bin/activate
    python3 payout_hunter.py
"

echo "Payout Hunter is now running 24/7 in a detached screen session named 'payout-hunter'."
echo "To view the output, run: screen -r payout-hunter"
echo "To detach again (leave it running in the background), press: Ctrl+A then D"
