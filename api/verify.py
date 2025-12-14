# api/verify.py
import json
import logging
import re
from http import HTTPStatus
import httpx
import random

# Impor fungsi dari folder lib
from lib.generator import generate_random_name, generate_image_with_pillow, generate_birth_date

# Konfigurasi
SHEERID_BASE_URL = 'https://services.sheerid.com'
DEFAULT_SCHOOL_ID = '8387'
SCHOOLS = {
    '8387': { 'name': 'Pennsylvania State University-Penn State Harrisburg' }
}

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def handler(request):
    if request.method != 'POST':
        return json.dumps({"error": "Method not allowed"}), 405, {'Content-Type': 'application/json'}

    try:
        body = json.loads(request.body)
        sheerid_url = body.get("url")
        if not sheerid_url:
            return json.dumps({"error": "Missing 'url' in request body"}), 400, {'Content-Type': 'application/json'}

        match = re.search(r"verificationId=([a-f0-9]+)", sheerid_url, re.IGNORECASE)
        if not match:
            return json.dumps({"error": "Invalid SheerID URL format"}), 400, {'Content-Type': 'application/json'}
        
        verification_id = match.group(1)
        logger.info(f"Memulai verifikasi untuk ID: {verification_id}")

        # 1. Generate data palsu
        first_name, last_name = generate_random_name()
        email = generate_gmail_email(first_name, last_name)
        birth_date = generate_birth_date()
        
        # 2. Generate gambar
        img_data = generate_image_with_pillow(first_name, last_name)
        logger.info("Gambar verifikasi berhasil dibuat.")

        # 3. Jalankan proses verifikasi
        with httpx.Client(timeout=30.0) as client:
            device_fingerprint = ''.join(random.choice('0123456789abcdef') for _ in range(32))
            school_name = SCHOOLS[DEFAULT_SCHOOL_ID]['name']
            
            step2_body = {
                "firstName": first_name, "lastName": last_name, "birthDate": birth_date,
                "email": email, "phoneNumber": "",
                "organization": {"id": int(DEFAULT_SCHOOL_ID), "idExtended": DEFAULT_SCHOOL_ID, "name": school_name},
                "deviceFingerprintHash": device_fingerprint, "locale": "en-US",
                "metadata": {"refererUrl": sheerid_url, "verificationId": verification_id},
            }
            
            # Kirim data pribadi
            resp, status = _sheerid_request(client, "POST", f"{SHEERID_BASE_URL}/rest/v2/verification/{verification_id}/step/collectStudentPersonalInfo", step2_body)
            if status != 200 or resp.get("currentStep") == "error":
                raise Exception(f"Gagal kirim data: {resp.get('errorIds', 'Unknown error')}")
            logger.info("Data pribadi berhasil dikirim.")

            # Upload dokumen
            step4_body = {"files": [{"fileName": "student_card.png", "mimeType": "image/png", "fileSize": len(img_data)}]}
            step4_data, step4_status = _sheerid_request(client, "POST", f"{SHEERID_BASE_URL}/rest/v2/verification/{verification_id}/step/docUpload", step4_body)
            if not step4_data.get("documents"):
                raise Exception("Gagal mendapatkan upload URL.")
            upload_url = step4_data["documents"][0]["uploadUrl"]
            
            upload_response = client.put(upload_url, content=img_data, headers={"Content-Type": "image/png"})
            if not (200 <= upload_response.status_code < 300):
                raise Exception(f"Gagal upload ke S3: {upload_response.status_code}")
            logger.info("Dokumen berhasil diunggah.")

            final_data, _ = _sheerid_request(client, "POST", f"{SHEERID_BASE_URL}/rest/v2/verification/{verification_id}/step/completeDocUpload")
            logger.info(f"Proses selesai. Status akhir: {final_data.get('currentStep')}")

        return json.dumps({
            "success": True,
            "message": "Verifikasi berhasil dikirim, status menunggu review.",
            "details": final_data
        }), 200, {'Content-Type': 'application/json'}

    except Exception as e:
        logger.error(f"Terjadi kesalahan: {e}")
        return json.dumps({
            "success": False,
            "message": f"Verifikasi gagal: {str(e)}"
        }), 500, {'Content-Type': 'application/json'}

def _sheerid_request(client, method, url, body=None):
    headers = {"Content-Type": "application/json"}
    response = client.request(method, url, json=body, headers=headers)
    try:
        return response.json(), response.status_code
    except:
        return response.text, response.status_code
