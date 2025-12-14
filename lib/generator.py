# lib/generator.py
import random
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import io
import requests # Untuk mengunduh template dari URL

# --- Fungsi Generator Data ---
def generate_random_name():
    first_names = ["Alex", "Jordan", "Taylor", "Morgan", "Casey", "Riley"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia"]
    return random.choice(first_names), random.choice(last_names)

def generate_gmail_email(first_name, last_name):
    digit_count = random.choice([3, 4])
    digits = ''.join([str(random.randint(0, 9)) for _ in range(digit_count)])
    return f"{first_name.lower()}.{last_name.lower()}{digits}@gmail.com"

def generate_birth_date():
    year = 2000 + random.randint(0, 5)
    month = str(random.randint(1, 12)).zfill(2)
    day = str(random.randint(1, 28)).zfill(2)
    return f"{year}-{month}-{day}"

# --- Fungsi Generator Gambar dengan Pillow ---
def generate_image_with_pillow(first_name, last_name):
    """
    Membuat gambar verifikasi dengan menambahkan teks ke template.
    Template diambil dari URL untuk kemudahan deploy.
    """
    try:
        # Gunakan template dari URL yang sudah saya siapkan
        template_url = "https://i.ibb.co/68v0h2F/template.png"
        response = requests.get(template_url)
        response.raise_for_status() # Akan error jika gagal download
        
        img = Image.open(io.BytesIO(response.content))
        draw = ImageDraw.Draw(img)
        
        # Gunakan font default yang pasti ada di Vercel
        try:
            font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
            font_info = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
        except IOError:
            # Fallback jika font tidak ditemukan
            font_title = ImageFont.load_default()
            font_info = ImageFont.load_default()

        # Tambahkan teks ke gambar
        psu_id = f"9{random.randint(10000000, 99999999)}"
        full_name = f"{first_name} {last_name}"
        major = "Computer Science (BS)"
        
        draw.text((50, 150), full_name, fill="black", font=font_title)
        draw.text((50, 200), f"ID: {psu_id}", fill="black", font=font_info)
        draw.text((50, 230), f"Major: {major}", fill="black", font=font_info)
        draw.text((50, 260), f"Status: Enrolled", fill="green", font=font_info)

        # Simpan gambar ke memory (bytes)
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        
        return img_byte_arr.getvalue()

    except Exception as e:
        raise Exception(f"Gagal membuat gambar: {str(e)}")
