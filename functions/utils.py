from flask import jsonify
import qrcode
from io import BytesIO
import base64

def generate_qr(qrid):
    qr_data = f"http://127.0.0.1:5000/{qrid}"
    img = qrcode.make(qr_data)

    buffered = BytesIO()
    img.save(buffered, format="PNG")
    buffered.seek(0)
    img_base64 = base64.b64encode(buffered.getvalue()).decode()

    return {"qr": img_base64, "qr_data": qr_data}