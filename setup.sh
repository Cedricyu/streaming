#!/bin/bash

set -e

# ===== 1. 自動安裝 nginx + rtmp module =====
echo "==> 安裝 nginx + RTMP module"
sudo apt update
sudo apt install -y nginx libnginx-mod-rtmp

# ===== 2. 備份舊 nginx.conf =====
if [ ! -f /etc/nginx/nginx.conf.bak ]; then
    echo "==> 備份原本的 /etc/nginx/nginx.conf"
    sudo cp /etc/nginx/nginx.conf /etc/nginx/nginx.conf.bak
fi

# ===== 3. 複製本地 nginx.conf 覆蓋系統設定 =====
echo "==> 更新 nginx.conf（支援 rtmp + hls + http）"
sudo cp ./nginx.conf /etc/nginx/nginx.conf

# ===== 4. 檢查 config、重啟 nginx =====
sudo nginx -t
sudo systemctl restart nginx || sudo service nginx restart

# ===== 5. 檢查 RTMP 設定與 port =====
if grep -q 'rtmp' /etc/nginx/nginx.conf; then
    echo "[OK] nginx.conf 已有 rtmp 配置"
else
    echo "[警告] /etc/nginx/nginx.conf 沒有 rtmp 配置，請加入 rtmp {...} 設定"
    exit 1
fi

if sudo netstat -plnt | grep -q ':1935'; then
    echo "[OK] nginx 已啟動 1935 RTMP port"
else
    echo "[警告] nginx 尚未監聽 1935 port，請檢查 nginx 是否啟動"
    exit 1
fi

echo "[總結] 這台已支援 nginx-rtmp，可以直接用 ffmpeg 推流到 rtmp://localhost/live/stream"

# ===== 6. 啟用 venv =====
echo "==> 啟用 Python venv"
source ./stream_video/venv/bin/activate

# ===== 7. 啟動 stream.py =====
cd ./stream
nohup python3 stream.py > ../stream.log 2>&1 &
STREAM_PID=$!
echo "stream.py 啟動，PID: $STREAM_PID，log: ./stream.log"

# ===== 8. 啟動 musetalk.py =====
cd ../video
nohup python3 musetalk.py > ../musetalk.log 2>&1 &
MUSE_PID=$!
echo "musetalk.py 啟動，PID: $MUSE_PID，log: ./musetalk.log"

echo "所有服務已啟動，可以 tail -f stream.log musetalk.log 來看 log"
