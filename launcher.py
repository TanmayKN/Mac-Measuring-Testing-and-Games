#!/opt/homebrew/bin/python3.11
"""Launcher — re-runs angle_app.py with sudo via osascript so the user gets a password dialog."""
import os, sys, subprocess

# When running inside the .app, these point into the bundle itself
python     = sys.executable
script_dir = os.path.dirname(os.path.abspath(__file__))
target     = os.path.join(script_dir, "angle_app.py")

# Bundle's lib folder so macimu/pygame are found without system Python
lib_dir = os.path.join(script_dir, "lib", f"python{sys.version_info.major}.{sys.version_info.minor}")

applescript = (
    f'do shell script "PYTHONPATH=\\"{lib_dir}\\" \\"{python}\\" \\"{target}\\"" '
    f'with administrator privileges'
)
result = subprocess.run(["osascript", "-e", applescript])
sys.exit(result.returncode)
