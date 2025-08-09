from flask import Flask, jsonify, render_template, request, send_file, session
from datetime import datetime, timezone, timedelta
from io import BytesIO
from supabase_client import supabase_exp
from functions.states_letters import state_letter
from functions.utils import generate_qr
from dotenv import load_dotenv
from babel.dates import format_datetime as babel_format_datetime
import qrcode
import base64
import os
import pytz

load_dotenv()

URL = os.getenv("URL")

app = Flask(__name__)
app.permanent_session_lifetime = timedelta(minutes=4)
app.secret_key = os.getenv("SECRETKEY")


users = {
    "user_1": {
        "pin": 112654,
        "id": 20010307,
        "name": "Gabriele Giustozzi"
    },

    "user_2": {
        "pin": 222222,
        "id": 20062209,
        "name": "Giorgia D'Ortona"
    }
}
badge = {
    "disabled": {"class": "bg-secondary", "label": "Non attivo", "function": "activateQRCode"},
    "activated": {"class": "bg-primary", "label": "Attivo", "time": {"label": "Attivato il: ", "column": "activated_at"}},
    "in transit": {"class": "bg-warning", "label": "In transito", "time": {"label": "Spedito il: ", "column": "sent_at"}},
    "delivered": {"class": "bg-success", "label": "Consegnato", "time": {"label": "Arrivato il: ", "column": "delivered_at"}}
}

id_to_name = {v["id"]: v["name"] for v in users.values()}
pin_to_user = {v["pin"]: v for v in users.values()}



@app.route("/", methods=["GET", "POST"])
def home():
    return render_template("home.html")



#CREAZIONE QR

@app.route("/<int:qrid>", methods=["GET", "POST"])
def check_mail(qrid):
    if request.method == "POST":
        
        sender = request.form.get("pin")
        receiver = users["user_2"]["id"] if int(sender) == users["user_1"]["id"] else users["user_1"]["id"]


        if int(sender) == users["user_1"]["id"] or int(sender) == users["user_2"]["id"]: 
            response = (supabase_exp.table("QrCode").select().eq("id", qrid).limit(1).execute())

            if response.data and len(response.data) > 0: 
                data = response.data[0]
                result = state_letter(data['status'], qrid, sender, receiver)

                return render_template(result["template"], message=result["message"]) 
            else:
                return render_template("error_message.html", error="Errore di connessione al database o  QRcode inesistente", redirect="")
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



#GESTIONE QR

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

@app.route("/qrManager/qrCodeList")
def qr_codes_list():
    response = (supabase_exp.table("QrCode").select("*").order("status", desc=False).execute())

    if response.data and len(response.data) > 0: 
        return render_template("qr_list.html", data=response.data, badge=badge, redirect="qrManager", title="Lista QRcode")
    else:
        return render_template("error_message.html", error="Nessuna QRcode inattivo!", redirect="qrManager")


#PRIVATO

@app.route("/private", methods=["GET", "POST"])
def private():
    session.permanent = True

    if session.get("pin_verified"):
        return render_template("private.html")


    if request.method == "POST":
        pin = int(request.form.get("pin"))
        user = pin_to_user.get(pin)


        if user: 
            session["pin_verified"] = True
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]

            return render_template("private.html")
        else:
            return render_template("error_message.html", error="User id inesistente, riporva!", redirect="private")
    
    return render_template("pin_form.html")

@app.route("/private/outgoing")
def outgoing():
    user_id = session.get("user_id")
    response = (supabase_exp.table("QrCode").select("*").eq("sender", int(user_id)).order("status", desc=False).execute())

    if response.data and len(response.data) > 0: 
        return render_template("qr_list.html", data=response.data, badge=badge, title="Lettere in arrivo", redirect="private", private=True)
    else:
        return render_template("error_message.html", error="Nessuna lettere in arrivo per te!", redirect="private")
    
@app.route("/private/incoming")
def incoming():
    user_id = session.get("user_id")
    response = (supabase_exp.table("QrCode").select("*").eq("receiver", int(user_id)).order("status", desc=False).execute())

    if response.data and len(response.data) > 0: 
        return render_template("qr_list.html", data=response.data, badge=badge, title="Lettere in arrivo", redirect="private", private=True)
    else:
        return render_template("error_message.html", error="Nessuna lettere in arrivo per te!", redirect="private")

@app.route("/status/modify/<int:id>")
def modify_status(id):
    now_utc = datetime.now(timezone.utc).isoformat() 
    response = (supabase_exp.table("QrCode").update({"status": "activated", "activated_at": now_utc}).eq("id", id).execute())

    if response.data and len(response.data) > 0: 
        return jsonify({"success": True})
    else:
        return jsonify({"success": False}), 404



#FILTRI  
@app.template_filter("format_datetime")
def format_datetime_it(value, format="d MMMM yyyy, HH:mm"):
    try:
        dt = datetime.fromisoformat(value)
        local_tz = pytz.timezone("Europe/Rome")
        dt = dt.astimezone(local_tz)
        return babel_format_datetime(dt, format, locale="it_IT")
    except Exception:
        return "Data non valida"

@app.template_filter("get_name")
def get_name(user_id):
    return id_to_name.get(user_id, "")

@app.route("/test")
def test():
    session.clear()

    return render_template("success_message.html", message="Che test ragazzi") 

if __name__ == '__main__':
    app.run(debug=True)
