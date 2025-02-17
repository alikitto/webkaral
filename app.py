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

# Авторизация для WordPress API
auth = base64.b64encode(f"{WP_USERNAME}:{WP_PASSWORD}".encode()).decode()
HEADERS = {"Authorization": f"Basic {auth}"}

# Настройки видео
RESOLUTION = 720  # 1:1 (720x720)
BITRATE = "2500k"  # Оптимальный битрейт


def upload_media(file, filename=None):
    """ Загружает файл в WordPress и возвращает ID """
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
    """ Конвертация и обрезка видео в 1:1 (по центру) """
    try:
        temp_input = tempfile.NamedTemporaryFile(delete=False, suffix=".mov")
        temp_output = os.path.join(tempfile.gettempdir(), output_filename)

        print(f"Сохраняем видео {video.filename} во временный файл {temp_input.name}")
        video.save(temp_input.name)

        print("Начинаем конвертацию и обрезку видео...")

        # Получаем параметры видео
        probe = ffmpeg.probe(temp_input.name)
        video_stream = next((stream for stream in probe["streams"] if stream["codec_type"] == "video"), None)

        if not video_stream:
            raise ValueError("Не найден видеопоток")

        width = int(video_stream["width"])
        height = int(video_stream["height"])

        # Обрезка по центру
        crop_size = min(width, height)
        x_offset = (width - crop_size) // 2
        y_offset = (height - crop_size) // 2

        # Применяем поворот, если видео снято в вертикальном режиме
        rotation = None
        if "displaymatrix" in video_stream.get("side_data_list", [{}])[0]:
            rotation = int(video_stream["side_data_list"][0]["displaymatrix"])
            if rotation == -90:
                ffmpeg.input(temp_input.name).filter("transpose", 1).output(temp_input.name, overwrite_output=True).run()

        # Применяем обрезку и масштабирование
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
    return render_template("index.html")


@app.route("/add-product", methods=["POST"])
def add_product():
    try:
        category_id = request.form.get("category")
        weight = request.form.get("weight")
        gold_purity = request.form.get("gold_purity")
        price = request.form.get("price")
        sale_price = request.form.get("sale_price", "0")
        image = request.files.get("image")
        video = request.files.get("video")

        if not category_id or not weight or not price:
            return jsonify({"status": "error", "message": "❌ Обязательные поля не заполнены"}), 400

        product_slug = f"product-{random.randint(1000, 9999)}"
        print(f"Создаём товар с slug: {product_slug}")

        # Загружаем изображение
        image_id = upload_media(image) if image else None

        if not image_id:
            return jsonify({"status": "error", "message": "❌ Ошибка загрузки изображения"}), 400

        # Обработка видео
        video_id = None
        if video:
            output_filename = f"{product_slug}.mp4"

            if video.filename.lower().endswith(".mov"):
                converted_video_path = convert_and_crop_video(video, output_filename)
                if converted_video_path:
                    with open(converted_video_path, "rb") as converted_video:
                        video_id = upload_media(converted_video, filename=output_filename)
            else:
                video_id = upload_media(video, filename=output_filename)

        # Проверка, загружено ли видео
        if video and not video_id:
            return jsonify({"status": "error", "message": "❌ Ошибка загрузки видео"}), 400

        # Данные для WooCommerce
        product_data = {
            "name": "Новый товар",
            "slug": product_slug,
            "type": "simple",
            "regular_price": price,
            "sale_price": sale_price if sale_price != "0" else None,
            "categories": [{"id": int(category_id)}],
            "description": f"Вес: {weight} г, Проба: {gold_purity}",
            "images": [{"id": image_id}],
            "meta_data": [{"key": "_weight", "value": weight}]
        }

        if video_id:
            product_data["meta_data"].append({"key": "_product_video_gallery", "value": video_id})

        url = f"{WC_API_URL}/products"
        params = {"consumer_key": WC_CONSUMER_KEY, "consumer_secret": WC_CONSUMER_SECRET}
        response = requests.post(url, json=product_data, params=params)

        if response.status_code == 201:
            return jsonify({"status": "success", "message": "✅ Товар успешно добавлен!"})
        else:
            return jsonify({"status": "error", "message": "❌ Ошибка при добавлении товара.", "details": response.text}), 400

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8080)
