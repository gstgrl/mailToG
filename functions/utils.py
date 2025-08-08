from flask import jsonify
from io import BytesIO
from dotenv import load_dotenv
import os
import qrcode
import base64

load_dotenv()

URL = os.getenv("URL")

def generate_qr(qrid):
    qr_data = f"{URL}/{qrid}"
    img = qrcode.make(qr_data)

    buffered = BytesIO()
    img.save(buffered, format="PNG")
    buffered.seek(0)
    img_base64 = base64.b64encode(buffered.getvalue()).decode()

    return {"qr": img_base64, "qr_data": qr_data}