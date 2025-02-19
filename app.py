def convert_video_without_resizing(video, filename_slug):
    """Конвертирует видео в MP4 без изменения размера"""
    try:
        temp_input = tempfile.NamedTemporaryFile(delete=False, suffix=".mov")
        temp_output = os.path.join(tempfile.gettempdir(), f"{filename_slug}.mp4")

        print(f"🔄 Сохраняем оригинальное видео {video.filename} во временный файл {temp_input.name}")
        video.save(temp_input.name)

        print("🔄 Начинаем конвертацию в MP4 без изменения размера...")

        # Конвертация без изменения разрешения
        ffmpeg.input(temp_input.name).output(
            temp_output, vcodec="libx264", acodec="aac", bitrate="2000k"
        ).run(overwrite_output=True)

        print(f"✅ Конвертация завершена: {temp_output}")
        return temp_output
    except Exception as e:
        print(f"❌ Ошибка конвертации видео: {e}")
        return None


def convert_and_crop_video(video, filename_slug):
    """ Обрезка видео в формат 1:1 и конвертация в MP4 (720x720) """
    try:
        temp_input = tempfile.NamedTemporaryFile(delete=False, suffix=".mov")
        temp_output = os.path.join(tempfile.gettempdir(), f"{filename_slug}_cropped.mp4")

        print(f"🔄 Сохраняем видео {video.filename} во временный файл {temp_input.name}")
        video.save(temp_input.name)

        print("🔄 Начинаем обрезку видео в 1:1 (720x720)...")

        # Обрезаем в 1:1 (центрируем)
        ffmpeg.input(temp_input.name).filter(
            "crop", "min(iw,ih)", "min(iw,ih)", "(iw-min(iw,ih))/2", "(ih-min(iw,ih))/2"
        ).filter(
            "scale", 720, 720
        ).output(
            temp_output, vcodec="libx264", acodec="aac", bitrate="2000k"
        ).run(overwrite_output=True)

        print(f"✅ Конвертация и обрезка завершены: {temp_output}")
        return temp_output
    except Exception as e:
        print(f"❌ Ошибка конвертации видео: {e}")
        return None


def upload_video_to_ftp(video_path, filename_slug):
    """ Загружает MP4 видео на FTP """
    try:
        print("📌 [DEBUG] Подключаемся к FTP серверу...")

        ftp = FTP(FTP_HOST)
        ftp.login(FTP_USER, FTP_PASS)

        ftp.cwd("/wp-content/uploads/original_videos/")
        print(f"📌 [DEBUG] Текущая директория FTP: {ftp.pwd()}")

        with open(video_path, "rb") as file:
            print(f"📌 [DEBUG] Загружаем файл {filename_slug}.mp4 ...")
            ftp.storbinary(f"STOR {filename_slug}.mp4", file)

        print(f"✅ Файл успешно загружен по FTP: /wp-content/uploads/original_videos/{filename_slug}.mp4")

        ftp.quit()
        return f"https://karal.az/wp-content/uploads/original_videos/{filename_slug}.mp4"
    except Exception as e:
        print(f"❌ Ошибка при загрузке файла по FTP: {e}")
        return None


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
            return jsonify({"status": "error", "message": "❌ Обязательные поля не заполнены"}), 400

        gold_purity = GOLD_PURITY_MAP.get(gold_purity_id, "585 (14K)")
        category_info = CATEGORY_DATA.get(category_id, {})
        product_name = random.choice(category_info["name"]) if isinstance(category_info["name"], list) else category_info["name"]
        product_slug = f"{category_info['slug']}-{random.randint(1000, 9999)}"

        print(f"📌 [INFO] Создаём товар: {product_name}, Slug: {product_slug}, Вес: {weight}, Цена: {price}")

        # 1️⃣ Сохраняем оригинал фото в `/original_photos/`
        original_photo_url = None
        if image:
            original_photo_url = save_original_file(image, product_slug, "original_photos")

        # 2️⃣ Обрабатываем фото и загружаем в WordPress (1000x1000)
        image_id = None
        if image:
            processed_image = process_image(image, product_slug)
            if processed_image:
                with open(processed_image, "rb") as img_file:
                    image_id = upload_media(img_file, filename=f"{product_slug}.jpg")

        # 3️⃣ Конвертируем MOV в MP4 (без изменений) и загружаем на FTP
        original_video_url = None
        if video:
            original_mp4 = convert_video_without_resizing(video, product_slug)
            if original_mp4:
                original_video_url = upload_video_to_ftp(original_mp4, product_slug)  # исправлен отступ


        # 4️⃣ Конвертируем и загружаем видео в WordPress (720x720)
        video_id = None
        if video:
            converted_video_path = convert_and_crop_video(video, product_slug)
            if converted_video_path:
                with open(converted_video_path, "rb") as converted_video:
                    video_id = upload_media(converted_video, filename=f"{product_slug}.mp4")

        print(f"✅ [INFO] Оригинальное фото: {original_photo_url}")
        print(f"✅ [INFO] Загруженное изображение ID: {image_id}")
        print(f"✅ [INFO] Оригинальное видео: {original_video_url}")
        print(f"✅ [INFO] Загруженное видео ID: {video_id}")

        # 5️⃣ Создаём товар в WooCommerce
        product_data = {
            "name": product_name,
            "slug": product_slug,
            "regular_price": price,
            "sale_price": sale_price if sale_price != "0" else None,
            "categories": [{"id": int(category_id)}],
            "images": [{"id": image_id}] if image_id else [],
            "attributes": [
                {"id": 2, "name": "Əyar", "options": [gold_purity], "visible": True, "variation": False}
            ],
            "meta_data": [
                {"key": "_weight", "value": weight},
                {"key": "_product_video_autoplay", "value": "on"},
                {"key": "_gold_purity", "value": gold_purity}
            ]
        }

        # Добавляем ссылки на оригиналы в мета-данные
        if original_photo_url:
            product_data["meta_data"].append({"key": "_original_photo_url", "value": original_photo_url})
        if original_video_url:
            product_data["meta_data"].append({"key": "_original_video_url", "value": original_video_url})

        # Добавляем видео в WooCommerce
        if video_id:
            product_data["meta_data"].append({"key": "_product_video_gallery", "value": video_id})

        print("📌 [INFO] Отправляем запрос на создание товара...")
        response = requests.post(
            WC_API_URL + "/products",
            json=product_data,
            params={"consumer_key": WC_CONSUMER_KEY, "consumer_secret": WC_CONSUMER_SECRET}
        )

        print(f"📌 [INFO] Ответ от сервера WooCommerce: {response.status_code}")
        print(f"📌 [INFO] Детали ответа: {response.text}")

        if response.status_code == 201:
            return jsonify({"status": "success", "message": "✅ Товар добавлен!"})
        else:
            print("❌ [ERROR] Ошибка при добавлении товара")
            return jsonify({"status": "error", "message": "❌ Ошибка при добавлении товара"}), 400
