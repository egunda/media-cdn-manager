#!/bin/bash
if ! command -v lsof >/dev/null 2>&1; then
    echo "Error: 'lsof' is not installed. Cannot detect process on port 6001."
    exit 1
fi

PID=$(lsof -t -i:6001)

if [ -z "$PID" ]; then
    echo "No server found running on port 6001."
else
    echo "Stopping server on port 6001 (PID: $PID)..."
    kill $PID
    echo "Server stopped."
fi
