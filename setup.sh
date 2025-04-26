#!/bin/bash

set -e

# ===== 1. 安裝 nginx + RTMP module（如已安裝自動略過）=====
echo "==> 安裝 nginx + RTMP module"
if ! dpkg -l | grep -q libnginx-mod-rtmp; then
    sudo apt update
    sudo apt install -y nginx libnginx-mod-rtmp
else
    echo "[SKIP] nginx 及 libnginx-mod-rtmp 已安裝"
fi

# ===== 2. 備份舊 nginx.conf（只備份一次）=====
if [ ! -f /etc/nginx/nginx.conf.bak ]; then
    echo "==> 備份原本的 /etc/nginx/nginx.conf"
    sudo cp /etc/nginx/nginx.conf /etc/nginx/nginx.conf.bak
else
    echo "[SKIP] 已備份 nginx.conf"
fi

# ===== 3. 覆蓋 nginx.conf（如果不同才更新）=====
if ! cmp -s ./nginx.conf /etc/nginx/nginx.conf; then
    echo "==> 更新 nginx.conf（支援 rtmp + hls + http）"
    sudo cp ./nginx.conf /etc/nginx/nginx.conf
else
    echo "[SKIP] /etc/nginx/nginx.conf 已是最新"
fi

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

if sudo ss -plnt | grep -q ':1935'; then
    echo "[OK] nginx 已啟動 1935 RTMP port"
else
    echo "[警告] nginx 尚未監聽 1935 port，請檢查 nginx 是否啟動"
    exit 1
fi

echo "[總結] 這台已支援 nginx-rtmp，可以直接用 ffmpeg 推流到 rtmp://localhost/live/stream"

# ===== 6. 檢查/啟用 venv =====
echo "==> 檢查/建立 Python venv"
if [ ! -d "./venv" ]; then
    python3 -m venv venv
    echo "==> 已建立新 venv"
else
    echo "[SKIP] venv 已存在"
fi

source ./venv/bin/activate

# ===== 7. 安裝 Python 相依套件 =====
if [ -f requirements.txt ]; then
    pip install --upgrade pip
    pip install -r requirements.txt
    echo "[OK] Python 相依套件安裝完成"
else
    echo "[警告] requirements.txt 不存在，請確認專案路徑"
fi