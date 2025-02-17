from flask import Flask, render_template, request, jsonify
import requests
import os
import base64
import random
import tempfile
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

# Авторизация WordPress API
auth = base64.b64encode(f"{WP_USERNAME}:{WP_PASSWORD}".encode()).decode()
HEADERS = {"Authorization": f"Basic {auth}"}

# Настройки видео
RESOLUTION = 720
BITRATE = "2500k"

# Загрузка файла в WordPress
def upload_media(file, filename=None):
    if not file:
        print("❌ Ошибка: Файл отсутствует!")
        return None

    filename = filename or file.filename
    print(f"🔄 Загружаем файл: {filename}")

    files = {"file": (filename, file, "video/mp4" if filename.endswith(".mp4") else file.content_type)}
    response = requests.post(WP_MEDIA_URL, headers=HEADERS, files=files)

    if response.status_code == 201:
        media_id = response.json().get("id")
        print(f"✅ Файл загружен! ID: {media_id}")
        return media_id
    else:
        print(f"❌ Ошибка загрузки: {response.text}")
        return None

# Конвертация и центрирование видео
def convert_and_crop_video(video, output_filename):
    try:
        temp_input = tempfile.NamedTemporaryFile(delete=False, suffix=".mov")
        temp_output = os.path.join(tempfile.gettempdir(), output_filename)

        print(f"🔄 Сохраняем видео {video.filename} во временный файл {temp_input.name}")
        video.save(temp_input.name)

        print("🔄 Начинаем конвертацию и центрирование видео...")

        # Обрезка видео по центру
        ffmpeg.input(temp_input.name).filter(
            "crop", f"min(iw,ih)", f"min(iw,ih)", f"(iw-min(iw,ih))/2", f"(ih-min(iw,ih))/2"
        ).filter(
            "scale", RESOLUTION, RESOLUTION
        ).output(
            temp_output, vcodec="libx264", acodec="aac", bitrate=BITRATE
        ).run(overwrite_output=True)

        print(f"✅ Конвертация завершена: {temp_output}")
        return temp_output
    except Exception as e:
        print(f"❌ Ошибка конвертации видео: {e}")
        return None

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/add-product", methods=["POST"])
def add_product():
    try:
        category_id = request.form.get("category")
        price = request.form.get("price")
        weight = request.form.get("weight")
        image = request.files.get("image")
        video = request.files.get("video")

        if not category_id or not weight or not price:
            return jsonify({"status": "error", "message": "❌ Обязательные поля не заполнены"}), 400

        image_id = upload_media(image) if image else None
        if not image_id:
            return jsonify({"status": "error", "message": "❌ Ошибка загрузки изображения"}), 400

        video_id = None
        if video:
            output_filename = f"product_{random.randint(1000, 9999)}.mp4"
            converted_video_path = convert_and_crop_video(video, output_filename)
            if converted_video_path:
                with open(converted_video_path, "rb") as converted_video:
                    video_id = upload_media(converted_video, filename=output_filename)

        product_data = {
            "name": "Новый товар",
            "regular_price": price,
            "images": [{"id": image_id}],
            "meta_data": [{"key": "_weight", "value": weight}]
        }

        if video_id:
            product_data["meta_data"].append({"key": "_product_video_gallery", "value": video_id})

        response = requests.post(WC_API_URL + "/products", json=product_data,
                                 params={"consumer_key": WC_CONSUMER_KEY, "consumer_secret": WC_CONSUMER_SECRET})

        print(f"Ответ от WooCommerce: {response.status_code} - {response.text}")

        return jsonify({"status": "success", "message": "✅ Товар добавлен!"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8080)
