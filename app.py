from flask import Flask, render_template, request, jsonify
import requests
import os
import base64
import random
import tempfile
import threading
import ffmpeg

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

# Настройки видео
RESOLUTION = 720  # 1:1
BITRATE = "2500k"

def upload_media(file, filename=None):
    """Загрузка файла в WordPress"""
    if not file:
        return None, None
    filename = filename or file.filename
    files = {"file": (filename, file, "video/mp4" if filename.endswith(".mp4") else file.content_type)}
    response = requests.post(WP_MEDIA_URL, headers=HEADERS, files=files)
    if response.status_code == 201:
        return response.json().get("id"), response.json().get("source_url")
    return None, None

def convert_and_crop_video(video_url, output_filename):
    """Конвертация видео"""
    try:
        temp_output = os.path.join(tempfile.gettempdir(), output_filename)
        temp_input = tempfile.NamedTemporaryFile(delete=False, suffix=".mov")

        # Скачиваем MOV
        with requests.get(video_url, stream=True) as r:
            with open(temp_input.name, "wb") as f:
                for chunk in r.iter_content(1024):
                    f.write(chunk)

        # Проверяем параметры видео
        probe = ffmpeg.probe(temp_input.name)
        video_stream = next((stream for stream in probe["streams"] if stream["codec_type"] == "video"), None)
        width, height = int(video_stream["width"]), int(video_stream["height"])

        # Обрезка видео
        crop_size = min(width, height)
        x_offset = (width - crop_size) // 2
        y_offset = (height - crop_size) // 2

        ffmpeg.input(temp_input.name).filter(
            "crop", crop_size, crop_size, x_offset, y_offset
        ).filter(
            "scale", RESOLUTION, RESOLUTION
        ).output(
            temp_output, vcodec="libx264", acodec="aac", bitrate=BITRATE
        ).run(overwrite_output=True)

        return temp_output
    except Exception as e:
        print(f"Ошибка конвертации: {e}")
        return None

def async_convert_and_upload(video_url, output_filename, product_id):
    """Фоновая обработка видео"""
    converted_video_path = convert_and_crop_video(video_url, output_filename)
    if converted_video_path:
        with open(converted_video_path, "rb") as converted_video:
            video_id, video_url = upload_media(converted_video, filename=output_filename)
            update_product_video(product_id, video_id)

def update_product_video(product_id, video_id):
    """Обновление товара с MP4"""
    url = f"{WC_API_URL}/products/{product_id}"
    params = {"consumer_key": WC_CONSUMER_KEY, "consumer_secret": WC_CONSUMER_SECRET}
    data = {"meta_data": [{"key": "_product_video_gallery", "value": video_id}]}
    requests.put(url, json=data, params=params)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/add-product", methods=["POST"])
def add_product():
    try:
        category_id = request.form.get("category")
        weight = request.form.get("weight")
        price = request.form.get("price")
        image = request.files.get("image")
        video = request.files.get("video")

        if not category_id or not weight or not price:
            return jsonify({"status": "error", "message": "❌ Обязательные поля не заполнены"}), 400

        product_name = f"Product-{random.randint(1000, 9999)}"
        product_slug = f"product-{random.randint(1000, 9999)}"

        # Загружаем изображение
        image_id, _ = upload_media(image) if image else (None, None)

        # Создаём товар в WooCommerce
        product_data = {
            "name": product_name,
            "slug": product_slug,
            "type": "simple",
            "regular_price": price,
            "categories": [{"id": int(category_id)}],
            "description": f"Товар {product_name}, вес {weight}г.",
            "images": [{"id": image_id}],
        }
        url = f"{WC_API_URL}/products"
        params = {"consumer_key": WC_CONSUMER_KEY, "consumer_secret": WC_CONSUMER_SECRET}
        response = requests.post(url, json=product_data, params=params)

        if response.status_code == 201:
            product_id = response.json().get("id")

            # Загружаем MOV
            video_id, video_url = upload_media(video) if video else (None, None)

            # Запускаем конвертацию в фоне
            if video_url:
                output_filename = f"{product_name.replace(' ', '_')}-{product_slug}.mp4"
                threading.Thread(target=async_convert_and_upload, args=(video_url, output_filename, product_id)).start()

            return jsonify({"status": "success", "message": "✅ Товар добавлен!"})
        else:
            return jsonify({"status": "error", "message": "❌ Ошибка при добавлении товара."}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8080)
