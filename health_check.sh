#!/bin/bash

# --- Configuration ---
LOG_FILE="/tmp/payout_hunter_health.log"
# The name of the screen session that runs the main script
SCREEN_SESSION_NAME="payout-hunter"
# The script that starts the main process
RUN_SCRIPT="./run_hunter.sh"

echo "--- $(date) ---" >> "$LOG_FILE"

# Check if the screen session is running
if screen -list | grep -q "$SCREEN_SESSION_NAME"; then
    echo "[$SCREEN_SESSION_NAME] is running. Health check passed." >> "$LOG_FILE"
else
    echo "[$SCREEN_SESSION_NAME] is NOT running. Attempting restart..." >> "$LOG_FILE"
    
    # Run the main script to restart the process
    # We use nohup to ensure the restart attempt doesn't hang the cron job
    # We also need to ensure we are in the correct directory
    cd "$(dirname "$0")" || exit 1
    
    # The run_hunter.sh script already handles starting the screen session
    nohup "$RUN_SCRIPT" >> "$LOG_FILE" 2>&1 &
    
    echo "Restart command issued." >> "$LOG_FILE"
fi
