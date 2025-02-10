from flask import Flask, request, jsonify, render_template
import requests
import os

app = Flask(__name__)

WC_API_URL = os.getenv("WC_API_URL")
WC_CONSUMER_KEY = os.getenv("WC_CONSUMER_KEY")
WC_CONSUMER_SECRET = os.getenv("WC_CONSUMER_SECRET")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/add_product", methods=["POST"])
def add_product():
    data = request.json

    product_data = {
        "name": data.get("name"),
        "type": "simple",
        "regular_price": data.get("price"),
        "description": f"Товар: {data.get('name')} с пробой {data.get('purity')} и весом {data.get('weight')} г",
        "categories": [{"id": data.get("category_id")}],
        "images": [{"src": data.get("image")}],
        "weight": data.get("weight"),
        "attributes": [
            {
                "id": 2,
                "name": "Əyar",
                "options": [data.get("purity")]
            }
        ]
    }

    response = requests.post(
        f"{WC_API_URL}/products",
        json=product_data,
        auth=(WC_CONSUMER_KEY, WC_CONSUMER_SECRET)
    )

    if response.status_code == 201:
        return jsonify({"message": "Товар успешно добавлен!", "status": "success"}), 201
    else:
        return jsonify({
            "message": "Ошибка при добавлении товара.",
            "details": response.text,
            "status": "error"
        }), response.status_code


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
