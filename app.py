from flask import Flask, jsonify, render_template, request, send_file
from datetime import datetime, timezone
from io import BytesIO
from supabase_client import supabase_exp
from functions.states_letters import state_letter
from functions.utils import generate_qr
from dotenv import load_dotenv
import qrcode
import base64
import os

load_dotenv()

URL = os.getenv("URL")

app = Flask(__name__)

sender_id = {
    "user_1": {
        "id": 112654,
        "name": "Gabriele Giustozzi"
    },

    "user_2": {
        "id": 220906,
        "name": "Giorgia D'Ortona"
    }
}

@app.route("/", methods=["GET", "POST"])
def home():
    return render_template("home.html")

@app.route("/<int:qrid>", methods=["GET", "POST"])
def check_mail(qrid):
    if request.method == "POST":
        sender = request.form.get("pin")
        
        if int(sender) == sender_id["user_1"]["id"] or int(sender) == sender_id["user_2"]["id"]: 
            response = ( supabase_exp.table("QrCode").select().eq("id", qrid).single().execute())

            if response.data and len(response.data) > 0: 
                result = state_letter(response.data['status'], qrid, sender)
                return render_template(result["template"], message=result["message"]) 
            else:
                return render_template("error_message.html", error="Errore di connessione al database", redirect=str(qrid))
        else:
            return render_template("error_message.html", error="Pin errato, riporva!", redirect=str(qrid))

    
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
    
@app.route("/status", methods=["GET", "POST"])
def status():
    if request.method == "POST":
        sender = request.form.get("pin")

        if int(sender) == sender_id["user_1"]["id"] or int(sender) == sender_id["user_2"]["id"]: 
            response = (supabase_exp.table("QrCode").select("*").eq("sender", int(sender)).order("status", desc=False).execute())

            badge = {
                "disabled": {"class": "bg-secondary", "label": "Non attivo", "function": "activateQRCode"},
                "activated": {"class": "bg-primary", "label": "Attivo"},
                "in transit": {"class": "bg-warning", "label": "In transito"},
                "delivered": {"class": "bg-success", "label": "Consegnato"}
            }

            if response.data and len(response.data) > 0: 
                return render_template("status.html", data=response.data, badge=badge, sender=int(sender))
            else:
                return render_template("error_message.html", error="Nessuna lettere spedita da te!", redirect="qrManager")
            
        else:
            return render_template("error_message.html", error="User id inesistente, riporva!", redirect="qrManager")
    
    return render_template("pin_form.html")

@app.route("/status/modify/<int:id>/<int:sender>")
def modify_status(id, sender):
    now_utc = datetime.now(timezone.utc).isoformat() 
    response = (supabase_exp.table("QrCode").update({"status": "activated", "activated_at": now_utc}).eq("id", id).eq("sender", sender).execute())

    if response.data and len(response.data) > 0: 
        return jsonify({"success": True})
    else:
        return jsonify({"success": False}), 404
    
@app.route("/test")
def test():
    return render_template("success_message.html", message="Che test ragazzi") 

if __name__ == '__main__':
    app.run(debug=True)
