import subprocess
import sys
import os

if __name__ == '__main__':
    # Construct the path to launcher.py relative to this script's directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    launcher_path = os.path.join(script_dir, 'apps', 'launcher.py')

    env = os.environ.copy()
    env['LAB_05_MULTIMEDIA_ROOT'] = script_dir

    # Launch the launcher.py script
    try:
        process = subprocess.Popen([sys.executable, launcher_path],
                                   cwd=os.path.join(script_dir, "apps"),
                                   env=env
                                   )
        process.wait()
    except Exception as e:
        print(f"Failed to start launcher: {e}")
