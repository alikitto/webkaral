from flask import Flask, render_template, request, jsonify
import requests
import os
from ftplib import FTP
import io
import base64
import random
import tempfile
import ffmpeg
import threading  # Добавлено для фоновой загрузки
from PIL import Image, ImageOps

app = Flask(__name__)

# WooCommerce API
WC_API_URL = os.getenv("WC_API_URL", "https://karal.az/wp-json/wc/v3")
WC_CONSUMER_KEY = os.getenv("WC_CONSUMER_KEY")
WC_CONSUMER_SECRET = os.getenv("WC_CONSUMER_SECRET")

# WordPress API
WP_USERNAME = os.getenv("WP_USERNAME", "alikitto")
WP_PASSWORD = os.getenv("WP_PASSWORD", "HsbD0gjVhsj0Fb1KXrMx4nLQ")
WP_MEDIA_URL = "https://karal.az/wp-json/wp/v2/media"

# Авторизация
auth = base64.b64encode(f"{WP_USERNAME}:{WP_PASSWORD}".encode()).decode()
HEADERS = {"Authorization": f"Basic {auth}"}

# ДАННЫЕ ДЛЯ FTP-ДОСТУПА
FTP_HOST = "116.202.196.92"
FTP_USER = "pypy777"
FTP_PASS = "jN2wR7rD2f"
FTP_MOV_DIR = "/wp-content/uploads/original_videos/"  # Путь для MOV

# Настройки видео
BITRATE = "1700k"  # Оптимизировано для скорости
RESOLUTION_VIDEO = (600, 600)  # Новый размер

# ------------------- ФУНКЦИИ -------------------
def upload_file_via_ftp(file_path, filename_slug, ftp_dir):
    """ Фоновая загрузка файла на FTP сервер """
    def ftp_upload():
        try:
            print("📌 [DEBUG] Подключаемся к FTP серверу...")

            with FTP(FTP_HOST) as ftp:
                ftp.login(FTP_USER, FTP_PASS)
                ftp.cwd(ftp_dir)

                print(f"📌 [DEBUG] Загружаем файл {filename_slug} ...")

                with open(file_path, "rb") as file:
                    ftp.storbinary(f"STOR {filename_slug}", file, 1024 * 64)  # Быстрая передача

            print(f"✅ Файл успешно загружен по FTP: {ftp_dir}{filename_slug}")
        except Exception as e:
            print(f"❌ Ошибка при загрузке файла по FTP: {e}")

    # Запускаем загрузку в фоне
    threading.Thread(target=ftp_upload, daemon=True).start()

def convert_video_to_mp4(video, filename_slug):
    """ Конвертирует MOV в MP4 (600x600, 1700k) """
    try:
        temp_input = tempfile.NamedTemporaryFile(delete=False, suffix=".mov")
        temp_output = os.path.join(tempfile.gettempdir(), f"{filename_slug}.mp4")

        print(f"🔄 Сохраняем оригинальное MOV {video.filename} во временный файл {temp_input.name}")
        video.save(temp_input.name)

        print("🔄 Конвертируем в MP4 (600x600, 1700k)...")
        ffmpeg.input(temp_input.name).filter(
            "scale", RESOLUTION_VIDEO[0], RESOLUTION_VIDEO[1]
        ).output(
            temp_output, vcodec="libx264", acodec="aac", bitrate=BITRATE
        ).run(overwrite_output=True)

        print(f"✅ Конвертация завершена: {temp_output}")
        return temp_output
    except Exception as e:
        print(f"❌ Ошибка конвертации видео: {e}")
        return None

def upload_media(file_path, filename):
    """Загружает обработанный файл в WordPress и возвращает ID"""
    try:
        with open(file_path, "rb") as file:
            mime_type = "video/mp4" if filename.endswith(".mp4") else "image/jpeg"
            files = {"file": (filename, file, mime_type)}
            response = requests.post(WP_MEDIA_URL, headers=HEADERS, files=files)

            if response.status_code == 201:
                media_id = response.json().get("id")
                print(f"✅ Файл загружен в WordPress! ID: {media_id}")
                return media_id
            else:
                print(f"❌ Ошибка загрузки в WordPress: {response.text}")
                return None
    except Exception as e:
        print(f"❌ Ошибка загрузки файла в WordPress: {e}")
        return None

# ------------------- ОБРАБОТКА ТОВАРА -------------------
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/add-product", methods=["POST"])
def add_product():
    try:
        print("📌 [INFO] Получен запрос на добавление товара")

        category_id = request.form.get("category")
        weight = request.form.get("weight")
        price = request.form.get("price")
        video = request.files.get("video")

        if not category_id or not weight or not price:
            return jsonify({"status": "error", "message": "❌ Обязательные поля не заполнены"}), 400

        product_slug = f"product-{random.randint(1000, 9999)}"

        # 1️⃣ Конвертируем MOV в MP4 (600x600, 1700k) и сразу добавляем в товар
        video_id = None
        if video:
            converted_mp4 = convert_video_to_mp4(video, product_slug)
            if converted_mp4:
                video_id = upload_media(converted_mp4, f"{product_slug}.mp4")

        # 2️⃣ Загружаем MOV в FTP **фоново** (НЕ задерживает процесс)
        if video:
            temp_input = tempfile.NamedTemporaryFile(delete=False, suffix=".mov")
            video.save(temp_input.name)
            upload_file_via_ftp(temp_input.name, f"{product_slug}.mov", FTP_MOV_DIR)

        print(f"✅ Загруженное видео ID: {video_id}")

        # 3️⃣ Создаём товар в WooCommerce
        product_data = {
            "name": f"Product {product_slug}",
            "slug": product_slug,
            "regular_price": price,
            "categories": [{"id": int(category_id)}],
            "meta_data": [
                {"key": "_weight", "value": weight},
                {"key": "_product_video_gallery", "value": video_id} if video_id else {}
            ]
        }

        response = requests.post(
            WC_API_URL + "/products",
            json=product_data,
            params={"consumer_key": WC_CONSUMER_KEY, "consumer_secret": WC_CONSUMER_SECRET}
        )

        print(f"📌 [INFO] WooCommerce ответ: {response.status_code}")
        return jsonify({"status": "success" if response.status_code == 201 else "error"})

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
