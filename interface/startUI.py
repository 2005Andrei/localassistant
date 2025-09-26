import time
import sys
import os
from threading import Thread

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def spinning_cursor():
    while True:
        for cursor in '|/-\\':
            yield cursor

def home_assistant_animation():
    spinner = spinning_cursor()
    frames = [
        """
    ╔══════════════════════════════╗
    ║    HOME ASSISTANT STARTING   ║
    ║                              ║
    ║           ████████           ║
    ║         ██        ██         ║
    ║        ██    ██    ██        ║
    ║       ██    ████    ██       ║
    ║       ██    ████    ██       ║
    ║        ██    ██    ██        ║
    ║         ██        ██         ║
    ║           ████████           ║
    ║                              ║
    ║      Initializing... {}      ║
    ╚══════════════════════════════╝
        """,
        """
    ╔══════════════════════════════╗
    ║    HOME ASSISTANT STARTING   ║
    ║                              ║
    ║           ████████           ║
    ║         ██∙∙∙∙∙∙∙∙██         ║
    ║        ██∙∙∙∙██∙∙∙∙██        ║
    ║       ██∙∙∙∙████∙∙∙∙██       ║
    ║       ██∙∙∙∙████∙∙∙∙██       ║
    ║        ██∙∙∙∙██∙∙∙∙██        ║
    ║         ██∙∙∙∙∙∙∙∙██         ║
    ║           ████████           ║
    ║                              ║
    ║      Loading Modules {}      ║
    ╚══════════════════════════════╝
        """
    ]
    
    for i in range(20):
        clear_screen()
        frame = frames[i % 2]
        print(frame.format(next(spinner)))
        time.sleep(0.2)

def progress_bar(width=40):
    for i in range(width + 1):
        percent = (i / width) * 100
        bar = '█' * i + '░' * (width - i)
        sys.stdout.write(f'\r[{bar}] {percent:.1f}%')
        sys.stdout.flush()
        time.sleep(0.1)
    print()

def animate():
    clear_screen()
    spinning_cursor()
    home_assistant_animation()
    progress_bar()
