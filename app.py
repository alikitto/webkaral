from flask import Flask, render_template, request, jsonify
import requests
import os
import base64
import random
import tempfile
import ffmpeg
from PIL import Image, ImageOps
import mimetypes

app = Flask(__name__)

# WooCommerce API
WC_API_URL = os.getenv("WC_API_URL", "https://karal.az/wp-json/wc/v3")
WC_CONSUMER_KEY = os.getenv("WC_CONSUMER_KEY")
WC_CONSUMER_SECRET = os.getenv("WC_CONSUMER_SECRET")

# WordPress API
WP_USERNAME = os.getenv("WP_USERNAME", "alikitto")
WP_PASSWORD = os.getenv("WP_PASSWORD")
WP_MEDIA_URL = "https://karal.az/wp-json/wp/v2/media"

# Авторизация
auth = base64.b64encode(f"{WP_USERNAME}:{WP_PASSWORD}".encode()).decode()
HEADERS = {"Authorization": f"Basic {auth}"}

# Настройки
RESOLUTION = (1000, 1000)  # Обновлено на 1000x1000
BITRATE = "2500k"

CATEGORY_DATA = {
    "126": {"name": "Qızıl üzük", "slug": "qizil-uzuk", "parent": None},
    "132": {"name": "Qızıl sırğa", "slug": "qizil-sirqa", "parent": None},
    "140": {"name": "Qızıl sep", "slug": "qizil-sep", "parent": None},
    "138": {"name": "Qızıl qolbaq", "slug": "qizil-qolbaq", "parent": None},
    "144": {"name": "Qızıl dəst", "slug": "qizil-komplekt-dest", "parent": None},
}

GOLD_PURITY_MAP = {
    "105": "585 (14K)",
    "106": "750 (18K)"
}

GOLD_COLOR_MAP = {
    "269": "Ağ qızıl",
    "267": "Sarı qızıl",
    "280": "Ağ və sarı",
    "271": "Rose Gold"
}

GEMSTONE_MAP = {
    "29263": "Daşsız",
    "282": "Brilliant",
    "29267": "Svarovski",
    "29271": "Sadə qaş",
    "29273": "Zümrüd",
    "29269": "Mirvari",
    "29265": "Sapfir",
    "336": "Ametist",
    "283": "Korund",
    "109": "Topaz",
    "3313": "Almaz"
}

# Обрезка фото
def process_image(image, filename_slug):
    try:
        temp_output = os.path.join(tempfile.gettempdir(), f"{filename_slug}.jpg")
        img = Image.open(image)
        img = ImageOps.exif_transpose(img)
        img = img.resize(RESOLUTION, Image.LANCZOS)
        img.save(temp_output, format="JPEG")
        return temp_output
    except Exception as e:
        print(f"❌ Ошибка обработки фото: {e}")
        return None

# Конвертация видео
def convert_and_crop_video(video, output_filename):
    try:
        temp_output = os.path.join(tempfile.gettempdir(), output_filename)
        ffmpeg.input(video).filter(
            "scale", RESOLUTION[0], RESOLUTION[1]
        ).output(
            temp_output, vcodec="libx264", acodec="aac", bitrate=BITRATE
        ).run(overwrite_output=True)
        return temp_output
    except Exception as e:
        print(f"❌ Ошибка конвертации видео: {e}")
        return None

@app.route("/add-product", methods=["POST"])
def add_product():
    try:
        category_id = request.form.get("category")
        parent_category = CATEGORY_DATA.get(category_id, {}).get("parent")
        categories = [{"id": int(category_id)}]
        if parent_category:
            categories.append({"id": parent_category})
        
        weight = request.form.get("weight")
        gold_purity_id = request.form.get("gold_purity")
        gold_color_id = request.form.get("gold_color")
        gemstone_id = request.form.get("gemstone")
        price = request.form.get("price")
        sale_price = request.form.get("sale_price", "0")
        karat = request.form.get("karatqr")
        image = request.files.get("image")
        video = request.files.get("video")

        gold_purity = GOLD_PURITY_MAP.get(gold_purity_id, "585 (14K)")
        gold_color = GOLD_COLOR_MAP.get(gold_color_id, "Sarı qızıl")
        gemstone = GEMSTONE_MAP.get(gemstone_id, "Daşsız")

        image_id = None
        if image:
            processed_image = process_image(image, "product")
            if processed_image:
                with open(processed_image, "rb") as img_file:
                    image_id = upload_media(img_file, filename="product.jpg")

        video_id = None
        if video:
            output_filename = "product.mp4"
            converted_video_path = convert_and_crop_video(video, output_filename)
            if converted_video_path:
                with open(converted_video_path, "rb") as converted_video:
                    video_id = upload_media(converted_video, filename=output_filename)

        product_data = {
            "name": "Yeni məhsul",
            "slug": "yeni-mehsul",
            "regular_price": price,
            "sale_price": sale_price if sale_price != "0" else None,
            "categories": categories,
            "images": [{"id": image_id}] if image_id else [],
            "attributes": [
                {"id": 2, "name": "Əyar", "options": [gold_purity], "visible": True},
                {"id": 4, "name": "Qızılın rəngi", "options": [gold_color], "visible": True},
                {"id": 3, "name": "Qaşlar", "options": [gemstone], "visible": True}
            ],
            "meta_data": [
                {"key": "karatqr", "value": karat}
            ]
        }

        response = requests.post(
            WC_API_URL + "/products",
            json=product_data,
            params={"consumer_key": WC_CONSUMER_KEY, "consumer_secret": WC_CONSUMER_SECRET}
        )
        
        return jsonify({"status": "success", "message": "✅ Товар добавлен!"}) if response.status_code == 201 else jsonify({"status": "error"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})
