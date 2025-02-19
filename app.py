from flask import Flask, render_template, request, jsonify
import requests
import os
import io
import base64
import random
import tempfile
import ffmpeg
import boto3
from PIL import Image, ImageOps
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)

# WooCommerce API
WC_API_URL = os.getenv("WC_API_URL", "https://karal.az/wp-json/wc/v3")
WC_CONSUMER_KEY = os.getenv("WC_CONSUMER_KEY")
WC_CONSUMER_SECRET = os.getenv("WC_CONSUMER_SECRET")

# WordPress API
WP_MEDIA_URL = "https://karal.az/wp-json/wp/v2/media"
WP_USERNAME = os.getenv("WP_USERNAME")
WP_PASSWORD = os.getenv("WP_PASSWORD")
auth = base64.b64encode(f"{WP_USERNAME}:{WP_PASSWORD}".encode()).decode()
HEADERS = {"Authorization": f"Basic {auth}"}

# Cloudflare R2 Credentials
R2_ACCOUNT_ID = os.getenv('R2_ACCOUNT_ID')
R2_ACCESS_KEY_ID = os.getenv('R2_ACCESS_KEY_ID')
R2_SECRET_ACCESS_KEY = os.getenv('R2_SECRET_ACCESS_KEY')
R2_BUCKET_NAME = os.getenv('R2_BUCKET_NAME')

# Настройки видео и фото
RESOLUTION_VIDEO = (720, 720)  # 1:1 формат
BITRATE = "1700k"

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

# Инициализация клиента для Cloudflare R2
session = boto3.session.Session()
r2_client = session.client(
    's3',
    endpoint_url=f'https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com',
    aws_access_key_id=R2_ACCESS_KEY_ID,
    aws_secret_access_key=R2_SECRET_ACCESS_KEY
)

def upload_to_r2(file_path, bucket_folder, filename):
    """Загружает файл в указанный бакет и папку на R2."""
    try:
        with open(file_path, 'rb') as file_data:
            r2_client.upload_fileobj(file_data, R2_BUCKET_NAME, f"{bucket_folder}/{filename}")
        print(f"✅ Файл {filename} успешно загружен в R2 в папку {bucket_folder}.")
        return f"https://video.karal.az/{bucket_folder}/{filename}"
    except Exception as e:
        print(f"❌ Ошибка при загрузке файла в R2: {e}")
        return None

def process_image(image, filename_slug):
    """Обрезка фото в 1000x1000 и сохранение во временный файл."""
    try:
        temp_output = os.path.join(tempfile.gettempdir(), f"{filename_slug}.jpg")
        img = Image.open(image)
        img = ImageOps.exif_transpose(img)
        width, height = img.size
        crop_size = min(width, height)
        left = (width - crop_size) // 2
        top = (height - crop_size) // 2
        img = img.crop((left, top, left + crop_size, top + crop_size))
        img = img.resize((1000, 1000), Image.LANCZOS)
        img.save(temp_output, format="JPEG")
        print(f"✅ Обработанное изображение сохранено: {temp_output}")
        return temp_output
    except Exception as e:
        print(f"❌ Ошибка обработки фото: {e}")
        return None

def convert_and_crop_video(video, filename_slug):
    """Конвертирует и обрезает видео в формат 1:1 с разрешением 720x720."""
    try:
        temp_input = tempfile.NamedTemporaryFile(delete=False, suffix=".mov")
        temp_output = os.path.join(tempfile.gettempdir(), f"{filename_slug}.mp4")
        video.save(temp_input.name)
        ffmpeg.input(temp_input.name).filter(
            'crop', 'min(iw,ih)', 'min(iw,ih)', '(iw-min(iw,ih))/2', '(ih-min(iw,ih))/2'
        ).filter(
            'scale', RESOLUTION_VIDEO[0], RESOLUTION_VIDEO[1]
        ).output(
            temp_output, vcodec='libx264', acodec='aac', bitrate=BITRATE
        ).run(overwrite_output=True)
        print(f"✅ Видео конвертировано и обрезано: {temp_output}")
        return temp_output
    except Exception as e:
        print(f"❌ Ошибка конвертации видео: {e}")
        return None

def upload_media_to_wp(file_path, filename):
    """Загружает файл в медиабиблиотеку WordPress и возвращает ID медиа."""
    try:
        with open(file_path, 'rb') as file_data:
            mime_type = 'video/mp4' if filename.endswith('.mp4') else 'image/jpeg'
            files = {'file': (filename, file_data, mime_type)}
            response = requests.post(WP_MEDIA_URL, headers=HEADERS, files=files)
            if response.status_code == 201:
                media_id = response.json().get('id')
                print(f"✅ Файл загружен в WordPress! ID: {media_id}")
                return media_id
            else:
                print(f"❌ Ошибка загрузки в WordPress: {response.text}")
                return None
    except Exception as e:
        print(f"❌ Ошибка при загрузке файла в WordPress: {e}")
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
            return jsonify({"status": "error", "message": "❌ Обязательные поля
::contentReference[oaicite:0]{index=0}
 
