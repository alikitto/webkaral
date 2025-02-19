from flask import Flask, render_template, request, jsonify
import requests
import os
from ftplib import FTP
import io
import base64
import random
import tempfile
import ffmpeg
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
BITRATE = "1500k"  # Уменьшил для скорости
RESOLUTION_VIDEO = (720, 720)

# ------------------- ФУНКЦИИ -------------------
def upload_file_via_ftp(file_path, filename_slug, ftp_dir):
    """ Загружает файл на FTP сервер """
    try:
        print("📌 [DEBUG] Подключаемся к FTP серверу...")

        with FTP(FTP_HOST) as ftp:
            ftp.login(FTP_USER, FTP_PASS)
            ftp.cwd(ftp_dir)

            print(f"📌 [DEBUG] Загружаем файл {filename_slug} ...")

            with open(file_path, "rb") as file:
                ftp.storbinary(f"STOR {filename_slug}", file)

        print(f"✅ Файл успешно загружен по FTP: {ftp_dir}{filename_slug}")
        return f"https://karal.az{ftp_dir}{filename_slug}"
    except Exception as e:
        print(f"❌ Ошибка при загрузке файла по FTP: {e}")
        return None

def convert_video_to_mp4(video, filename_slug):
    """Конвертирует MOV в MP4 без изменения размера"""
    try:
        temp_input = tempfile.NamedTemporaryFile(delete=False, suffix=".mov")
        temp_output = os.path.join(tempfile.gettempdir(), f"{filename_slug}.mp4")

        print(f"🔄 Сохраняем оригинальное MOV {video.filename} во временный файл {temp_input.name}")
        video.save(temp_input.name)

        print("🔄 Конвертируем в MP4 без изменения размера...")
        ffmpeg.input(temp_input.name).output(
            temp_output, vcodec="libx264", acodec="aac", bitrate=BITRATE
        ).run(overwrite_output=True)

        print(f"✅ Конвертация завершена: {temp_output}")
        return temp_output
    except Exception as e:
        print(f"❌ Ошибка конвертации видео: {e}")
        return None

def convert_and_crop_video(video, filename_slug):
    """ Обрезка видео в 1:1 и конвертация в MP4 """
    try:
        temp_input = tempfile.NamedTemporaryFile(delete=False, suffix=".mov")
        temp_output = os.path.join(tempfile.gettempdir(), f"{filename_slug}_cropped.mp4")

        print(f"🔄 Сохраняем MOV {video.filename} во временный файл {temp_input.name}")
        video.save(temp_input.name)

        print("🔄 Обрезаем и конвертируем в 1:1 (720x720)...")
        ffmpeg.input(temp_input.name).filter(
            "crop", "min(iw,ih)", "min(iw,ih)", "(iw-min(iw,ih))/2", "(ih-min(iw,ih))/2"
        ).filter(
            "scale", RESOLUTION_VIDEO[0], RESOLUTION_VIDEO[1]
        ).output(
            temp_output, vcodec="libx264", acodec="aac", bitrate=BITRATE
        ).run(overwrite_output=True)

        print(f"✅ Конвертация и обрезка завершены: {temp_output}")
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
    return render_template("index.html", categories=CATEGORY_DATA)

@app.route("/add-product", methods=["POST"])
def add_product():
    try:
        print("📌 [INFO] Получен запрос на добавление товара")

        category_id = request.form.get("category")
        weight = request.form.get("weight")
        price = request.form.get("price")
        video = request.files.get("video")

        if not category_id or not weight or not price:
            print("❌ [ERROR] Не заполнены обязательные поля")
            return jsonify({"status": "error", "message": "❌ Обязательные поля не заполнены"}), 400

        product_slug = f"product-{random.randint(1000, 9999)}"

        # 1️⃣ Конвертируем MOV в MP4 (без изменений) и загружаем на FTP
        original_video_url = None
        if video:
            original_mp4 = convert_video_to_mp4(video, product_slug)
            if original_mp4:
                original_video_url = upload_file_via_ftp(original_mp4, f"{product_slug}.mp4", FTP_MOV_DIR)

        # 2️⃣ Конвертируем и загружаем обрезанное видео (720x720) в WordPress
        video_id = None
        if video:
            cropped_video_path = convert_and_crop_video(video, product_slug)
            if cropped_video_path:
                video_id = upload_media(cropped_video_path, f"{product_slug}.mp4")

        # 3️⃣ Создаём товар в WooCommerce
        product_data = {
            "name": f"Product {product_slug}",
            "slug": product_slug,
            "regular_price": price,
            "categories": [{"id": int(category_id)}],
            "meta_data": [
                {"key": "_weight", "value": weight},
                {"key": "_original_video_url", "value": original_video_url} if original_video_url else {},
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
        print(f"❌ [ERROR] Исключение в add_product: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
