import os
import platform
import subprocess
import shutil

def compile_loading_window():
    """Compile the loading window for macOS"""
    if platform.system().lower() == 'darwin':
        try:
            # Compile the loading window
            subprocess.run([
                'clang',
                'loading_window.m',
                '-framework', 'Cocoa',
                '-o', 'loading_window'
            ], check=True)
            return True
        except subprocess.CalledProcessError as e:
            print("Failed to compile loading window:", e)
            return False
    return False

def build_executable():
    # Determine the system
    system = platform.system().lower()
    
    # Base PyInstaller command
    cmd = [
        'pyinstaller',
        '--onefile',
        '--windowed',
        '--name=TheInversePath',
        '--clean',
        '--add-data', f'sound_effects.py{os.pathsep}.',
        '--add-data', f'music_generator.py{os.pathsep}.',
        'main.py'
    ]
    
    # Add icon if it exists
    if system == 'windows' and os.path.exists('icon.ico'):
        cmd.extend(['--icon=icon.ico'])
    elif system == 'darwin' and os.path.exists('icon.icns'):
        cmd.extend(['--icon=icon.icns'])
        
        # For macOS, compile the loading window
        compile_loading_window()
    
    # Run PyInstaller
    subprocess.run(cmd, check=True)
    
    if system == 'darwin':
        # For macOS, we need to modify the generated app to show the loading window
        app_path = 'dist/TheInversePath.app'
        if os.path.exists(app_path):
            macos_path = os.path.join(app_path, 'Contents/MacOS')
            
            # Copy the loading window binary to the app bundle
            if os.path.exists('loading_window'):
                shutil.copy2('loading_window', os.path.join(macos_path, 'loading_window'))
                os.chmod(os.path.join(macos_path, 'loading_window'), 0o755)
            else:
                print("Warning: loading_window binary not found!")
                return
            
            # Create the wrapper script
            wrapper_script = '''#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
"$DIR/loading_window" & # Start loading window
LOADING_PID=$!
"$DIR/TheInversePath.bin" # Start main app
kill $LOADING_PID # Close loading window when main app starts
'''
            # Save the wrapper script
            with open('dist/wrapper.sh', 'w') as f:
                f.write(wrapper_script)
            os.chmod('dist/wrapper.sh', 0o755)
            
            # Move the original executable
            os.rename(
                os.path.join(macos_path, 'TheInversePath'),
                os.path.join(macos_path, 'TheInversePath.bin')
            )
            
            # Move the wrapper script to be the main executable
            shutil.move('dist/wrapper.sh', os.path.join(macos_path, 'TheInversePath'))
            
            print("Successfully added loading window to macOS app!")
    
    print(f"\nBuild completed for {system}!")

if __name__ == '__main__':
    build_executable() 
