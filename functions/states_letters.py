from supabase_client import supabase_exp
from datetime import datetime, timezone

now_utc = datetime.now(timezone.utc).isoformat()


def state_letter(status, id, sender_id=None, receiver_id=None):
    match status:
        case "disabled":
            return activate_qrcode(id)
        case "activated":
            return send_letter(id, sender_id, receiver_id)
        case "in transit":
            return letter_delivered(id)
        case "delivered":
            return {
                "template": "success_message.html", 
                "message": "Lettera gia scansionata ed arrivata con successo!"
            }
        
def activate_qrcode(id):
    response = (supabase_exp.table("QrCode")
                .update({"status": "activated", "activated_at": now_utc})
                .eq("id", id).execute())

    if response.data and len(response.data) > 0: 
        return {
            "template": "success_message.html", 
            "message": "QrCode attivato con successo"
        }
    else:
        return "error_message.html"

def send_letter(id, sender_id, receiver_id):
    response = (supabase_exp.table("QrCode")
                .update({"status": "in transit", "sent_at": now_utc, "sender": sender_id, "receiver": receiver_id})
                .eq("id", id).execute())

    if response.data and len(response.data) > 0: 
        return {
            "template": "success_message.html", 
            "message": "Lettera spedita con successo"
        }   
    else:
        return "error_message.html"

def letter_delivered(id):
    response = (supabase_exp.table("QrCode")
                .update({"status": "delivered", "delivered_at": now_utc})
                .eq("id", id).execute())

    if response.data and len(response.data) > 0: 
        return {
            "template": "success_message.html", 
            "message": "Lettera arrivata a destinazione"
        }
    else:
        return "error_message.html"