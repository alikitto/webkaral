from flask import Flask, render_template, request, jsonify
import requests
import os
import base64
import random
import tempfile
import moviepy as mp

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

# **Настройки конвертации**
TARGET_WIDTH = 720  # Ширина видео (для уменьшения)
BITRATE = "1000k"  # Битрейт видео (качество)

# **Выбор формата (9:16, 1:1, 4:5)**
TARGET_ASPECT_RATIO = "9:16"  # Опции: "9:16", "1:1", "4:5"
CROP_MODE = True  # True = обрезка краёв, False = добавление чёрных полос

def upload_media(file, filename=None):
    """ Загружает файл в медиатеку WordPress и возвращает ID """
    if not file:
        return None

    filename = filename or file.filename
    files = {"file": (filename, file, "video/mp4" if filename.endswith(".mp4") else file.content_type)}
    response = requests.post(WP_MEDIA_URL, headers=HEADERS, files=files)

    if response.status_code == 201:
        return response.json().get("id")
    return None

def convert_mov_to_mp4(video, output_filename):
    """ Конвертация MOV в MP4 с изменением формата и качества """
    try:
        temp_input = tempfile.NamedTemporaryFile(delete=False, suffix=".mov")
        temp_output = os.path.join(tempfile.gettempdir(), output_filename)

        video.save(temp_input.name)
        clip = mp.VideoFileClip(temp_input.name)

        # **Обрабатываем формат видео**
        orig_w, orig_h = clip.size
        aspect_ratios = {
            "9:16": (9, 16),
            "1:1": (1, 1),
            "4:5": (4, 5)
        }
        target_w, target_h = aspect_ratios[TARGET_ASPECT_RATIO]

        new_h = int(TARGET_WIDTH * target_h / target_w)

        if CROP_MODE:
            # Обрезаем края, чтобы видео идеально влезло в новый формат
            clip = clip.crop(
                x_center=orig_w / 2,
                y_center=orig_h / 2,
                width=min(orig_w, int(orig_h * target_w / target_h)),
                height=min(orig_h, int(orig_w * target_h / target_w))
            )
        else:
            # Добавляем чёрные полосы
            clip = clip.resize(width=TARGET_WIDTH)
            clip = clip.margin(top=(new_h - clip.h) // 2, bottom=(new_h - clip.h) // 2, color=(0, 0, 0))

        clip.write_videofile(temp_output, codec="libx264", audio_codec="aac", bitrate=BITRATE)

        return temp_output
    except Exception as e:
        print(f"Ошибка конвертации видео: {e}")
        return None

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

        image_id = upload_media(image) if image else None
        if not image_id:
            return jsonify({"status": "error", "message": "❌ Ошибка загрузки изображения"}), 400

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
