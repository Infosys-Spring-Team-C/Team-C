import subprocess
import sys
import time
import os

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

def run_services():
    print("=" * 60)
    print("[*] SalesGenie AI - Launching Backend & Frontend")
    print("=" * 60)
    print("1. Backend API:  http://localhost:8000 (Docs: http://localhost:8000/docs)")
    print("2. Frontend UI:  http://localhost:8501")
    print("=" * 60)
    
    python_exe = sys.executable

    # Start FastAPI backend
    backend_proc = subprocess.Popen([
        python_exe, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000", "--reload"
    ])
    
    time.sleep(2)

    # Start Streamlit frontend
    frontend_proc = subprocess.Popen([
        python_exe, "-m", "streamlit", "run", "app.py", "--server.port", "8501"
    ])

    try:
        backend_proc.wait()
        frontend_proc.wait()
    except KeyboardInterrupt:
        print("\nStopping services...")
        backend_proc.terminate()
        frontend_proc.terminate()

if __name__ == "__main__":
    run_services()
