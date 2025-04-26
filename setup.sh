#!/bin/bash

# 啟用 venv
source /stream_video/venv/bin/activate

# 1. 檢查 nginx.conf 是否有 rtmp 區塊
if grep -q 'rtmp' /etc/nginx/nginx.conf; then
    echo "[OK] nginx.conf 已有 rtmp 配置"
else
    echo "[警告] /etc/nginx/nginx.conf 沒有 rtmp 配置，請加入 rtmp {...} 設定"
    exit 1
fi

# 2. 檢查 1935 port 是否已啟用
if sudo netstat -plnt | grep -q ':1935'; then
    echo "[OK] nginx 已啟動 1935 RTMP port"
else
    echo "[警告] nginx 尚未監聽 1935 port，請檢查 nginx 是否啟動"
    exit 1
fi

echo "[總結] 這台已支援 nginx-rtmp，可以直接用 ffmpeg 推流到 rtmp://localhost/live/stream"

# 3. 啟動 stream.py
cd ./stream
nohup python3 stream.py > ../stream.log 2>&1 &
STREAM_PID=$!
echo "stream.py 啟動，PID: $STREAM_PID，log: ./stream.log"

# 4. 啟動 musetalk.py
cd ../video
nohup python3 musetalk.py > ../musetalk.log 2>&1 &
MUSE_PID=$!
echo "musetalk.py 啟動，PID: $MUSE_PID，log: ./musetalk.log"

echo "所有服務已啟動，可以 tail -f stream.log musetalk.log 來看 log"
