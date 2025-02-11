from flask import Flask, render_template, request, jsonify
import requests
import os
import random

app = Flask(__name__)

# WooCommerce API настройки
WC_API_URL = os.getenv("WC_API_URL", "https://karal.az/wp-json/wc/v3")
WC_MEDIA_URL = os.getenv("WC_MEDIA_URL", "https://karal.az/wp-json/wp/v2/media")
WC_CONSUMER_KEY = os.getenv("WC_CONSUMER_KEY")
WC_CONSUMER_SECRET = os.getenv("WC_CONSUMER_SECRET")

# Пробы золота с ID
GOLD_PURITY_MAP = {
    "105": "585 (14K)",
    "106": "750 (18K)"
}

# Категории товаров и генерация названия
CATEGORY_TITLES = {
    "126": ("Qızıl üzük", "qizil-uzuk"),
    "132": ("Qızıl sırğa", "qizil-sirqa"),
    "140": ("Qızıl sep", "qizil-sep"),
    "138": ("Qızıl qolbaq", "qizil-qolbaq"),
    "144": ("Qızıl dəst komplekt", "qizil-komplet-dest")
}

# Описания товаров
DESCRIPTION_TEMPLATES = {
    "126": [
        "🔹 Yeni qızıl üzük modeli. Zərif dizaynı ilə gündəlik və xüsusi günlər üçün ideal seçim! ✨",
        "💍 Zövqlü dizayn və yüksək keyfiyyət! Bu unikal qızıl üzük zərifliyi və incəliyi ilə seçilir. ✨",
        "✨ Qızılın əbədi gözəlliyi! Zəriflik, incəlik və yüksək keyfiyyət – bu qızıl üzük hər anınızı daha xüsusi edəcək."
    ],
    "132": ["Yeni qızıl sırğa modeli. Çəkisi: {weight}g, Əyarı: {gold_purity}"],
    "140": ["Yeni qızıl sep modeli."],
    "138": ["Yeni qızıl qolbaq modeli."],
    "144": ["Yeni qızıl komplekt."]
}

@app.route("/")
def home():
    return render_template("index.html", categories=CATEGORY_TITLES, gold_purity_map=GOLD_PURITY_MAP)

@app.route("/add-product", methods=["POST"])
def add_product():
    try:
        category_id = request.form.get("category")
        weight = request.form.get("weight")
        gold_purity_id = request.form.get("gold_purity")
        price = request.form.get("price")
        sale_price = request.form.get("sale_price", "0")

        product_name, slug_base = CATEGORY_TITLES.get(category_id, ("Qızıl məhsul", "qizil-mehsul"))
        description_template = random.choice(DESCRIPTION_TEMPLATES.get(category_id, ["Yeni qızıl məhsul."]))
        description = description_template.format(weight=weight, gold_purity=GOLD_PURITY_MAP.get(gold_purity_id, "N/A"))

        # Загрузка изображения в WooCommerce
        image_url = None
        if 'image' in request.files:
            image_file = request.files['image']
            if image_file.filename:
                image_url = upload_image_to_wc(image_file)

        if not image_url:
            return jsonify({"status": "error", "message": "Ошибка загрузки изображения"}), 400

        product_data = {
            "name": product_name,
            "slug": f"{slug_base}-{random.randint(1000, 9999)}",
            "type": "simple",
            "regular_price": price,
            "sale_price": sale_price if sale_price != "0" else None,
            "categories": [{"id": int(category_id)}],
            "description": description,
            "images": [{"src": image_url}],
            "attributes": [
                {
                    "id": 2,  # ID атрибута Əyar
                    "options": [GOLD_PURITY_MAP.get(gold_purity_id, "N/A")],
                    "visible": True,
                    "variation": False
                }
            ],
            "meta_data": [
                {
                    "key": "_weight",
                    "value": f"{weight} g"
                }
            ]
        }

        url = f"{WC_API_URL}/products"
        params = {
            "consumer_key": WC_CONSUMER_KEY,
            "consumer_secret": WC_CONSUMER_SECRET
        }
        response = requests.post(url, json=product_data, params=params)

        if response.status_code == 201:
            product_id = response.json().get("id")
            product_url = f"https://karal.az/product/{product_id}"
            return jsonify({"status": "success", "message": "Товар успешно добавлен!", "url": product_url})
        else:
            return jsonify({
                "status": "error",
                "message": "Ошибка при добавлении товара.",
                "details": response.text
            }), 400

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# **Функция загрузки изображений в WooCommerce через API**
def upload_image_to_wc(image_file):
    try:
        url = WC_MEDIA_URL
        params = {
            "consumer_key": WC_CONSUMER_KEY,
            "consumer_secret": WC_CONSUMER_SECRET
        }
        files = {
            "file": (image_file.filename, image_file.stream, image_file.content_type)
        }
        headers = {
            "Content-Disposition": f"attachment; filename={image_file.filename}",
            "Content-Type": image_file.content_type
        }

        response = requests.post(url, files=files, params=params, headers=headers)

        if response.status_code == 201:
            return response.json().get("source_url")
        else:
            print(f"Ошибка загрузки изображения: {response.text}")
            return None
    except Exception as e:
        print(f"Ошибка при отправке изображения: {e}")
        return None

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8080)
