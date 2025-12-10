#!/bin/bash

echo "Starting Backend Server..."
cd backend
source venv/Scripts/activate
cd app
python -u start_server.py
