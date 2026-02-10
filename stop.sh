#!/bin/bash
# Find the PID of the process running on port 6001
PID=$(lsof -t -i:6001)

if [ -z "$PID" ]; then
    echo "No server found running on port 6001."
else
    echo "Stopping server on port 6001 (PID: $PID)..."
    kill $PID
    echo "Server stopped."
fi
