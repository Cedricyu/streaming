import subprocess
import os
import sys
import time

BASE = os.path.abspath(os.path.dirname(__file__))

processes = []

def run_service(script_path, cwd):
    return subprocess.Popen(
        [sys.executable, script_path],
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

if __name__ == "__main__":
    # 啟動 Service B
    proc_b = run_service("video_service.py", os.path.join(BASE, "video"))
    processes.append(proc_b)
    print("Service B 啟動...")

    # 等 2 秒確保 B 先起來
    time.sleep(2)

    # 啟動 Service A
    proc_a = run_service("stream.py", os.path.join(BASE, "stream"))
    processes.append(proc_a)
    print("Service A 啟動...")

    print("=== 按 Ctrl+C 可關閉所有服務 ===\n")
    try:
        # 實時顯示兩個子程序 log
        while True:
            for p in processes:
                line = p.stdout.readline()
                if line:
                    print(line, end="")
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n關閉服務中...")
        for p in processes:
            p.terminate()
