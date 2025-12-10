#!/bin/bash

echo "Setting up Test Automation Framework - Backend"
echo "==============================================="

# Navigate to backend directory
cd backend

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/Scripts/activate

# Install dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt --break-system-packages

# Install Playwright browsers
echo "Installing Playwright browsers..."
playwright install chromium

# Create data directories
echo "Creating data directories..."
mkdir -p data/projects
mkdir -p data/reports

echo ""
echo "Backend setup complete!"
echo ""
echo "To start the backend server, run:"
echo "  cd backend"
echo "  source venv/Scripts/activate"
echo "  cd app"
echo "  python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000"
