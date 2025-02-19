from flask import Flask, render_template, request, jsonify
import requests
import os
import base64
import random
import tempfile
import ffmpeg
from PIL import Image, ImageOps
import mimetypes

app = Flask(__name__, template_folder="./")

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

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/add-product", methods=["POST"])
def add_product():
    try:
        category_id = request.form.get("category")
        weight = request.form.get("weight")
        gold_purity_id = request.form.get("gold_purity")
        gold_color_id = request.form.get("gold_color")
        gemstone_id = request.form.get("gemstone")
        price = request.form.get("price")
        sale_price = request.form.get("sale_price", "0")
        karat = request.form.get("karatqr")
        image = request.files.get("image")
        video = request.files.get("video")

        product_data = {
            "name": "Yeni məhsul",
            "slug": "yeni-mehsul",
            "regular_price": price,
            "sale_price": sale_price if sale_price != "0" else None,
            "categories": [{"id": int(category_id)}],
            "images": [],
            "attributes": [
                {"id": 2, "name": "Əyar", "options": [gold_purity_id], "visible": True},
                {"id": 4, "name": "Qızılın rəngi", "options": [gold_color_id], "visible": True},
                {"id": 3, "name": "Qaşlar", "options": [gemstone_id], "visible": True}
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

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
