from flask import Flask, render_template, request, jsonify
import os
import base64
import random
import tempfile
import requests
import mimetypes
import ffmpeg
from PIL import Image, ImageOps

app = Flask(__name__)

# Устанавливаем новую целевую размерность
RESOLUTION_IMAGE = (900, 900)
RESOLUTION_VIDEO = (900, 900)
BITRATE = "2500k"

# Данные для API WooCommerce и WordPress
WC_API_URL = os.getenv("WC_API_URL", "https://karal.az/wp-json/wc/v3")
WC_CONSUMER_KEY = os.getenv("WC_CONSUMER_KEY")
WC_CONSUMER_SECRET = os.getenv("WC_CONSUMER_SECRET")

WP_USERNAME = os.getenv("WP_USERNAME", "alikitto")
WP_PASSWORD = os.getenv("WP_PASSWORD", "HsbD0gjVhsj0Fb1KXrMx4nLQ")
WP_MEDIA_URL = "https://karal.az/wp-json/wp/v2/media"

auth = base64.b64encode(f"{WP_USERNAME}:{WP_PASSWORD}".encode()).decode()
HEADERS = {"Authorization": f"Basic {auth}"}

# Обрезка изображения до 900x900
def process_image(image, filename_slug):
    """ Обрезает изображение до 900x900 и сохраняет """
    try:
        temp_input = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
        temp_output = os.path.join(tempfile.gettempdir(), f"{filename_slug}.jpg")

        image.save(temp_input.name)
        img = Image.open(temp_input.name)

        # Автоматический поворот по EXIF-данным
        img = ImageOps.exif_transpose(img)

        width, height = img.size

        # Обрезка в 1:1 (центрируем по вертикали и горизонтали)
        crop_size = min(width, height)
        left = (width - crop_size) // 2
        top = (height - crop_size) // 2
        right = left + crop_size
        bottom = top + crop_size
        img = img.crop((left, top, right, bottom))

        # Масштабируем в 900x900
        img = img.resize(RESOLUTION_IMAGE, Image.LANCZOS)
        img.save(temp_output, format="JPEG")

        return temp_output
    except Exception as e:
        print(f"❌ Ошибка обработки фото: {e}")
        return None

# Обрезка видео до 900x900
def convert_and_crop_video(video, output_filename):
    """ Обрезка видео до 900x900 и конвертация в MP4 """
    try:
        temp_input = tempfile.NamedTemporaryFile(delete=False, suffix=".mov")
        temp_output = os.path.join(tempfile.gettempdir(), output_filename)

        print(f"🔄 Сохраняем видео {video.filename} во временный файл {temp_input.name}")
        video.save(temp_input.name)

        print("🔄 Начинаем конвертацию видео в 900x900...")

        ffmpeg.input(temp_input.name).filter(
            "crop", "min(iw,ih)", "min(iw,ih)", "(iw-min(iw,ih))/2", "(ih-min(iw,ih))/2"
        ).filter(
            "scale", 900, 900
        ).output(
            temp_output, vcodec="libx264", acodec="aac", bitrate=BITRATE
        ).run(overwrite_output=True)

        print(f"✅ Конвертация завершена: {temp_output}")
        return temp_output
    except Exception as e:
        print(f"❌ Ошибка конвертации видео: {e}")
        return None

@app.route("/add-product", methods=["POST"])
def add_product():
    try:
        print("📌 [INFO] Получен запрос на добавление товара")

        category_id = request.form.get("category")
        weight = request.form.get("weight")
        price = request.form.get("price")
        sale_price = request.form.get("sale_price", "0")
        image = request.files.get("image")
        video = request.files.get("video")

        if not category_id or not weight or not price:
            return jsonify({"status": "error", "message": "❌ Обязательные поля не заполнены"}), 400

        product_slug = f"product-{random.randint(1000, 9999)}"

        # Обработка изображения
        image_id = None
        if image:
            processed_image = process_image(image, product_slug)
            if processed_image:
                with open(processed_image, "rb") as img_file:
                    image_id = upload_media(img_file, filename=f"{product_slug}.jpg")

        # Обработка видео
        video_id = None
        if video:
            output_filename = f"{product_slug}.mp4"
            converted_video_path = convert_and_crop_video(video, output_filename)
            if converted_video_path:
                with open(converted_video_path, "rb") as converted_video:
                    video_id = upload_media(converted_video, filename=output_filename)

        return jsonify({"status": "success", "message": "✅ Товар добавлен!"})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
