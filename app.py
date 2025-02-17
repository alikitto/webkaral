from flask import Flask, render_template, request, jsonify
import requests
import os
import base64
import random
import tempfile
import threading
import ffmpeg

app = Flask(__name__)

# WooCommerce API данные
WC_API_URL = os.getenv("WC_API_URL", "https://karal.az/wp-json/wc/v3")
WC_CONSUMER_KEY = os.getenv("WC_CONSUMER_KEY")
WC_CONSUMER_SECRET = os.getenv("WC_CONSUMER_SECRET")

# WordPress API данные
WP_USERNAME = os.getenv("WP_USERNAME", "alikitto")
WP_PASSWORD = os.getenv("WP_PASSWORD", "HsbD0gjVhsj0Fb1KXrMx4nLQ")
WP_MEDIA_URL = "https://karal.az/wp-json/wp/v2/media"

# Авторизация для WordPress API
auth = base64.b64encode(f"{WP_USERNAME}:{WP_PASSWORD}".encode()).decode()
HEADERS = {"Authorization": f"Basic {auth}"}

# Настройки видео
RESOLUTION = 720  # Размер видео (1:1)
BITRATE = "2500k"  # Оптимальный битрейт

def upload_media(file, filename=None):
    """Загрузка файла в WordPress"""
    if not file:
        return None
    filename = filename or file.filename
    print(f"🔼 Загружаем файл: {filename}")
    files = {"file": (filename, file, "video/mp4" if filename.endswith(".mp4") else file.content_type)}
    response = requests.post(WP_MEDIA_URL, headers=HEADERS, files=files)
    if response.status_code == 201:
        media_id = response.json().get("id")
        return media_id
    else:
        print(f"⚠️ Ошибка загрузки: {response.text}")
        return None

def convert_and_crop_video(video, output_filename):
    """Конвертация MOV → MP4 с обрезкой 1:1"""
    try:
        temp_input = tempfile.NamedTemporaryFile(delete=False, suffix=".mov")
        temp_output = os.path.join(tempfile.gettempdir(), output_filename)
        video.save(temp_input.name)
        probe = ffmpeg.probe(temp_input.name)
        video_stream = next((stream for stream in probe["streams"] if stream["codec_type"] == "video"), None)
        width, height = int(video_stream["width"]), int(video_stream["height"])
        crop_size = min(width, height)
        x_offset = (width - crop_size) // 2
        y_offset = (height - crop_size) // 2
        ffmpeg.input(temp_input.name).filter(
            "crop", crop_size, crop_size, x_offset, y_offset
        ).filter(
            "scale", RESOLUTION, RESOLUTION
        ).output(
            temp_output, vcodec="libx264", acodec="aac", bitrate=BITRATE
        ).run_async()
        return temp_output
    except Exception as e:
        print(f"❌ Ошибка конвертации: {e}")
        return None

def async_convert_and_upload(video, output_filename, product_id):
    """Фоновая обработка видео"""
    converted_video_path = convert_and_crop_video(video, output_filename)
    if converted_video_path:
        with open(converted_video_path, "rb") as converted_video:
            video_id = upload_media(converted_video, filename=output_filename)
            print(f"✅ Видео загружено! ID: {video_id}")

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/add-product", methods=["POST"])
def add_product():
    try:
        category_id = request.form.get("category")
        weight = request.form.get("weight")
        price = request.form.get("price")
        sale_price = request.form.get("sale_price", "0")
        image = request.files.get("image")
        video = request.files.get("video")
        if not category_id or not weight or not price:
            return jsonify({"status": "error", "message": "❌ Обязательные поля не заполнены"}), 400
        product_name = f"Product-{random.randint(1000, 9999)}"
        product_slug = f"product-{random.randint(1000, 9999)}"
        image_id = upload_media(image) if image else None
        product_data = {
            "name": product_name,
            "slug": product_slug,
            "type": "simple",
            "regular_price": price,
            "sale_price": sale_price if sale_price != "0" else None,
            "categories": [{"id": int(category_id)}],
            "description": f"Товар {product_name}, вес {weight}г.",
            "images": [{"id": image_id}],
        }
        url = f"{WC_API_URL}/products"
        params = {"consumer_key": WC_CONSUMER_KEY, "consumer_secret": WC_CONSUMER_SECRET}
        response = requests.post(url, json=product_data, params=params)
        if response.status_code == 201:
            product_id = response.json().get("id")
            if video:
                output_filename = f"{product_name.replace(' ', '_')}-{product_slug}.mp4"
                threading.Thread(target=async_convert_and_upload, args=(video, output_filename, product_id)).start()
            return jsonify({"status": "success", "message": "✅ Товар добавлен!"})
        else:
            return jsonify({"status": "error", "message": "❌ Ошибка при добавлении товара."}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8080)
