import os
import subprocess
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# Пути к API WooCommerce
WC_API_URL = os.getenv("WC_API_URL", "https://karal.az/wp-json/wc/v3")
WC_CONSUMER_KEY = os.getenv("WC_CONSUMER_KEY")
WC_CONSUMER_SECRET = os.getenv("WC_CONSUMER_SECRET")

# Пути к API WordPress для загрузки файлов
WP_USERNAME = os.getenv("WP_USERNAME", "alikitto")
WP_PASSWORD = os.getenv("WP_PASSWORD", "HsbD0gjVhsj0Fb1KXrMx4nLQ")
WP_MEDIA_URL = "https://karal.az/wp-json/wp/v2/media"

# Функция загрузки видео в WordPress
def upload_video(video_path):
    """ Загружает видео в медиатеку WordPress и возвращает ID файла """
    with open(video_path, "rb") as file:
        files = {"file": (os.path.basename(video_path), file, "video/mp4")}
        response = requests.post(WP_MEDIA_URL, auth=(WP_USERNAME, WP_PASSWORD), files=files)

    if response.status_code == 201:
        return response.json().get("id")  # Получаем ID загруженного видео
    return None

# Функция конвертации MOV → MP4 через FFmpeg
def convert_to_mp4(input_path, output_path):
    """ Конвертирует видео MOV → MP4 через FFmpeg """
    try:
        command = [
            "ffmpeg", "-i", input_path, 
            "-vcodec", "libx264", "-acodec", "aac",
            "-strict", "experimental", output_path
        ]
        subprocess.run(command, check=True)
        return output_path
    except subprocess.CalledProcessError:
        return None

@app.route("/upload-video", methods=["POST"])
def upload_video_api():
    """ Загружает видео и конвертирует его в MP4 перед отправкой в WordPress """
    try:
        video = request.files.get("video")
        if not video:
            return jsonify({"status": "error", "message": "Файл видео не загружен"}), 400
        
        input_path = f"/tmp/{video.filename}"
        output_path = f"/tmp/converted.mp4"

        video.save(input_path)  # Сохраняем исходный MOV
        converted_path = convert_to_mp4(input_path, output_path)

        if not converted_path:
            return jsonify({"status": "error", "message": "Ошибка конвертации видео"}), 500

        # Загружаем в WP и получаем ID
        video_id = upload_video(converted_path)
        if not video_id:
            return jsonify({"status": "error", "message": "Ошибка загрузки в WordPress"}), 500

        return jsonify({"status": "success", "video_id": video_id})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8080)
