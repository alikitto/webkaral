import os
import base64
import requests
import boto3
import ffmpeg
from flask import Flask, render_template, request, jsonify
from PIL import Image, ImageOps
import io
import tempfile
import concurrent.futures

app = Flask(__name__)

# Cloudflare R2 Config
R2_ENDPOINT = os.getenv("R2_ENDPOINT")
R2_ACCESS_KEY = os.getenv("R2_ACCESS_KEY_ID")
R2_SECRET_KEY = os.getenv("R2_SECRET_ACCESS_KEY")
R2_BUCKET = os.getenv("R2_BUCKET_NAME")

# WooCommerce API Config
WC_API_URL = os.getenv("WC_API_URL")
WC_CONSUMER_KEY = os.getenv("WC_CONSUMER_KEY")
WC_CONSUMER_SECRET = os.getenv("WC_CONSUMER_SECRET")

# WordPress API Config
WP_USERNAME = os.getenv("WP_USERNAME")
WP_PASSWORD = os.getenv("WP_PASSWORD")
WP_MEDIA_URL = os.getenv("WP_MEDIA_URL")

# Auth
auth = base64.b64encode(f"{WP_USERNAME}:{WP_PASSWORD}".encode()).decode()
HEADERS = {"Authorization": f"Basic {auth}"}

# S3 Client for Cloudflare R2
s3_client = boto3.client(
    "s3",
    endpoint_url=R2_ENDPOINT,
    aws_access_key_id=R2_ACCESS_KEY,
    aws_secret_access_key=R2_SECRET_KEY
)

BITRATE = "1700k"

CATEGORY_DATA = {
    "126": {"name": "Qızıl üzük", "slug": "qizil-uzuk"},
    "132": {"name": "Qızıl sırğa", "slug": "qizil-sirqa"},
    "140": {"name": "Qızıl sep", "slug": "qizil-sep"},
    "138": {"name": "Qızıl qolbaq", "slug": "qizil-qolbaq"},
    "144": {"name": ["Qızıl dəst", "Qızıl komplekt"], "slug": "qizil-komplekt-dest"}
}

@app.route("/")
def home():
    return render_template("index.html", categories=CATEGORY_DATA)

def upload_to_r2(file_data, key):
    """Uploads a file to Cloudflare R2"""
    try:
        s3_client.upload_fileobj(file_data, R2_BUCKET, key, ExtraArgs={"ACL": "public-read"})
        return f"https://video.karal.az/{key}"
    except Exception as e:
        print(f"❌ Error uploading to R2: {e}")
        return None

def process_image(image):
    """Resize image to 1000x1000 and return as BytesIO"""
    img = Image.open(image)
    img = ImageOps.exif_transpose(img)
    img = img.resize((1000, 1000), Image.LANCZOS)
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="JPEG")
    img_bytes.seek(0)
    return img_bytes

def process_video(video):
    """Convert and crop video to 720x720 resolution with better quality"""
    try:
        temp_input = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
        temp_input.write(video.read())
        temp_input.close()
        temp_output = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
        (
            ffmpeg.input(temp_input.name)
            .filter('crop', 'min(iw,ih)', 'min(iw,ih)', '(iw-min(iw,ih))/2', '(ih-min(iw,ih))/2')
            .filter("scale", 720, 720)
            .output(temp_output.name, vcodec="libx264", acodec="aac", crf=23, bitrate=BITRATE, preset="slow", format="mp4")
            .run(overwrite_output=True)
        )
        temp_output.seek(0)
        return open(temp_output.name, 'rb')
    except Exception as e:
        print(f"❌ Error processing video: {e}")
        return None

def upload_to_wordpress(file_data, filename):
    """Uploads processed image to WordPress"""
    try:
        file_data.seek(0)
        files = {"file": (filename, file_data.getvalue(), "image/jpeg")}
        response = requests.post(WP_MEDIA_URL, headers=HEADERS, files=files)
        if response.status_code == 201:
            return response.json().get("id")
        return None
    except Exception as e:
        print(f"❌ Error uploading to WordPress: {e}")
        return None

@app.route("/add-product", methods=["POST"])
def add_product():
    try:
        data = request.form
        category_id = data.get("category")
        price = data.get("price")
        sale_price = data.get("sale_price", "0")
        weight = data.get("weight")
        sku = data.get("sku")
        image = request.files.get("image")
        video = request.files.get("video")
        product_slug = f"{CATEGORY_DATA.get(category_id, {}).get('slug', 'unknown')}-{sku}"

        image_id = upload_to_wordpress(process_image(image), f"{product_slug}.jpg") if image else None
        video_url = upload_to_r2(process_video(video), f"product_videos/{product_slug}.mp4") if video else None

        product_data = {
            "name": f"Product {category_id}",
            "slug": product_slug,
            "sku": sku,
            "regular_price": price,
            "sale_price": sale_price if sale_price != "0" else None,
            "categories": [{"id": int(category_id)}],
            "images": [{"id": image_id}] if image_id else [],
            "meta_data": [{"key": "_weight", "value": weight}]
        }

        if video_url:
            
            product_data["meta_data"].append({"key": "_product_video_gallery", "value": video_url})

        response = requests.post(
            WC_API_URL + "/products",
            json=product_data,
            params={"consumer_key": WC_CONSUMER_KEY, "consumer_secret": WC_CONSUMER_SECRET}
        )
        
        return jsonify({"status": "success" if response.status_code == 201 else "error", "message": response.text})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

if __name__ == "__main__":
    app.run(debug=True)
