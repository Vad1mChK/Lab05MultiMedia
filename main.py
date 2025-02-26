import subprocess
import sys
import os

if __name__ == '__main__':
    # Construct the path to launcher.py relative to this script's directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    launcher_path = os.path.join(script_dir, 'apps', 'launcher.py')

    # Launch the launcher.py script
    try:
        process = subprocess.Popen([sys.executable, launcher_path],
                                   cwd=os.path.join(script_dir, "apps")
                                   )
        process.wait()
    except Exception as e:
        print(f"Failed to start launcher: {e}")
