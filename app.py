from flask import Flask, request
import requests
import os
import tensorflow as tf
from PIL import Image, ImageOps
import numpy as np

app = Flask(__name__)

# ====== REPLACE THESE ======
VERIFY_TOKEN = "my_verify_token"
ACCESS_TOKEN = "EAARZAVGHPLpQBQymH7Qt5SYSv7HR4c1hrS0g3N0VWVIQHE3HXYxUsV7POPA4l4hs7KG3gQEBrXuWDafADTrcfcg0WVD6XNOObRkurwLENqSWZB1Gl9JjkuhJzxQF8ZCMfgeyzHwHfHaZBSjIzu30Gxj6Dk5iThBrdupxigWCDKMlor1FUfO3LK68RifZCiqJpwAZDZD"
PHONE_NUMBER_ID = "1040714015786345"
# ===========================

DISEASE_MANAGEMENT = {
    "Bacterial Leaf Blight": "⚠️ *Bacterial Leaf Blight (பாக்டீரியா இலை கருகல் நோய்)* symptoms theriyudhu.\n\n✅ *Management:*\nStreptomycin sulphate + Tetracycline combination (e.g., Streptocycline) @ 120g/acre + Copper oxychloride @ 500g/acre water-la mix panni thelikkavum.",
    "Brown Spot": "⚠️ *Brown Spot (பழுப்பு புள்ளி நோய்)* affect aagirukku.\n\n✅ *Management:*\nMancozeb 2.0 g/litre or Edifenphos 1 ml/litre of water-la mix panni spray pannunga.",
    "Healthy Rice Leaf": "🌿 Super! Unga nel payir (paddy crop) healthy-a irukku. Endha noyum illai. Nalla yield kidaikka vaazhthukkal!",
    "Leaf Blast": "⚠️ *Leaf Blast (குலை நோய்)* symptoms irukku.\n\n✅ *Management:*\nTricyclazole 75 WP @ 200g/acre or Pseudomonas fluorescens @ 1kg/acre spray pannunga. Thanneer thengama paathukonga.",
    "Leaf scald": "⚠️ *Leaf Scald (இலை கருகல் / வெளிறிய நோய்)* symptoms theriyudhu.\n\n✅ *Management:*\nHexaconazole 5 EC @ 2 ml/litre or Propiconazole 25 EC @ 1 ml/litre thanneer-la mix panni spray pannavum.",
    "Sheath Blight": "⚠️ *Sheath Blight (இலை உறை அழுகல் நோய்)* affect aagirukku.\n\n✅ *Management:*\nCarbendazim 50 WP @ 200g/acre or Propiconazole 25 EC @ 200 ml/acre spray pannunga. Payir idaiveli (spacing) maintain pannavum."
}

def predict_paddy_disease(image_path, model_path='keras_model.h5', labels_path='labels.txt'):
    np.set_printoptions(suppress=True)
    
    # Clean load model - bypasses no longer needed with TF 2.15
    model = tf.keras.models.load_model(model_path, compile=False)
    
    with open(labels_path, "r") as f:
        class_names = f.readlines()

    data = np.ndarray(shape=(1, 224, 224, 3), dtype=np.float32)
    image = Image.open(image_path).convert("RGB")
    size = (224, 224)
    image = ImageOps.fit(image, size, Image.Resampling.LANCZOS)

    image_array = np.asarray(image)
    normalized_image_array = (image_array.astype(np.float32) / 127.5) - 1
    data[0] = normalized_image_array

    prediction = model.predict(data)
    index = np.argmax(prediction)
    class_name = class_names[index].strip()
    
    if " " in class_name:
        class_name = class_name.split(" ", 1)[1]
        
    confidence_score = prediction[0][index]
    return class_name, confidence_score

@app.route("/webhook", methods=["GET"])
def verify():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode and token:
        if mode == "subscribe" and token == VERIFY_TOKEN:
            return challenge, 200
    return "Verification failed", 403

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    try:
        message = data["entry"][0]["changes"][0]["value"]["messages"][0]
        sender = message["from"]

        if message["type"] == "image":
            media_id = message["image"]["id"]
            media_url = get_media_url(media_id)
            
            download_image(media_url, media_id)
            local_image_path = f"images/{media_id}.jpg"

            send_whatsapp_message(sender, "🔍 Image received! Analyzing paddy leaf... Please wait.")

            try:
                predicted_class, confidence = predict_paddy_disease(local_image_path)
                advice = DISEASE_MANAGEMENT.get(predicted_class, "Diagnosis complete, but specific management not found. Please consult an expert.")
                reply_text = f"📊 *Diagnosis:* {predicted_class}\n🎯 *Accuracy:* {confidence * 100:.1f}%\n\n{advice}"
                
            except Exception as e:
                print(f"Prediction Error: {e}")
                reply_text = "Sorry, model process pandrathula oru error vandhuduchu. Please try again with a clear image."

        else:
            reply_text = "🌱 Please send a clear image of the paddy leaf to detect disease."

        send_whatsapp_message(sender, reply_text)

    except KeyError:
        pass 
    except Exception as e:
        print("Webhook Error:", e)

    return "OK", 200

def get_media_url(media_id):
    url = f"https://graph.facebook.com/v19.0/{media_id}"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
    response = requests.get(url, headers=headers)
    return response.json()["url"]

def download_image(url, media_id):
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
    response = requests.get(url, headers=headers)
    if not os.path.exists("images"):
        os.makedirs("images")
    with open(f"images/{media_id}.jpg", "wb") as f:
        f.write(response.content)

def send_whatsapp_message(to, text):
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text}
    }
    requests.post(url, headers=headers, json=payload)

if __name__ == "__main__":
    app.run(port=5000)