
import subprocess
import sys
from pathlib import Path

def install_package():
    # Get the current directory
    current_dir = Path.cwd()
    
    # Uninstall existing package if it exists
    subprocess.run([sys.executable, "-m", "pip", "uninstall", "-y", "jupyter_whisper"])
    
    # Install the package in development mode
    subprocess.run([sys.executable, "-m", "pip", "install", "-e", str(current_dir)])
    
    print("\nPackage installed successfully!")
    print("You can now use 'from jupyter_whisper import setup_jupyter_whisper' to configure your API keys.")

if __name__ == "__main__":
    install_package()
