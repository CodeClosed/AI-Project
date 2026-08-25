"""
Launcher script for NutriMenu AI Streamlit Web UI.
Run with: python run_ui.py
"""

import sys
import subprocess
from pathlib import Path


def main():
    app_path = Path(__file__).resolve().parent / "app.py"
    if not app_path.is_file():
        print(f"Error: Could not locate app entry point at {app_path}", file=sys.stderr)
        sys.exit(1)

    # Verify streamlit is available
    try:
        import streamlit
    except ImportError:
        print("Error: Streamlit is not installed in the current environment.", file=sys.stderr)
        print("Install required dependencies using: pip install -r requirements.txt", file=sys.stderr)
        sys.exit(1)

    print("=" * 70)
    print("🥗 Starting NutriMenu AI: 3-Tier Food Recommendation Dashboard...")
    print(f"📁 Loading App from: {app_path}")
    print("🌐 Opening web browser at: http://localhost:8501")
    print("=" * 70)
    
    cmd = [sys.executable, "-m", "streamlit", "run", str(app_path)]
    try:
        res = subprocess.run(cmd)
        sys.exit(res.returncode)
    except KeyboardInterrupt:
        print("\n👋 App stopped by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error launching Streamlit: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
