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

# Настройки видео и фото
RESOLUTION_VIDEO = (720, 900)  # 4:5 формат
RESOLUTION_IMAGE = (720, 900)  # 4:5 формат
BITRATE = "2500k"

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

# Обрезка и центрирование фото 4:5
def process_image(image):
    try:
        temp_input = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
        temp_output = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg").name

        image.save(temp_input.name)

        img = Image.open(temp_input.name)
        width, height = img.size

        target_width, target_height = RESOLUTION_IMAGE

        # Обрезка по центру
        if width / height > target_width / target_height:
            new_width = int(height * target_width / target_height)
            left = (width - new_width) / 2
            right = left + new_width
            img = img.crop((left, 0, right, height))
        else:
            new_height = int(width * target_height / target_width)
            top = (height - new_height) / 2
            bottom = top + new_height
            img = img.crop((0, top, width, bottom))

        img = img.resize(RESOLUTION_IMAGE, Image.ANTIALIAS)
        img.save(temp_output, format="JPEG")
        
        return temp_output
    except Exception as e:
        print(f"❌ Ошибка обработки фото: {e}")
        return None

# Обрезка и центрирование видео 4:5
def convert_and_crop_video(video, output_filename):
    try:
        temp_input = tempfile.NamedTemporaryFile(delete=False, suffix=".mov")
        temp_output = os.path.join(tempfile.gettempdir(), output_filename)

        print(f"🔄 Сохраняем видео {video.filename} во временный файл {temp_input.name}")
        video.save(temp_input.name)

        print("🔄 Начинаем конвертацию видео в 4:5...")

        ffmpeg.input(temp_input.name).filter(
            "crop", f"min(iw,ih)", f"min(iw,ih)", f"(iw-min(iw,ih))/2", f"(ih-min(iw,ih))/2"
        ).filter(
            "scale", RESOLUTION_VIDEO[0], RESOLUTION_VIDEO[1]
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

        print(f"Создаём товар: {product_name}, Вес: {weight}, Цена: {price}")

        image_id = upload_media(open(process_image(image), "rb")) if image else None
        video_id = None
        if video:
            output_filename = f"{product_name.replace(' ', '_')}.mp4"
            converted_video_path = convert_and_crop_video(video, output_filename)
            if converted_video_path:
                with open(converted_video_path, "rb") as converted_video:
                    video_id = upload_media(converted_video, filename=output_filename)

        product_data = {
            "name": product_name,
            "regular_price": price,
            "sale_price": sale_price if sale_price != "0" else None,
            "categories": [{"id": int(category_id)}],
            "images": [{"id": image_id}],
            "meta_data": [
                {"key": "_weight", "value": weight},
                {"key": "_product_video_autoplay", "value": "on"},
                {"key": "_gold_purity", "value": gold_purity}
            ]
        }

        if video_id:
            product_data["meta_data"].append({"key": "_product_video_gallery", "value": video_id})

        response = requests.post(WC_API_URL + "/products", json=product_data,
                                 params={"consumer_key": WC_CONSUMER_KEY, "consumer_secret": WC_CONSUMER_SECRET})

        return jsonify({"status": "success", "message": "✅ Товар добавлен!"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
