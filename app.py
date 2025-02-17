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

# Пробы золота (Əyar)
GOLD_PURITY_MAP = {
    "105": "585 (14K)",
    "106": "750 (18K)"
}

# Настройки конвертации
RESIZE_WIDTH = 720  # Максимальная ширина видео (можно поменять)
BITRATE = "1000k"   # Качество битрейта

# Функция загрузки файла в WordPress
def upload_media(file, filename=None):
    """ Загружает файл (изображение или видео) в медиатеку WordPress и возвращает ID """
    if not file:
        print("Ошибка: Файл отсутствует!")
        return None

    filename = filename or file.filename
    print(f"Загружаем файл: {filename}")

    files = {"file": (filename, file, "video/mp4" if filename.endswith(".mp4") else file.content_type)}
    response = requests.post(WP_MEDIA_URL, headers=HEADERS, files=files)

    if response.status_code == 201:
        media_id = response.json().get("id")
        print(f"Файл загружен успешно! ID: {media_id}")
        return media_id
    else:
        print(f"Ошибка загрузки файла: {response.text}")
        return None

# Функция конвертации MOV → MP4 с изменением размера и исправлением поворота
def convert_mov_to_mp4(video, output_filename):
    """ Конвертация MOV в MP4 с изменением размера и битрейта """
    try:
        temp_input_path = os.path.join(tempfile.gettempdir(), video.filename)
        temp_output_path = os.path.join(tempfile.gettempdir(), output_filename)

        print(f"Сохраняем видео {video.filename} во временный файл {temp_input_path}")
        video.save(temp_input_path)

        print(f"Начинаем конвертацию MOV → MP4...")

        # Определяем соотношение сторон
        command_probe = [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height", "-of", "csv=p=0", temp_input_path
        ]
        resolution = subprocess.check_output(command_probe).decode().strip()
        width, height = map(int, resolution.split(","))

        # Выбираем правильное соотношение сторон
        if width > height:
            video_size = "1280:720"  # Горизонтальное видео (16:9)
        else:
            video_size = "720:1280"  # Вертикальное видео (9:16)

        # Конвертация видео с исправлением поворота
        command = [
            "ffmpeg", "-i", temp_input_path,
            "-vf", f"scale={video_size},transpose=1",  # Авто-поворот и изменение размера
            "-c:v", "libx264", "-crf", "23", "-preset", "fast",
            "-c:a", "aac", "-b:a", "128k",
            temp_output_path
        ]

        subprocess.run(command, check=True)
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
        # Получаем данные из формы
        category_id = request.form.get("category")
        weight = request.form.get("weight")
        gold_purity_id = request.form.get("gold_purity")
        price = request.form.get("price")
        sale_price = request.form.get("sale_price", "0")
        image = request.files.get("image")
        video = request.files.get("video")

        # Проверяем валидность данных
        if not category_id or not weight or not price:
            return jsonify({"status": "error", "message": "❌ Обязательные поля не заполнены"}), 400

        # Преобразуем ID пробы в текстовое значение
        gold_purity = GOLD_PURITY_MAP.get(gold_purity_id, "585 (14K)")

        # Генерируем название и slug
        category_info = CATEGORY_DATA.get(category_id, {})
        product_name = random.choice(category_info["name"]) if isinstance(category_info["name"], list) else category_info["name"]
        product_slug = f"{category_info['slug']}-{random.randint(1000, 9999)}"

        print(f"Создаём товар: {product_name}, Slug: {product_slug}, Вес: {weight}, Цена: {price}")

        # Загружаем изображение
        image_id = upload_media(image) if image else None
        if not image_id:
            return jsonify({"status": "error", "message": "❌ Ошибка загрузки изображения"}), 400

        # Проверка типа видео и конвертация, если это MOV
        video_id = None
        if video:
            output_filename = f"{product_name.replace(' ', '_')}-{product_slug}.mp4"

            if video.filename.lower().endswith(".mov"):
                converted_video_path = convert_mov_to_mp4(video, output_filename)
                if converted_video_path:
                    with open(converted_video_path, "rb") as converted_video:
                        video_id = upload_media(converted_video, filename=output_filename)
            else:
                video_id = upload_media(video, filename=output_filename)

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
            "meta_data": [
                {"key": "_weight", "value": weight},
                {"key": "_product_video_autoplay", "value": "on"}
            ]
        }

        if video_id:
            product_data["meta_data"].append({"key": "_product_video_gallery", "value": video_id})

        return jsonify({"status": "success", "message": "✅ Товар успешно добавлен!"})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8080)
