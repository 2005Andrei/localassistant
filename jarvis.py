import shutil
import subprocess
import requests
import psutil
import socket
import signal
import os
import tempfile
from typing import Optional, List
import threading
import time
import sys

'''
1) check for ollama
2) run animation
3) run api
4) start tts and stt
'''

# Global variables
process: Optional[subprocess.Popen] = None
log_file_handle: Optional[object] = None
log_file_path: Optional[str] = None
stream_thread: Optional[threading.Thread] = None
should_exit = threading.Event()


def check_ollama() -> bool:
    # check for ollama
    ollama_path = shutil.which("ollama")
    if ollama_path:
        print(f"[+] Ollama is at {ollama_path}")

        try:
            vers = subprocess.run(["ollama", "--version"], capture_output=True, text=True)
            if vers.returncode == 0:
                    print(f"Ollama version {vers}")
                    return True
        except Exception as e:
            print(f"[-] Error: {e}")
            return False
    else:
        print("Ollama not found at path.")
        return False


def setup_logging() -> str:
    global log_file_handle, log_file_path

    try:
        os.makedirs("./.log", exist_ok=True)
        log_file_path = f"./.log/ollama_requests_{int(time.time())}.log"
        
        with open(log_file_path, "w") as f:
            pass
        
        print(f"[+] Log file created at {log_file_path}")
        return log_file_path
    except Exception as e:
        print(f"[-] Error creating log file: {e}")
        raise


def stream_output(process: subprocess.Popen, log_path: str):
    try:
        with open(log_path, 'a', buffering=1) as f:
            while not should_exit.is_set() and process.poll() is None:
                line = process.stdout.readline()
                if line:
                    print(f"[Ollama] {line.strip()}") 
                    f.write(line)
                    f.flush()
                else:
                    time.sleep(0.1)
    except Exception as e:
        print(f"[-] Error in output streaming: {e}")


def run_ollama():
    global process, stream_thread, log_file_path
    
    if not check_ollama():
        raise RuntimeError("Ollama unable to serve")

 
    kill_ollama()
    
    try:
        log_file_path = setup_logging()

        process = subprocess.Popen(["ollama", "serve"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)

        print("[+] <ollama serve> started")

        should_exit.clear()
        stream_thread = threading.Thread(target=stream_output, args=(process, log_file_path), daemon=True)
        stream_thread.start()
        
        if not ollama_ready(timeout=30):
            raise RuntimeError("Ollama is not serving")

    except Exception as e:
        cleanup_ollama()
        raise e


def ollama_ready(timeout: int = 30) -> bool:
    start_time = time.time()

    while time.time() - start_time < timeout:
        if should_exit.is_set():
            return False

        try:
            with socket.create_connection(("localhost", 11434), timeout=1):
                print("[+] Ollama is serving")
                return True
        except (socket.error, ConnectionRefusedError):
            pass

    return False


def cleanup_ollama():
    global process, stream_thread, log_file_path, should_exit

    should_exit.set()

    if process:
        print("[/] Terminating process started by this program")
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        except Exception as e:
            print("idk")
        finally:
            process = None
    if stream_thread and stream_thread.is_alive():
        print("[/] Terminating serving thread..")

        stream_thread.join(timeout=2)
        if stream_thread.is_alive():
            print("[-] Stream thread survived. You: 0, Thread: 1")

    log_file_path = None
    stream_thread = None


def kill_ollama():
    for proc in psutil.process_iter(attrs=['pid', 'name', 'cmdline']):
        try:
            if "ollama" in proc.info['name']:
                proc.terminate()
                proc.wait(timeout=5)
                print(f"[+] Terminated process {proc}")
        except Exception as e:
            print(f"[-] Exception: {e}")

def signal_handler(signum, frame):
    cleanup_ollama()
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def start_new():
    try:
        if sys.platform.startswith("win"):
            cmd = ["start", "cmd", "\k", "python", "core/setup.py"]
            ui_process = subprocess.Popen(cmd, shell=True)
        else:
            print("I'm on windows at the moment, will change for linux and macos when I have the time")

if __name__=="__main__":
    try:
        run_ollama()

        print("[+] Ollama is serving. Ctrl c stops the program.")
        start_new()
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("[!] Exiting serving. Exiting Georging. See you next time")
    except Exception as e:
        print(f"[-] Oh no: {e}")
    finally:
        cleanup_ollama()

    #startapi() --> start logging
    #           --> save that in a file
    #           --> open new window for seeing requests up to the users wishes
