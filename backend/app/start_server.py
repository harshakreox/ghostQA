"""
Windows-compatible startup script for GhostQA backend
This MUST be run instead of 'uvicorn main:app' on Windows
"""

import sys
import os
import asyncio

# Force unbuffered output
os.environ['PYTHONUNBUFFERED'] = '1'

# CRITICAL: Set Windows event loop policy FIRST, before any imports
if sys.platform == 'win32':
    print(" Detected Windows - Setting ProactorEventLoop policy...", flush=True)
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    print(" Event loop policy set successfully", flush=True)

# Now we can import uvicorn and start the server
if __name__ == "__main__":
    import uvicorn

    print("\n Starting GhostQA Backend Server...", flush=True)
    print(" Server will run on: http://localhost:8000", flush=True)
    print(" API Docs available at: http://localhost:8000/docs", flush=True)
    print("\n" + "="*50, flush=True)

    # Note: reload=False ensures logs appear in this terminal
    # Set reload=True for development but logs may not show
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # Changed to False to see logs
        log_level="info",
        access_log=True
    )