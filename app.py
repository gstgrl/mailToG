from flask import Flask, jsonify, render_template, request, send_file
import qrcode
from io import BytesIO
import base64
from supabase_client import supabase_exp
from functions.states_letters import state_letter
from functions.utils import generate_qr
from dotenv import load_dotenv
import os

load_dotenv()

URL = os.getenv("URL")

app = Flask(__name__)

static_pin = 2203

@app.route("/", methods=["GET", "POST"])
def home():
    return render_template("home.html")

@app.route("/<int:qrid>", methods=["GET", "POST"])
def check_mail(qrid):
    if request.method == "POST":
        pin = request.form.get("pin")
        
        if int(pin) == static_pin: 
            response = ( supabase_exp.table("QrCode").select().eq("id", qrid).single().execute())

            if response.data and len(response.data) > 0: 
                result = state_letter(response.data['status'], qrid)
                return render_template(result["template"], message=result["message"]) 
            else:
                return render_template("error_message.html", error="Errore di connessione al database", id=qrid)
        else:
            return render_template("error_message.html", error="Pin errato, riporva!", id=qrid)

    
    return render_template("pin_form.html")

@app.route("/qr")
def create_QR():
    response = (supabase_exp.table("QrCode").insert({}).execute())

    if response.data and len(response.data) > 0: 
        qrid = response.data[0]["id"]
        response_qr = generate_qr(qrid)


        url = f"{URL}/{qrid}"
        data = request.args.get("data", response_qr["qr_data"])


        return render_template("qrCode_generated.html", qr_code=response_qr["qr"], data=data, url=response_qr["qr_data"])
    else:
        return render_template("error_message.html", error="Errore di connessione col database! QrCode non generato")
    
@app.route("/qrManager")
def qr_manager():
    return render_template("qrCode_manager.html")

@app.route("/qrManager/generate_qr/<int:qrid>")
def generate_qr_for_status(qrid):
    qr_data = f"{URL}/{qrid}"
    img = qrcode.make(qr_data)

    buffered = BytesIO()
    img.save(buffered, format="PNG")
    buffered.seek(0)
    img_base64 = base64.b64encode(buffered.getvalue()).decode()

    return {"qr": img_base64, "qr_data": qr_data}

@app.route("/qrManager/change_status/<int:qrid>/<string:status>")
def change_status(qrid, status):
    response = ( supabase_exp.table("QrCode").update({"status": status}).eq("id", qrid).execute())

    if response.data and len(response.data) > 0:
        return jsonify({"message": "Status updated", "new_status": status})
    else:
        return jsonify({"error": "Failed to update"}), 400
    
@app.route("/qr/download/<string:data>")
def download_qr(data):
    # Genera QR code come file
    img = qrcode.make(data)
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name="qrcode.png",
        mimetype="image/png"
    )
    
@app.route("/status")
def status():
    response = (supabase_exp.table("QrCode").select("*").execute())

    badge_classes = {
        "disabled": "bg-secondary",
        "activated": "bg-primary",
        "in transit": "bg-warning",
        "delivered": "bg-success"
    }

    badge_labels = {
        "disabled": "Non attivo",
        "activated": "Attivo",
        "in transit": "In transito",
        "delivered": "Consegnato"
    }


    if response.data and len(response.data) > 0: 
        return render_template("status.html", data=response.data, badge_classes=badge_classes, badge_labels=badge_labels)
    else:
        return render_template("error_message.html", error="Errore di connessione con il database!") 
    
@app.route("/test")
def test():
    return render_template("success_message.html", message="Che test ragazzi") 

if __name__ == '__main__':
    app.run(debug=True)
