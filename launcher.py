"""Agent Zero Desktop Launcher — double-click to start the Command Center.

Launches the web dashboard and opens the browser automatically.
"""

import sys
import time
import webbrowser
import subprocess
from pathlib import Path


def launch():
    base = Path(__file__).resolve().parent
    dashboard = base / "dashboard" / "app.py"
    print("=" * 60)
    print("  ANGESTIC ESSENCE — Command Center Launcher")
    print("=" * 60)
    print()
    print(f"  Starting dashboard server...")
    print()

    server = subprocess.Popen(
        [sys.executable, str(dashboard)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        cwd=str(base),
    )

    print("  Waiting for server to come online...")
    time.sleep(2)

    url = "http://127.0.0.1:5000"
    print(f"  Opening browser to {url}")
    webbrowser.open(url)

    print()
    print("  Dashboard is running. Close this window to stop.")
    print("-" * 60)

    try:
        for line in server.stdout:
            print(line, end="")
    except KeyboardInterrupt:
        pass
    finally:
        server.terminate()
        server.wait()
        print()
        print("  Agent Zero shutdown complete.")


if __name__ == "__main__":
    launch()
