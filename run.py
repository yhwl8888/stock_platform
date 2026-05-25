import subprocess
import sys
import os
import signal
import threading
import time


def start_backend():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "api.main:app", "--host", "127.0.0.1", "--port", "8000", "--reload"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return proc


def start_frontend():
    proc = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "web/app.py", "--server.port", "8501"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return proc


def main():
    print("启动后端服务...")
    backend = start_backend()
    time.sleep(3)
    print("启动前端界面...")
    frontend = start_frontend()

    print("\n" + "=" * 50)
    print("  量化选股回测平台已启动")
    print("  Backend:  http://127.0.0.1:8000")
    print("  Frontend: http://127.0.0.1:8501")
    print("=" * 50 + "\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n正在关闭服务...")
        backend.terminate()
        frontend.terminate()


if __name__ == "__main__":
    main()
