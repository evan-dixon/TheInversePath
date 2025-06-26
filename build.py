import os
import platform
import subprocess

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
    
    # Run PyInstaller
    subprocess.run(cmd, check=True)
    
    print(f"\nBuild completed for {system}!")

if __name__ == '__main__':
    build_executable() 
