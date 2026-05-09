from flask import Flask, request, jsonify
import hashlib

app = Flask(__name__)
SECRET_KEY = "JEPFX-2026-UNLOCKED"
VALID_USERS = {"JEPFX": "@JEPFX_1875", "SEAN": "SEAN_0", "N4XCO": "N4XCO_0"}

# Homepage
@app.route('/')
def home():
    return "✅ JEPFX SERVER ONLINE — DEPLOYED"

# Check License
@app.route('/api/check-license', methods=['POST'])
def check_license():
    data = request.get_json()
    if data.get("license_key") == SECRET_KEY:
        return jsonify({"status":"ok","message":"License Valid"}),200
    return jsonify({"status":"denied"}),403

# Validate User
@app.route('/api/validate-user', methods=['POST'])
def validate_user():
    data = request.get_json()
    if data.get("username") in VALID_USERS:
        return jsonify({"status":"ok"}),200
    return jsonify({"status":"denied"}),403

# Check Password
@app.route('/api/check-password', methods=['POST'])
def check_password():
    data = request.get_json()
    u = data.get("username")
    p = data.get("password")
    if u in VALID_USERS and VALID_USERS[u] == p:
        return jsonify({"status":"ok"}),200
    return jsonify({"status":"denied"}),403

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
