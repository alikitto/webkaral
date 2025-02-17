from flask import Flask, render_template, request, jsonify
import requests
import os
import base64
import random
import tempfile
import shutil
from moviepy import VideoFileClip

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

# Пробы золота (Əyar)
GOLD_PURITY_MAP = {
    "105": "585 (14K)",
    "106": "750 (18K)"
}

# Настройки видео
VIDEO_SETTINGS = {
    "aspect_ratio": "9:16",  # Выбрать 9:16, 1:1 или 4:5
    "resize_width": 720,  # Размер по ширине
    "bitrate": "1000k",  # Битрейт
}

# Функция загрузки медиа в WordPress
def upload_media(file_path, filename):
    """Загружает файл (изображение или видео) в медиатеку WordPress и возвращает ID"""
    if not os.path.exists(file_path):
        print(f"Ошибка: Файл {file_path} не найден!")
        return None

    print(f"Загружаем {filename} в WordPress... ({file_path})")
    with open(file_path, "rb") as file:
        files = {"file": (filename, file, "video/mp4" if filename.endswith(".mp4") else "image/jpeg")}
        response = requests.post(WP_MEDIA_URL, headers=HEADERS, files=files)

    if response.status_code == 201:
        media_id = response.json().get("id")
        print(f"Файл загружен успешно! ID: {media_id}")
        return media_id
    else:
        print(f"Ошибка загрузки файла: {response.text}")
        return None

# Функция конвертации MOV → MP4
def convert_mov_to_mp4(video):
    """Конвертация MOV в MP4 с изменением размера"""
    try:
        temp_input_path = os.path.join(tempfile.gettempdir(), video.filename)
        temp_output_path = temp_input_path.replace(".mov", ".mp4")

        # **Сохранение загруженного видео во временную папку**
        print(f"Сохраняем видео {video.filename} в {temp_input_path}")
        video.save(temp_input_path)

        # **Открываем файл в MoviePy**
        print("Начало конвертации MOV → MP4...")
        clip = VideoFileClip(temp_input_path)

        # **Выбор соотношения сторон**
        aspect_ratio = VIDEO_SETTINGS["aspect_ratio"]
        if aspect_ratio == "9:16":
            clip = clip.resize(height=1080)
        elif aspect_ratio == "1:1":
            clip = clip.crop(x_center=clip.w / 2, width=min(clip.w, clip.h))
        elif aspect_ratio == "4:5":
            clip = clip.crop(y_center=clip.h / 2, height=clip.w * 5 / 4)

        # **Сохранение с нужным битрейтом**
        clip.write_videofile(temp_output_path, codec="libx264", audio_codec="aac", bitrate=VIDEO_SETTINGS["bitrate"])
        print(f"Конвертация завершена! Файл сохранён: {temp_output_path}")

        return temp_output_path
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
        category_id = request.form.get("category")
        weight = request.form.get("weight")
        gold_purity_id = request.form.get("gold_purity")
        price = request.form.get("price")
        sale_price = request.form.get("sale_price", "0")
        image = request.files.get("image")
        video = request.files.get("video")

        if not category_id or not weight or not price:
            return jsonify({"status": "error", "message": "❌ Обязательные поля не заполнены"}), 400

        gold_purity = GOLD_PURITY_MAP.get(gold_purity_id, "585 (14K)")
        category_info = CATEGORY_DATA.get(category_id, {})
        product_name = random.choice(category_info["name"]) if isinstance(category_info["name"], list) else category_info["name"]
        product_slug = f"{category_info['slug']}-{random.randint(1000, 9999)}"

        print(f"Создаём товар: {product_name}, Slug: {product_slug}")

        # Загружаем изображение
        image_id = None
        if image:
            image_path = os.path.join(tempfile.gettempdir(), image.filename)
            image.save(image_path)
            image_id = upload_media(image_path, image.filename)

        # Загружаем видео
        video_id = None
        if video:
            video_filename = f"{product_name.replace(' ', '_')}-{product_slug}.mp4"
            if video.filename.lower().endswith(".mov"):
                converted_video_path = convert_mov_to_mp4(video)
                if converted_video_path:
                    video_id = upload_media(converted_video_path, video_filename)
            else:
                video_path = os.path.join(tempfile.gettempdir(), video.filename)
                video.save(video_path)
                video_id = upload_media(video_path, video_filename)

        # Формируем данные для WooCommerce
        product_data = {
            "name": product_name,
            "slug": product_slug,
            "type": "simple",
            "regular_price": price,
            "sale_price": sale_price if sale_price != "0" else None,
            "categories": [{"id": int(category_id)}],
            "description": f"Yeni {product_name} modeli. Çəkisi: {weight}g, Əyarı: {gold_purity}",
            "images": [{"id": image_id}] if image_id else [],
            "attributes": [{"id": 2, "options": [gold_purity], "visible": True, "variation": False}],
            "meta_data": [{"key": "_weight", "value": weight}, {"key": "_product_video_autoplay", "value": "on"}],
        }

        if video_id:
            product_data["meta_data"].append({"key": "_product_video_gallery", "value": video_id})

        response = requests.post(f"{WC_API_URL}/products", json=product_data, params={
            "consumer_key": WC_CONSUMER_KEY,
            "consumer_secret": WC_CONSUMER_SECRET
        })

        if response.status_code == 201:
            return jsonify({"status": "success", "message": "✅ Товар успешно добавлен!", "url": response.json().get("permalink", "#")})
        else:
            return jsonify({"status": "error", "message": "❌ Ошибка при добавлении товара.", "details": response.text}), 400

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8080)
