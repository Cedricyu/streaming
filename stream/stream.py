import subprocess
import os
import time
from flask import Flask, request, jsonify
from threading import Thread
from queue import Queue
import requests

app = Flask(__name__)
TMP_DIR = "./tmp_video"
os.makedirs(TMP_DIR, exist_ok=True)
transcode_queue = Queue()
SERVICE_B_URL = "http://localhost:8081/video/get?id={vid}"
SERVICE_B_LIST = "http://localhost:8081/video/list_pending"
POLL_INTERVAL = 10

def start_nginx_rtmp():
    # 路徑視你的 nginx 裝法而定
    nginx_conf_path = os.path.abspath('./nginx-rtmp.conf')
    print(f"啟動 nginx-rtmp, conf={nginx_conf_path}")
    return subprocess.Popen(['nginx', '-c', nginx_conf_path])

def start_hls_ffmpeg():
    print("啟動 ffmpeg HLS producer")
    return subprocess.Popen([
        'ffmpeg', '-hide_banner', '-loglevel', 'error',
        '-i', 'rtmp://localhost/live/stream',
        '-c:v', 'libx264', '-c:a', 'aac',
        '-f', 'hls',
        '-hls_time', '4', '-hls_list_size', '5', '-hls_flags', 'delete_segments',
        os.path.join(TMP_DIR, "index.m3u8")
    ])

def push_mp4_to_rtmp(mp4_path):
    cmd = [
        'ffmpeg', '-re', '-i', mp4_path,
        '-c', 'copy', '-f', 'flv', 'rtmp://localhost/live/stream'
    ]
    print(f"推流到 RTMP: {mp4_path}")
    subprocess.run(cmd)

def transcode_worker():
    while True:
        video_id = transcode_queue.get()
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
    while True:
        try:
            resp = requests.get(SERVICE_B_LIST)
            if resp.status_code == 200:
                pending_list = resp.json().get("videos", [])
                for vid in pending_list:
                    transcode_queue.put(vid)
        except Exception as e:
            print(f"Polling 錯誤: {e}")
        time.sleep(POLL_INTERVAL)

@app.route('/submit', methods=['POST'])
def submit_mp4():
    data = request.json
    video_id = data['video_id']
    transcode_queue.put(video_id)
    print(f"[API] 手動加入 queue: {video_id}")
    return jsonify({"status": "queued", "video_id": video_id})

if __name__ == "__main__":
    print("=== 啟動 RTMP nginx + HLS producer + Flask ===")
    nginx_proc = start_nginx_rtmp()
    # 確認 nginx 啟動成功再往下
    time.sleep(1)
    hls_proc = start_hls_ffmpeg()
    worker = Thread(target=transcode_worker, daemon=True)
    worker.start()
    poller = Thread(target=poll_new_videos, daemon=True)
    poller.start()
    app.run(port=8080, debug=True)
