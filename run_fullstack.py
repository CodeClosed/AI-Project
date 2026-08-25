"""
NutriMenu AI — Full-Stack Launcher (FastAPI Backend + React Frontend).
Runs:
- FastAPI backend on http://127.0.0.1:8000
- React Vite frontend on http://localhost:5173
"""

import sys
import os
import subprocess
import time
import webbrowser
from pathlib import Path

root_dir = Path(__file__).resolve().parent
frontend_dir = root_dir / "frontend"


def main():
    print("=" * 65)
    print("🥗 NutriMenu AI — Full-Stack Application Launcher")
    print("=" * 65)
    print("1. Starting FastAPI backend on http://127.0.0.1:8000 ...")

    # Start FastAPI backend
    backend_cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "backend.api:app",
        "--host",
        "127.0.0.1",
        "--port",
        "8000",
        "--reload",
    ]
    backend_proc = subprocess.Popen(backend_cmd, cwd=str(root_dir))

    # Wait for backend to spin up
    time.sleep(2)

    print("2. Starting React Vite frontend on http://localhost:5173 ...")
    # Start Vite frontend
    npm_cmd = "npm.cmd" if os.name == "nt" else "npm"
    frontend_proc = subprocess.Popen([npm_cmd, "run", "dev"], cwd=str(frontend_dir))

    time.sleep(2)
    print("\n✨ NutriMenu AI is running!")
    print("👉 Frontend: http://localhost:5173")
    print("👉 Backend API: http://127.0.0.1:8000/docs")
    print("\nPress Ctrl+C to terminate both servers.\n")

    try:
        # Open in default browser
        webbrowser.open("http://localhost:5173")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping services...")
        backend_proc.terminate()
        frontend_proc.terminate()
        print("Shutdown complete.")


if __name__ == "__main__":
    main()
