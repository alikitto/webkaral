from flask import Flask, render_template, request, jsonify
import requests
import os
import base64
import random
import tempfile
import subprocess

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
HEADERS = {"Authorization": f"Basic {auth}"}

# Категории товаров
CATEGORY_DATA = {
    "126": {"name": "Qızıl üzük", "slug": "qizil-uzuk"},
    "132": {"name": "Qızıl sırğa", "slug": "qizil-sirqa"},
    "140": {"name": "Qızıl sep", "slug": "qizil-sep"},
    "138": {"name": "Qızıl qolbaq", "slug": "qizil-qolbaq"},
    "144": {"name": ["Qızıl dəst", "Qızıl komplekt"], "slug": "qizil-komplekt-dest"}
}

# Функция загрузки файла в WordPress
def upload_media(file_path, filename, content_type):
    """ Загружает файл (изображение или видео) в WordPress и возвращает ID """
    with open(file_path, "rb") as file:
        files = {"file": (filename, file, content_type)}
        response = requests.post(WP_MEDIA_URL, headers=HEADERS, files=files)

    if response.status_code == 201:
        return response.json().get("id")
    else:
        print(f"Ошибка загрузки файла: {response.text}")
        return None

# Функция конвертации видео с `ffmpeg`
def convert_video(input_path, output_path):
    """Конвертирует видео в MP4 с нужным разрешением и битрейтом"""
    try:
        command = [
            "ffmpeg", "-y", "-i", input_path,
            "-vf", "scale=720:1280:force_original_aspect_ratio=decrease",  # Поддержка 9:16 (для вертикальных видео)
            "-c:v", "libx264", "-preset", "fast", "-b:v", "1000k",
            "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart",
            output_path
        ]
        subprocess.run(command, check=True)
        return output_path
    except Exception as e:
        print(f"Ошибка конвертации видео: {e}")
        return None

# Главная страница
@app.route("/")
def home():
    return render_template("index.html", categories=CATEGORY_DATA)

# Добавление товара
@app.route("/add-product", methods=["POST"])
def add_product():
    try:
        # Получаем данные из формы
        category_id = request.form.get("category")
        weight = request.form.get("weight")
        price = request.form.get("price")
        sale_price = request.form.get("sale_price", "0")
        image = request.files.get("image")
        video = request.files.get("video")

        # Генерируем название и slug
        category_info = CATEGORY_DATA.get(category_id, {})
        product_name = random.choice(category_info["name"]) if isinstance(category_info["name"], list) else category_info["name"]
        product_slug = f"{category_info['slug']}-{random.randint(1000, 9999)}"

        # Загружаем изображение
        image_id = None
        if image:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_img:
                image.save(temp_img.name)
                image_id = upload_media(temp_img.name, image.filename, "image/jpeg")

        # Загружаем и конвертируем видео
        video_id = None
        if video:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mov") as temp_video:
                video.save(temp_video.name)
                temp_output = temp_video.name.replace(".mov", ".mp4")

                # Конвертация видео
                converted_video_path = convert_video(temp_video.name, temp_output)
                if converted_video_path:
                    video_id = upload_media(converted_video_path, f"{product_name}.mp4", "video/mp4")

        # Данные для WooCommerce
        product_data = {
            "name": product_name,
            "slug": product_slug,
            "type": "simple",
            "regular_price": price,
            "sale_price": sale_price if sale_price != "0" else None,
            "categories": [{"id": int(category_id)}],
            "description": f"Yeni {product_name} modeli. Çəkisi: {weight}g",
            "images": [{"id": image_id}] if image_id else [],
            "meta_data": [
                {"key": "_weight", "value": weight},
                {"key": "_product_video_autoplay", "value": "on"}
            ]
        }

        if video_id:
            product_data["meta_data"].append({"key": "_product_video_gallery", "value": video_id})

        # Отправляем товар в WooCommerce
        url = f"{WC_API_URL}/products"
        params = {"consumer_key": WC_CONSUMER_KEY, "consumer_secret": WC_CONSUMER_SECRET}
        response = requests.post(url, json=product_data, params=params)

        if response.status_code == 201:
            return jsonify({"status": "success", "message": "✅ Товар успешно добавлен!"})
        else:
            return jsonify({"status": "error", "message": "❌ Ошибка при добавлении товара.", "details": response.text}), 400

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8080)
