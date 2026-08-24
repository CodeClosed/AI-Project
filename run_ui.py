"""
Launcher script for NutriMenu AI Streamlit Web UI.
Run with: python run_ui.py
"""

import sys
import subprocess
from pathlib import Path

def main():
    app_path = Path(__file__).resolve().parent / "app.py"
    print("=" * 70)
    print("🚀 Starting NutriMenu AI: 3-Tier Food Recommendation Dashboard...")
    print(f"📁 Loading App from: {app_path}")
    print("🌐 Opening web browser at: http://localhost:8501")
    print("=" * 70)
    
    cmd = [sys.executable, "-m", "streamlit", "run", str(app_path), "--server.headless=false"]
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n👋 App stopped by user.")

if __name__ == "__main__":
    main()
