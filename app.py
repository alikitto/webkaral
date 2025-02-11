from flask import Flask, render_template, request, jsonify
import requests
import os
import random

app = Flask(__name__)

# WooCommerce API настройки
WC_API_URL = os.getenv("WC_API_URL", "https://karal.az/wp-json/wc/v3")
WC_CONSUMER_KEY = os.getenv("WC_CONSUMER_KEY")
WC_CONSUMER_SECRET = os.getenv("WC_CONSUMER_SECRET")

CATEGORY_DATA = {
    "126": ("Qızıl üzük", "qizil-uzuk"),
    "132": ("Qızıl sırğa", "qizil-sirqa"),
    "140": ("Qızıl sep", "qizil-sep"),
    "138": ("Qızıl qolbaq", "qizil-qolbaq"),
    "144": ("Qızıl dəst komplekt", "qizil-komplet-dest"),
}

DESCRIPTIONS = {
    "126": [
        "🔹 Yeni qızıl üzük modeli. Zərif dizaynı ilə gündəlik və xüsusi günlər üçün ideal seçim! ✨",
        "💍 Zövqlü dizayn və yüksək keyfiyyət! Bu unikal qızıl üzük zərifliyi və incəliyi ilə seçilir. ✨",
        "✨ Qızılın əbədi gözəlliyi! Zəriflik, incəlik və yüksək keyfiyyət – bu qızıl üzük hər anınızı daha xüsusi edəcək."
    ],
    "132": ["Yeni qızıl sırğa modeli. Çəkisi: {weight} g, Əyarı: {gold_purity}"],
    "140": ["Yeni qızıl sep modeli."],
    "138": ["Yeni qızıl qolbaq modeli."],
    "144": ["Yeni qızıl komplekt."],
}

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

        name, slug = CATEGORY_DATA.get(category_id, ("Qızıl məhsul", "qizil-mehsul"))
        slug = f"{slug}-{random.randint(1000, 9999)}"
        description = random.choice(DESCRIPTIONS.get(category_id, ["Yeni qızıl məhsul."])).format(weight=weight, gold_purity=gold_purity)

        image_url = "https://karal.az/wp-content/uploads/2020/01/20200109_113139.jpg"

        product_data = {
            "name": name,
            "slug": slug,
            "type": "simple",
            "regular_price": price,
            "sale_price": sale_price if sale_price != "0" else None,
            "categories": [{"id": int(category_id)}],
            "description": description,
            "images": [{"src": image_url}],
            "attributes": [
                {"id": 2, "options": [gold_purity], "visible": True, "variation": False}
            ],
            "dimensions": {"weight": weight}
        }

        response = requests.post(f"{WC_API_URL}/products", json=product_data, auth=(WC_CONSUMER_KEY, WC_CONSUMER_SECRET))
        if response.status_code == 201:
            return jsonify({"status": "success", "message": "Товар добавлен!", "url": response.json()["permalink"]})

        return jsonify({"status": "error", "message": response.text}), 400

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8080)
