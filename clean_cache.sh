#!/bin/bash

# GhostQA Cache Cleanup Script
# Removes all cache files and directories from the project

echo "========================================"
echo "  GhostQA Cache Cleanup"
echo "========================================"
echo ""

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Working directory: $SCRIPT_DIR"
echo ""

# Counter for removed items
removed_count=0

# Function to remove and count
remove_item() {
    if [ -e "$1" ]; then
        rm -rf "$1"
        echo "  Removed: $1"
        ((removed_count++))
    fi
}

# 1. Python cache directories
echo "[1/6] Removing Python __pycache__ directories..."
find . -type d -name "__pycache__" 2>/dev/null | while read dir; do
    rm -rf "$dir"
    echo "  Removed: $dir"
    ((removed_count++))
done

# 2. Python compiled files
echo ""
echo "[2/6] Removing .pyc and .pyo files..."
find . -type f -name "*.pyc" -delete 2>/dev/null
find . -type f -name "*.pyo" -delete 2>/dev/null
find . -type f -name "*.pyd" -delete 2>/dev/null
echo "  Done"

# 3. Pytest cache
echo ""
echo "[3/6] Removing pytest cache..."
find . -type d -name ".pytest_cache" 2>/dev/null | while read dir; do
    rm -rf "$dir"
    echo "  Removed: $dir"
done
find . -type d -name ".mypy_cache" 2>/dev/null | while read dir; do
    rm -rf "$dir"
    echo "  Removed: $dir"
done

# 4. Node.js cache (but not node_modules itself)
echo ""
echo "[4/6] Removing Node.js cache..."
if [ -d "frontend/node_modules/.cache" ]; then
    rm -rf "frontend/node_modules/.cache"
    echo "  Removed: frontend/node_modules/.cache"
fi
if [ -d "frontend/.vite" ]; then
    rm -rf "frontend/.vite"
    echo "  Removed: frontend/.vite"
fi

# 5. Build artifacts
echo ""
echo "[5/6] Removing build artifacts..."
if [ -d "frontend/dist" ]; then
    rm -rf "frontend/dist"
    echo "  Removed: frontend/dist"
fi
if [ -d "backend/build" ]; then
    rm -rf "backend/build"
    echo "  Removed: backend/build"
fi
find . -type d -name "*.egg-info" 2>/dev/null | while read dir; do
    rm -rf "$dir"
    echo "  Removed: $dir"
done

# 6. Misc cache files
echo ""
echo "[6/6] Removing miscellaneous cache files..."
find . -type f -name ".DS_Store" -delete 2>/dev/null
find . -type f -name "Thumbs.db" -delete 2>/dev/null
find . -type f -name "*.log" -path "*/logs/*" -delete 2>/dev/null
find . -type d -name ".ruff_cache" 2>/dev/null | while read dir; do
    rm -rf "$dir"
    echo "  Removed: $dir"
done

echo ""
echo "========================================"
echo "  Cache cleanup complete!"
echo "========================================"
echo ""
echo "Note: To also clear the knowledge base cache, run:"
echo "  rm -rf backend/app/data/agent_knowledge/cache/*"
echo ""
