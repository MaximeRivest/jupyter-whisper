
import os
import sys
from pathlib import Path

def verify_jupyterchat_installation():
    import jupyterchat
    print(f"jupyterchat location: {jupyterchat.__file__}")
    
    # Check if static files are accessible
    static_dir = Path(jupyterchat.__file__).parent / 'static'
    print(f"Static directory exists: {static_dir.exists()}")
    if static_dir.exists():
        print("Static files:", list(static_dir.glob('*')))
    
    # Test basic functionality
    print("\nTesting basic functionality...")
    try:
        # Test if we can access the Chat class
        from claudette import Chat
        print("✓ Chat class is accessible")
        
        # Test if we can create a JupyterFrontEnd instance
        from ipylab import JupyterFrontEnd
        print("✓ JupyterFrontEnd is accessible")
        
        # Test if we can access the magic commands
        from IPython import get_ipython
        ip = get_ipython()
        if ip is not None:
            print("✓ IPython environment detected")
            if 'user' in ip.magics_manager.magics['cell']:
                print("✓ %%user magic is registered")
            if 'assistant' in ip.magics_manager.magics['cell']:
                print("✓ %%assistant magic is registered")
    except Exception as e:
        print(f"Error during functionality test: {e}")

if __name__ == '__main__':
    verify_jupyterchat_installation()
