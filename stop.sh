#!/bin/bash
# Find the PID of the process running on port 8080
PID=$(lsof -t -i:8080)

if [ -z "$PID" ]; then
    echo "No server found running on port 8080."
else
    echo "Stopping server on port 8080 (PID: $PID)..."
    kill $PID
    echo "Server stopped."
fi
