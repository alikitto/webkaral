from flask import Flask, render_template, request, jsonify
import requests
import os
import base64
import random
import tempfile
import ffmpeg
import PIL
from PIL import Image

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

def save_original_photo(image, filename_slug):
    """Сохраняет оригинальное фото в папку"""
    try:
        WP_PHOTOS_DIR = "/www/karal.az/wp-content/uploads/original_photos"
        WP_PHOTOS_URL = "https://karal.az/wp-content/uploads/original_photos"

        if not os.path.exists(WP_PHOTOS_DIR):
            os.makedirs(WP_PHOTOS_DIR, exist_ok=True)

        file_path = os.path.join(WP_PHOTOS_DIR, f"{filename_slug}.jpg")
        print(f"📌 [DEBUG] Сохраняем файл по пути: {file_path}")

        image.save(file_path)

        # Проверяем, создался ли файл
        if not os.path.exists(file_path):
            print("❌ Ошибка: файл не был создан!")
            return None

        image_url = f"{WP_PHOTOS_URL}/{filename_slug}.jpg"
        print(f"✅ Оригинальное фото сохранено: {image_url}")
        return image_url
    except Exception as e:
        print(f"❌ Ошибка сохранения оригинального фото: {e}")
        return None


# Папка на сервере, где будем хранить оригиналы фото
WP_PHOTOS_DIR = "/var/www/html/wp-content/uploads/original_photos"  # Путь на сервере
WP_PHOTOS_URL = "https://karal.az/wp-content/uploads/original_photos"  # URL для скачивания

# Настройки видео и фото
RESOLUTION_VIDEO = (720, 720)  # 4:5 формат
RESOLUTION_IMAGE = (1000, 1000)  # 4:5 формат
BITRATE = "2000k"

CATEGORY_DATA = {
    "126": {"name": "Qızıl üzük", "slug": "qizil-uzuk"},
    "132": {"name": "Qızıl sırğa", "slug": "qizil-sirqa"},
    "140": {"name": "Qızıl sep", "slug": "qizil-sep"},
    "138": {"name": "Qızıl qolbaq", "slug": "qizil-qolbaq"},
    "144": {"name": ["Qızıl dəst", "Qızıl komplekt"], "slug": "qizil-komplekt-dest"}
}

GOLD_PURITY_MAP = {
    "105": "585 (14K)",
    "106": "750 (18K)"
}

# Функция загрузки файлов в WordPress
import mimetypes

def upload_media(file, filename=None):
    """ Загружает файл в WordPress и возвращает ID """
    if not file:
        print("❌ Ошибка: Файл отсутствует!")
        return None

    filename = filename or "uploaded_file.jpg"
    print(f"🔄 Загружаем файл: {filename}")

    # Определяем MIME-тип файла
    mime_type, _ = mimetypes.guess_type(filename)
    if not mime_type:
        mime_type = "application/octet-stream"  # Фолбэк на случай неизвестного типа

    files = {"file": (filename, file, mime_type)}
    response = requests.post(WP_MEDIA_URL, headers=HEADERS, files=files)

    if response.status_code == 201:
        media_id = response.json().get("id")
        print(f"✅ Файл загружен! ID: {media_id}")
        return media_id
    else:
        print(f"❌ Ошибка загрузки: {response.text}")
        return None

# Обрезка и центрирование фото 1:1
from PIL import Image, ImageOps

def process_image(image, filename_slug):
    """Обрезка фото в 1000x1000 без сохранения на диск"""
    try:
        temp_output = os.path.join(tempfile.gettempdir(), f"{filename_slug}.jpg")

        img = Image.open(image)

        # Автоматический поворот изображения
        img = ImageOps.exif_transpose(img)

        width, height = img.size
        crop_size = min(width, height)
        left = (width - crop_size) // 2
        top = (height - crop_size) // 2
        right = left + crop_size
        bottom = top + crop_size
        img = img.crop((left, top, right, bottom))

        # Масштабируем в 1000x1000
        img = img.resize((1000, 1000), Image.LANCZOS)
        img.save(temp_output, format="JPEG")

        print(f"✅ Обработанное изображение сохранено: {temp_output}")
        return temp_output
    except Exception as e:
        print(f"❌ Ошибка обработки фото: {e}")
        return None


# Обрезка и центрирование видео 1:1
def convert_and_crop_video(video, output_filename):
    """ Обрезка видео в формат 1:1 и конвертация в MP4 """
    try:
        temp_input = tempfile.NamedTemporaryFile(delete=False, suffix=".mov")
        temp_output = os.path.join(tempfile.gettempdir(), output_filename)

        print(f"🔄 Сохраняем видео {video.filename} во временный файл {temp_input.name}")
        video.save(temp_input.name)

        print("🔄 Начинаем конвертацию видео в 1:1...")

        # Обрезаем в 1:1
        ffmpeg.input(temp_input.name).filter(
            "crop", "min(iw,ih)", "min(iw,ih)", "(iw-min(iw,ih))/2", "(ih-min(iw,ih))/2"
        ).filter(
            "scale", 720, 720
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
    return render_template("index.html", categories=CATEGORY_DATA)

@app.route("/add-product", methods=["POST"])
def add_product():
    try:
        print("📌 [INFO] Получен запрос на добавление товара")

        category_id = request.form.get("category")
        weight = request.form.get("weight")
        gold_purity_id = request.form.get("gold_purity")
        price = request.form.get("price")
        sale_price = request.form.get("sale_price", "0")
        image = request.files.get("image")
        video = request.files.get("video")

        if not category_id or not weight or not price:
            print("❌ [ERROR] Не заполнены обязательные поля")
            return jsonify({"status": "error", "message": "❌ Обязательные поля не заполнены"}), 400

        gold_purity = GOLD_PURITY_MAP.get(gold_purity_id, "585 (14K)")
        category_info = CATEGORY_DATA.get(category_id, {})
        product_name = random.choice(category_info["name"]) if isinstance(category_info["name"], list) else category_info["name"]
        product_slug = f"{category_info['slug']}-{random.randint(1000, 9999)}"

        print(f"📌 [INFO] Создаём товар: {product_name}, Slug: {product_slug}, Вес: {weight}, Цена: {price}")

        # 1️⃣ Загрузка оригинального фото в папку
        original_photo_url = None
        if image:
            original_photo_url = save_original_photo(image, product_slug)

        # 2️⃣ Обрезаем и загружаем обработанное фото (1000x1000) в медиабиблиотеку
        image_id = None
        if image:
            processed_image = process_image(image, product_slug)  # Конвертация из памяти, не из файла
            if processed_image:
                print("📌 [INFO] Загружаем обработанное изображение...")
                with open(processed_image, "rb") as img_file:
                    image_id = upload_media(img_file, filename=f"{product_slug}.jpg")

        # 3️⃣ Загрузка видео
        video_id = None
        if video:
            output_filename = f"{product_slug}.mp4"
            converted_video_path = convert_and_crop_video(video, output_filename)
            if converted_video_path:
                with open(converted_video_path, "rb") as converted_video:
                    print("📌 [INFO] Загружаем видео...")
                    video_id = upload_media(converted_video, filename=output_filename)

        print(f"✅ [INFO] Загруженное изображение ID: {image_id}")
        print(f"✅ [INFO] Загруженное видео ID: {video_id}")

        # 4️⃣ Подготавливаем данные товара
        product_data = {
            "name": product_name,
            "slug": product_slug,
            "regular_price": price,
            "sale_price": sale_price if sale_price != "0" else None,
            "categories": [{"id": int(category_id)}],
            "images": [{"id": image_id}] if image_id else [],
            "attributes": [
                {"id": 2, "name": "Əyar", "options": [gold_purity], "visible": True, "variation": False}
            ],
            "meta_data": [
                {"key": "_weight", "value": weight},
                {"key": "_product_video_autoplay", "value": "on"},
                {"key": "_gold_purity", "value": gold_purity}
            ]
        }

        # 5️⃣ Добавляем ссылку на оригинал в мета-данные товара
        if original_photo_url:
            product_data["meta_data"].append({"key": "_original_photo_url", "value": original_photo_url})

        # 6️⃣ Добавляем видео в мета-данные товара
        if video_id:
            product_data["meta_data"].append({"key": "_product_video_gallery", "value": video_id})

        print("📌 [INFO] Отправляем запрос на создание товара...")
        response = requests.post(
            WC_API_URL + "/products",
            json=product_data,
            params={"consumer_key": WC_CONSUMER_KEY, "consumer_secret": WC_CONSUMER_SECRET}
        )

        print(f"📌 [INFO] Ответ от сервера WooCommerce: {response.status_code}")
        print(f"📌 [INFO] Детали ответа: {response.text}")

        if response.status_code == 201:
            return jsonify({"status": "success", "message": "✅ Товар добавлен!"})
        else:
            print("❌ [ERROR] Ошибка при добавлении товара")
            return jsonify({"status": "error", "message": "❌ Ошибка при добавлении товара"}), 400

    except Exception as e:
        print(f"❌ [ERROR] Исключение в add_product: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500






