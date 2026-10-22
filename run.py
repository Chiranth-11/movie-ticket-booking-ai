#!/usr/bin/env python3
"""
CineAgent AI - Movie Ticket Booking System Launcher
Starts the FastAPI server with Uvicorn and opens the interactive web UI.
"""
import sys
import webbrowser
import threading
import time
import uvicorn
from backend.config import HOST, PORT, APP_NAME

def open_browser():
    time.sleep(1.2)
    webbrowser.open(f"http://{HOST}:{PORT}")

def main():
    print("=" * 65)
    print(f"🎬 {APP_NAME}")
    print("=" * 65)
    print(f"🌐 Server starting at: http://{HOST}:{PORT}")
    print(f"🤖 Autonomous ReAct Agent: Active & Ready")
    print(f"📚 Interactive Swagger API Docs: http://{HOST}:{PORT}/docs")
    print("=" * 65)

    threading.Thread(target=open_browser, daemon=True).start()
    uvicorn.run("backend.app:app", host=HOST, port=PORT, reload=False, log_level="info")

if __name__ == "__main__":
    main()
