from flask import Flask, request, jsonify
import hashlib

app = Flask(__name__)

# --- CONFIG (same as your tool) ---
SECRET_KEY = "JEPFX-2026-UNLOCKED"
VALID_USERS = ["JEPFX", "SEAN", "N4XCO"]
CURRENT_VERSION = "BETA v6"

# ---------------- API ENDPOINTS ----------------
@app.route('/')
def home():
    return
@app.route('/api/check-license', methods=['POST'])
def check_license():
    data = request.get_json()
    user_key = data.get("license_key", "")
    
    # Hash key to compare securely
    hashed_input = hashlib.sha256(user_key.encode()).hexdigest()
    correct_hash = hashlib.sha256(SECRET_KEY.encode()).hexdigest()

    if hashed_input == correct_hash:
        return jsonify({
            "status": "valid",
            "message": "✅ License ACTIVATED",
            "version": CURRENT_VERSION
        })
    else:
        return jsonify({"status": "invalid", "message": "❌ Wrong License Key"}), 403


@app.route('/api/check-update', methods=['GET'])
def check_update():
    return jsonify({
        "current_version": CURRENT_VERSION,
        "latest_version": "BETA v6", # change when you update
        "update_available": False,
        "download_url": "https://drive.google.com/drive/folders/1lmmSLacuObNoCpE7DVJuvuqDuYt1teqD"
    })


@app.route('/api/validate-user', methods=['POST'])
def validate_user():
    data = request.get_json()
    username = data.get("username", "").upper()
    if username in VALID_USERS:
        return jsonify({"status": "ok", "message": "User authorized"})
    return jsonify({"status": "denied", "message": "User not found"}), 403


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000) # Render uses port 10000 by default
