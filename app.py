from flask import Flask, render_template, request, jsonify
import requests
import base64
import random
import tempfile
from moviepy.editor import VideoFileClip  # ДЛЯ КОНВЕРТАЦИИ MOV → MP4
import os

try:
    import moviepy.editor
    print("✅ MoviePy установлен!")
except ModuleNotFoundError:
    print("❌ MoviePy НЕ установлен! Устанавливаем...")
    os.system("pip install moviepy ffmpeg imageio[ffmpeg] numpy")

app = Flask(__name__)

# WooCommerce API данные
WC_API_URL = os.getenv("WC_API_URL", "https://karal.az/wp-json/wc/v3")
WC_CONSUMER_KEY = os.getenv("WC_CONSUMER_KEY")
WC_CONSUMER_SECRET = os.getenv("WC_CONSUMER_SECRET")

# WordPress API данные (для загрузки изображений и видео)
WP_USERNAME = os.getenv("WP_USERNAME", "alikitto")
WP_PASSWORD = os.getenv("WP_PASSWORD", "HsbD0gjVhsj0Fb1KXrMx4nLQ")
WP_MEDIA_URL = "https://karal.az/wp-json/wp/v2/media"

# Авторизация для WordPress API
auth = base64.b64encode(f"{WP_USERNAME}:{WP_PASSWORD}".encode()).decode()
HEADERS = {
    "Authorization": f"Basic {auth}"
}

# Функция конвертации MOV → MP4
def convert_mov_to_mp4(mov_file):
    """ Конвертирует MOV в MP4 и возвращает путь к MP4-файлу """
    try:
        temp_dir = tempfile.gettempdir()  # Временная папка
        mp4_path = os.path.join(temp_dir, f"{random.randint(1000,9999)}.mp4")
        
        # Конвертация видео
        clip = VideoFileClip(mov_file)
        clip.write_videofile(mp4_path, codec="libx264", audio_codec="aac")

        return mp4_path
    except Exception as e:
        print(f"Ошибка конвертации MOV → MP4: {e}")
        return None

# Функция загрузки файла (изображение или видео) в WordPress
def upload_media(file):
    """ Загружает файл (изображение или видео) в медиатеку WordPress и возвращает ID """

    # Если формат MOV, сначала конвертируем в MP4
    if file.filename.lower().endswith(".mov"):
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mov")
        file.save(temp_file.name)  # Сохраняем MOV во временный файл

        mp4_path = convert_mov_to_mp4(temp_file.name)
        if not mp4_path:
            return None  # Ошибка конвертации

        with open(mp4_path, "rb") as mp4_file:
            files = {"file": (f"{random.randint(1000,9999)}.mp4", mp4_file, "video/mp4")}
            response = requests.post(WP_MEDIA_URL, headers=HEADERS, files=files)

        os.remove(mp4_path)  # Удаляем временный MP4-файл
        os.remove(temp_file.name)  # Удаляем временный MOV-файл

    else:
        files = {"file": (file.filename, file.stream, file.content_type)}
        response = requests.post(WP_MEDIA_URL, headers=HEADERS, files=files)

    if response.status_code == 201:
        media_id = response.json().get("id")  # Получаем ID файла
        return media_id
    else:
        return None

# Добавление товара
@app.route("/add-product", methods=["POST"])
def add_product():
    try:
        # Получаем данные из формы
        video = request.files.get("video")  # Файл видео

        # Загружаем видео
        video_id = upload_media(video) if video else None

        # Данные для WooCommerce API
        product_data = {
            "meta_data": []
        }

        # Если есть видео, добавляем его в meta_data
        if video_id:
            product_data["meta_data"].append({"key": "_product_video_gallery", "value": video_id})
            product_data["meta_data"].append({"key": "_product_video_autoplay", "value": "on"})  # Автоплей

        # Отправляем товар в WooCommerce
        url = f"{WC_API_URL}/products"
        params = {"consumer_key": WC_CONSUMER_KEY, "consumer_secret": WC_CONSUMER_SECRET}
        response = requests.post(url, json=product_data, params=params)

        # Проверка ответа
        if response.status_code == 201:
            return jsonify({"status": "success", "message": "✅ Товар успешно добавлен!"})
        else:
            return jsonify({"status": "error", "message": "❌ Ошибка при добавлении товара.", "details": response.text}), 400

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8080)
