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

# WordPress API данные (для загрузки изображений и видео)
WP_USERNAME = os.getenv("WP_USERNAME", "alikitto")
WP_PASSWORD = os.getenv("WP_PASSWORD", "HsbD0gjVhsj0Fb1KXrMx4nLQ")
WP_MEDIA_URL = "https://karal.az/wp-json/wp/v2/media"

# Авторизация для WordPress API
auth = base64.b64encode(f"{WP_USERNAME}:{WP_PASSWORD}".encode()).decode()
HEADERS = {"Authorization": f"Basic {auth}"}

# Категории товаров (исправлено, теперь определено до рендера `index.html`)
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
RESOLUTION = 720  # Размер видео (720x720, 1:1)
BITRATE = "2500k"  # Оптимальный битрейт

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

def convert_and_crop_video(video, output_filename):
    """ Конвертация MOV → MP4 с обрезкой в формат 1:1 (720x720) """
    try:
        temp_input = tempfile.NamedTemporaryFile(delete=False, suffix=".mov")
        temp_output = os.path.join(tempfile.gettempdir(), output_filename)

        print(f"Сохраняем видео {video.filename} во временный файл {temp_input.name}")
        video.save(temp_input.name)

        print(f"Начинаем конвертацию и обрезку видео...")

        # Читаем параметры видео
        probe = ffmpeg.probe(temp_input.name)
        video_stream = next((stream for stream in probe["streams"] if stream["codec_type"] == "video"), None)

        if not video_stream:
            raise ValueError("Не найден видеопоток")

        width = int(video_stream["width"])
        height = int(video_stream["height"])

        # Обрезка под 1:1 (центрируем)
        crop_size = min(width, height)
        x_offset = (width - crop_size) // 2
        y_offset = (height - crop_size) // 2

        # Запускаем FFmpeg для обрезки и сжатия
        ffmpeg.input(temp_input.name).filter(
            "crop", crop_size, crop_size, x_offset, y_offset
        ).filter(
            "scale", RESOLUTION, RESOLUTION
        ).output(
            temp_output, vcodec="libx264", acodec="aac", bitrate=BITRATE
        ).run(overwrite_output=True)

        print(f"Конвертация завершена! Файл сохранён: {temp_output}")

        return temp_output
    except Exception as e:
        print(f"Ошибка конвертации видео: {e}")
        return None

@app.route("/")
def home():
    return render_template("index.html", categories=CATEGORY_DATA)

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
                converted_video_path = convert_and_crop_video(video, output_filename)
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
            "attributes": [
                {"id": 2, "options": [gold_purity], "visible": True, "variation": False}
            ],
            "meta_data": [
                {"key": "_weight", "value": weight},
                {"key": "_product_video_autoplay", "value": "on"}
            ]
        }

        if video_id:
            product_data["meta_data"].append({"key": "_product_video_gallery", "value": video_id})

        url = f"{WC_API_URL}/products"
        params = {"consumer_key": WC_CONSUMER_KEY, "consumer_secret": WC_CONSUMER_SECRET}
        response = requests.post(url, json=product_data, params=params)

        if response.status_code == 201:
            product_url = response.json().get("permalink", "#")
            return jsonify({"status": "success", "message": "✅ Товар успешно добавлен!", "url": product_url})
        else:
            return jsonify({"status": "error", "message": "❌ Ошибка при добавлении товара.", "details": response.text}), 400

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8080)
