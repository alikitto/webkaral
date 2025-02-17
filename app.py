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

# WordPress API данные (для загрузки изображений и видео)
WP_USERNAME = os.getenv("WP_USERNAME", "alikitto")
WP_PASSWORD = os.getenv("WP_PASSWORD", "HsbD0gjVhsj0Fb1KXrMx4nLQ")
WP_MEDIA_URL = "https://karal.az/wp-json/wp/v2/media"

# Авторизация для WordPress API
auth = base64.b64encode(f"{WP_USERNAME}:{WP_PASSWORD}".encode()).decode()
HEADERS = {"Authorization": f"Basic {auth}"}

# Настройки видео
RESOLUTION = 720  # Размер кадра (720x720)
BITRATE = "2000k"  # Качество видео
THREADS = 1  # Ограничение нагрузки на сервер

# Функция загрузки файла в WordPress
def upload_media(file, filename=None):
    if not file:
        return None

    filename = filename or file.filename
    print(f"Загружаем файл: {filename}")

    files = {"file": (filename, file, "video/mp4" if filename.endswith(".mp4") else file.content_type)}
    response = requests.post(WP_MEDIA_URL, headers=HEADERS, files=files)

    if response.status_code == 201:
        media_id = response.json().get("id")
        media_url = response.json().get("source_url")
        print(f"Файл загружен успешно! ID: {media_id}, URL: {media_url}")
        return media_id, media_url
    else:
        print(f"Ошибка загрузки файла: {response.text}")
        return None, None

# Фоновая обработка видео
def process_video(video_url, media_id, output_filename):
    try:
        temp_output = os.path.join(tempfile.gettempdir(), output_filename)

        print(f"Загружаем видео {video_url} для обработки...")
        temp_input = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
        with requests.get(video_url, stream=True) as r:
            with open(temp_input.name, "wb") as f:
                for chunk in r.iter_content(1024):
                    f.write(chunk)

        print("Начинаем конвертацию видео...")
        probe = ffmpeg.probe(temp_input.name)
        video_stream = next((stream for stream in probe["streams"] if stream["codec_type"] == "video"), None)
        width, height = int(video_stream["width"]), int(video_stream["height"])

        # Обрезка видео в 1:1
        crop_size = min(width, height)
        x_offset = (width - crop_size) // 2
        y_offset = (height - crop_size) // 2

        ffmpeg.input(temp_input.name).filter("crop", crop_size, crop_size, x_offset, y_offset).filter("scale", RESOLUTION, RESOLUTION).output(temp_output, vcodec="libx264", acodec="aac", bitrate=BITRATE, threads=THREADS).run(overwrite_output=True)

        print(f"Конвертация завершена! Файл сохранён: {temp_output}")

        # Загрузка обработанного видео в WordPress (замена оригинального файла)
        with open(temp_output, "rb") as converted_video:
            upload_media(converted_video, filename=output_filename)

        print("Видео обновлено в WordPress!")

    except Exception as e:
        print(f"Ошибка обработки видео: {e}")

# Добавление товара
@app.route("/add-product", methods=["POST"])
def add_product():
    try:
        category_id = request.form.get("category")
        weight = request.form.get("weight")
        gold_purity_id = request.form.get("gold_purity")
        price = request.form.get("price")
        sale_price = request.form.get("sale_price", "0")
        image = request.files.get("image")
        video = request.files.get("video")

        if not category_id or not weight or not price:
            return jsonify({"status": "error", "message": "❌ Обязательные поля не заполнены"}), 400

        # Преобразуем ID пробы в текст
        gold_purity = GOLD_PURITY_MAP.get(gold_purity_id, "585 (14K)")

        # Генерируем название и slug
        category_info = CATEGORY_DATA.get(category_id, {})
        product_name = random.choice(category_info["name"]) if isinstance(category_info["name"], list) else category_info["name"]
        product_slug = f"{category_info['slug']}-{random.randint(1000, 9999)}"

        print(f"Создаём товар: {product_name}, Slug: {product_slug}, Вес: {weight}, Цена: {price}")

        # Загружаем изображение
        image_id, _ = upload_media(image) if image else (None, None)
        if not image_id:
            return jsonify({"status": "error", "message": "❌ Ошибка загрузки изображения"}), 400

        # Загружаем оригинальное видео
        video_id, video_url = upload_media(video) if video else (None, None)

        # Фоновая обработка видео
        if video_url:
            output_filename = f"{product_name.replace(' ', '_')}-{product_slug}.mp4"
            threading.Thread(target=process_video, args=(video_url, video_id, output_filename)).start()

        # Данные для WooCommerce
        product_data = {
            "name": product_name,
            "slug": product_slug,
            "type": "simple",
            "regular_price": price,
            "sale_price": sale_price if sale_price != "0" else None,
            "categories": [{"id": int(category_id)}],
            "description": f"Yeni {product_name} modeli. Çəkisi: {weight}g, Əyarı: {gold_purity}",
            "images": [{"id": image_id}],
            "attributes": [
                {"id": 2, "options": [gold_purity], "visible": True, "variation": False}
            ],
            "meta_data": [{"key": "_weight", "value": weight}, {"key": "_product_video_autoplay", "value": "on"}]
        }

        if video_id:
            product_data["meta_data"].append({"key": "_product_video_gallery", "value": video_id})

        response = requests.post(f"{WC_API_URL}/products", json=product_data, params={"consumer_key": WC_CONSUMER_KEY, "consumer_secret": WC_CONSUMER_SECRET})

        return jsonify({"status": "success", "message": "✅ Товар успешно добавлен!"})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8080)
