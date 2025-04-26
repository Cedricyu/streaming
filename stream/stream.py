import os
import time
import signal
from flask import Flask, request, jsonify
from threading import Thread, Event
from queue import Queue
import subprocess
import requests

app = Flask(__name__)
TMP_DIR = "./tmp_video"
os.makedirs(TMP_DIR, exist_ok=True)
transcode_queue = Queue()
SERVICE_B_URL = "http://localhost:8081/video/get?id={vid}"
SERVICE_B_LIST = "http://localhost:8081/video/list_pending"
POLL_INTERVAL = 10

# 用 event 控制 thread 結束
exit_event = Event()

def push_mp4_to_rtmp(mp4_path):
    cmd = [
        'ffmpeg', '-re', '-i', mp4_path,
        '-c', 'copy', '-f', 'flv', 'rtmp://localhost/live/stream'
    ]
    print(f"推流到 RTMP: {mp4_path}")
    subprocess.run(cmd)

def transcode_worker():
    while not exit_event.is_set():
        try:
            video_id = transcode_queue.get(timeout=1)
        except Exception:
            continue  # 1秒超時繼續檢查是否退出
        if video_id is None:
            break
        mp4_path = os.path.join(TMP_DIR, f"{video_id}")
        url = SERVICE_B_URL.format(vid=video_id)
        if not os.path.exists(mp4_path):
            resp = requests.get(url, stream=True)
            if resp.status_code != 200:
                print(f"下載失敗: {video_id} (狀態碼: {resp.status_code})")
                transcode_queue.task_done()
                continue
            with open(mp4_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"下載完成: {mp4_path}")
        else:
            print(f"已存在，略過下載: {mp4_path}")
        push_mp4_to_rtmp(mp4_path)
        transcode_queue.task_done()

def poll_new_videos():
    while not exit_event.is_set():
        try:
            resp = requests.get(SERVICE_B_LIST)
            if resp.status_code == 200:
                pending_list = resp.json().get("videos", [])
                for vid in pending_list:
                    transcode_queue.put(vid)
        except Exception as e:
            print(f"Polling 錯誤: {e}")
        for _ in range(POLL_INTERVAL * 2):  # 0.5s * 20 = 10秒
            if exit_event.is_set():
                break
            time.sleep(0.5)

@app.route('/submit', methods=['POST'])
def submit_mp4():
    data = request.json
    video_id = data['video_id']
    transcode_queue.put(video_id)
    print(f"[API] 手動加入 queue: {video_id}")
    return jsonify({"status": "queued", "video_id": video_id})

def signal_handler(sig, frame):
    print("\n[!] 收到結束訊號, 正在退出...")
    exit_event.set()
    transcode_queue.put(None)
    time.sleep(0.5)  # 留一點時間給 thread 收到 signal
    os._exit(0)  # <--- 強制結束整個 python process

if __name__ == "__main__":
    print("=== Flask 啟動，負責 mp4 推流到 RTMP，不管理 nginx ===")
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    worker = Thread(target=transcode_worker)
    poller = Thread(target=poll_new_videos)
    worker.start()
    poller.start()
    app.run(port=8080, debug=True, use_reloader=False)
    # Flask 停止後, 等待 thread 結束
    worker.join()
    poller.join()
    print("已安全退出所有執行緒。")
