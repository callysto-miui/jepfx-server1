from flask import Flask, request, jsonify
import hashlib
import datetime
import os

app = Flask(__name__)

# ==============================================
# ✅ EXACT YOUR LICENSES — PERMANENT / 1PC LOGIC
# ==============================================
LICENSES = {
    # 🔓 PERMANENT / UNLIMITED KEYS (CAN BE USED ON MULTIPLE PCS)
    "JEPFX-2026-SECRET": {
        "type": "unlimited",
        "hwid": [],
        "expires_at": None
    },
    # 🔒 SINGLE PC KEYS (1 KEY = 1 DEVICE ONLY)
    "JEPFX-2026-001": {"type": "single", "hwid": "", "expires_at": None},
    "JEPFX-2026-002": {"type": "single", "hwid": "", "expires_at": None},
    "JEPFX-2026-003": {"type": "single", "hwid": "", "expires_at": None},
    "JEPFX-2026-004": {"type": "single", "hwid": "", "expires_at": None},
    "JEPFX-2026-005": {"type": "single", "hwid": "", "expires_at": None}
}

# ==============================================
# ✅ EXACT YOUR VALID USERS
# ==============================================
VALID_USERS = {
    "JEPFX": "@JEPFX_1875",
    "SEAN": "SEAN_0",
    "N4XCO": "N4XCO_0",
    "RHYZ": "RHYZ_0"
}

# ==============================================
# ✅ API ROUTES — FULLY WORKING + YOUR LOGIC
# ==============================================

# --------------------------
# 1. ACTIVATE LICENSE
# --------------------------
@app.route('/api/activate', methods=['POST'])
def activate_license():
    try:
        data = request.get_json()
        license_key = data.get('license_key', '').strip()
        hardware_id = data.get('hardware_id', '').strip()

        if not license_key or not hardware_id:
            return jsonify({"msg": "Missing required fields"}), 400

        # Check if key exists
        if license_key not in LICENSES:
            return jsonify({"msg": "❌ Invalid License Key"}), 403

        key_data = LICENSES[license_key]
        key_type = key_data["type"]

        # ✅ UNLIMITED / PERMANENT KEY — ALLOW ANY PC
        if key_type == "unlimited":
            if hardware_id not in key_data["hwid"]:
                key_data["hwid"].append(hardware_id)
            return jsonify({"msg": "✅ Activated Successfully! (Unlimited Key)"}), 200

        # ✅ SINGLE PC KEY — ONLY 1 DEVICE
        elif key_type == "single":
            if key_data["hwid"] == "":
                # First activation — save this PC
                key_data["hwid"] = hardware_id
                return jsonify({"msg": "✅ Activated Successfully! (Single PC)"}), 200
            elif key_data["hwid"] == hardware_id:
                # Same PC — already activated
                return jsonify({"msg": "✅ Already Activated on this PC"}), 200
            else:
                # Different PC — BLOCK
                return jsonify({"msg": "❌ Key registered to another PC"}), 403

        else:
            return jsonify({"msg": "❌ Invalid Key Type"}), 403

    except Exception as e:
        return jsonify({"msg": f"Server Error: {str(e)}"}), 500


# --------------------------
# 2. VERIFY LICENSE (EVERY LAUNCH)
# --------------------------
@app.route('/api/verify-license', methods=['POST'])
def verify_license():
    try:
        data = request.get_json()
        hwid = data.get('hwid', '').strip()
        key_hash = data.get('hash', '').strip()

        if not hwid or not key_hash:
            return jsonify({"msg": "Invalid data"}), 400

        # Check every key
        for key, info in LICENSES.items():
            # ✅ Unlimited key
            if info["type"] == "unlimited":
                if hwid in info["hwid"] and hashlib.sha256(key.encode()).hexdigest() == key_hash:
                    return jsonify({"status": "ok"}), 200
            # ✅ Single PC key
            elif info["type"] == "single":
                if info["hwid"] == hwid and hashlib.sha256(key.encode()).hexdigest() == key_hash:
                    return jsonify({"status": "ok"}), 200

        return jsonify({"msg": "❌ License Revoked or Invalid"}), 403

    except Exception as e:
        return jsonify({"msg": f"Server Error: {str(e)}"}), 500


# --------------------------
# 3. VALIDATE USERNAME
# --------------------------
@app.route('/api/validate-user', methods=['POST'])
def validate_user():
    try:
        data = request.get_json()
        username = data.get('username', '').strip()

        if username in VALID_USERS:
            return jsonify({"status": "ok"}), 200
        else:
            return jsonify({"msg": "❌ User Not Found"}), 404

    except Exception as e:
        return jsonify({"msg": "Server Error"}), 500


# --------------------------
# 4. CHECK PASSWORD
# --------------------------
@app.route('/api/check-password', methods=['POST'])
def check_password():
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()

        if username in VALID_USERS and VALID_USERS[username] == password:
            return jsonify({"status": "ok"}), 200
        else:
            return jsonify({"msg": "❌ Wrong Password"}), 403

    except Exception as e:
        return jsonify({"msg": "Server Error"}), 500


# --------------------------
# 5. CHECK UPDATE
# --------------------------
@app.route('/api/check-update', methods=['GET'])
def check_update():
    return jsonify({
        "update_available": False,
        "latest_version": "BETA v7",
        "download_url": ""
    }), 200


# ==============================================
# ✅ RUN SERVER
# ==============================================
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
