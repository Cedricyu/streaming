from flask import Flask, send_from_directory, request, jsonify, abort
import os
import random  # <--- 新增
import time

app = Flask(__name__)
VIDEO_FOLDER = os.path.abspath(".")

@app.route("/video/get")
def get_video():
    filename = request.args.get("id", None)
    if not filename or not filename.endswith(".mp4"):
        abort(400)
    path = os.path.join(VIDEO_FOLDER, filename)
    if not os.path.exists(path):
        abort(404)
    return send_from_directory(VIDEO_FOLDER, filename, as_attachment=True, mimetype="video/mp4")

@app.route("/video/list_pending")
def list_pending():
    files = [f for f in os.listdir(VIDEO_FOLDER) if f.endswith(".mp4")]
    pending = []
    for f in files:
        # 如果是 ai_stream.mp4，用 random 假裝有時還沒好
        if f == "ai_stream.mp4":
            # 50% 機率假裝還沒好
            if random.random() < 0.5:
                print(f"[DEBUG] pretend {f} is not ready yet (pending)")
                continue
        pending.append(f)
    return jsonify({"videos": pending})

if __name__ == "__main__":
    app.run(port=8081, debug=True)
