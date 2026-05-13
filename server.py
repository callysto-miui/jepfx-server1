from flask import Flask, request, jsonify
import hashlib
from datetime import datetime, timedelta
import uuid
import json
import os

app = Flask(__name__)

# File to store data permanently
DATA_FILE = "server_data.json"

# ==================================================
# 📝 LICENSES & USERS - EDIT THESE AS NEEDED
# ==================================================
LICENSES = {
    # 🔓 PERMANENT KEYS
    "JEPFX-2026": {
        "type": "unlimited",
        "hwid": [],
        "expires_at": None
    },
    "JEPFX-2026-001": {"type": "single", "hwid": "", "expires_at": None},
    "JEPFX-2026-002": {"type": "single", "hwid": "", "expires_at": None},
    "JEPFX-2026-003": {"type": "single", "hwid": "", "expires_at": None},
    "JEPFX-2026-004": {"type": "single", "hwid": "", "expires_at": None},
    "JEPFX-2026-005": {"type": "single", "hwid": "", "expires_at": None}
}

VALID_USERS = {
    "JEPFX": "@JEPFX_1875",
    "SEAN": "SEAN_0",
    "N4XCO": "N4XCO_0",
    "RHYZ": "RHYZ_0"
}

# Trial data storage - loaded from file on startup
TRIAL_LICENSES = {}
TRIAL_USERS = {}

# ==================================================
# 💾 DATA LOAD & SAVE FUNCTIONS
# ==================================================
def load_data():
    """Load saved data from file, or create new if file doesn't exist"""
    global TRIAL_LICENSES, TRIAL_USERS
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
                TRIAL_LICENSES = data.get("trials", {})
                TRIAL_USERS = data.get("users", {})
        except Exception as e:
            print(f"Error loading data: {e}")
            TRIAL_LICENSES = {}
            TRIAL_USERS = {}
    else:
        save_data()  # Create empty file if none exists

def save_data():
    """Save current data to file"""
    data = {
        "trials": TRIAL_LICENSES,
        "users": TRIAL_USERS
    }
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error saving data: {e}")

# ==================================================
# 🔑 ADMIN KEY - MUST BE EXACT SAME IN BOTH FILES
# ==================================================
ADMIN_KEY = "JEPFX-ADMIN-2026"

# Load data when server starts
load_data()

# ==================================================
# 🚀 API ROUTES
# ==================================================
@app.route('/')
def home():
    return "✅ JEPFX SERVER | PERMANENT + TRIAL + MONITOR"

# ------------------------------
# GENERATE NEW TRIAL
# ------------------------------
@app.route('/api/admin/generate-trial', methods=['POST'])
def generate_trial():
    data = request.get_json()
    if not data or data.get("admin_key") != ADMIN_KEY:
        return jsonify({"status": "denied"}), 403

    duration_hours = int(data.get("duration_hours", 3))
    trial_license = f"JEPFX-TRIAL-{uuid.uuid4().hex[:8].upper()}"
    trial_user = f"TRIAL-{uuid.uuid4().hex[:6].upper()}"
    trial_pass = uuid.uuid4().hex[:10].upper()

    TRIAL_LICENSES[trial_license] = {
        "type": "trial",
        "hwid": "",
        "duration_hours": duration_hours,
        "start_time": None,
        "expires_at": None,
        "activated_at": None
    }

    TRIAL_USERS[trial_user] = {
        "password": trial_pass,
        "linked_license": trial_license
    }

    # Save to file immediately
    save_data()

    return jsonify({
        "trial_license": trial_license,
        "trial_username": trial_user,
        "trial_password": trial_pass,
        "duration_hours": duration_hours
    }), 200

# ------------------------------
# GET ALL TRIALS (WITH CORRECT STATUS)
# ------------------------------
@app.route('/api/admin/get-all-trials', methods=['POST'])
def get_all_trials():
    data = request.get_json()
    if not data or data.get("admin_key") != ADMIN_KEY:
        return jsonify({"status": "denied"}), 403

    trials_list = []
    now = datetime.utcnow()

    # Check expiry every time - so status is always correct
    for lic_key, lic_data in TRIAL_LICENSES.items():
        status = "NOT ACTIVATED"
        remaining = "-"

        if lic_data["start_time"] and lic_data["expires_at"]:
            if lic_data["expires_at"] > now:
                status = "✅ ACTIVE"
                time_left = lic_data["expires_at"] - now
                remaining = f"{time_left.days}d {time_left.seconds//3600}h {(time_left.seconds//60)%60}m"
            else:
                status = "❌ EXPIRED"
                remaining = "EXPIRED"

        trials_list.append({
            "license_key": lic_key,
            "duration_hours": f"{lic_data['duration_hours']}h",
            "hwid": lic_data["hwid"] if lic_data["hwid"] else "-",
            "activated_at": lic_data["activated_at"].strftime('%Y-%m-%d %H:%M UTC') if lic_data["activated_at"] else "-",
            "expires_at": lic_data["expires_at"].strftime('%Y-%m-%d %H:%M UTC') if lic_data["expires_at"] else "-",
            "status": status,
            "remaining": remaining
        })

    return jsonify({"trials": trials_list}), 200

# ------------------------------
# DELETE TRIAL
# ------------------------------
@app.route('/api/admin/delete-trial', methods=['POST'])
def delete_trial():
    data = request.get_json()
    if not data or data.get("admin_key") != ADMIN_KEY:
        return jsonify({"status": "denied"}), 403

    lic_key = data.get("license_key", "")
    if lic_key in TRIAL_LICENSES:
        # Delete linked user account
        for user, udata in list(TRIAL_USERS.items()):
            if udata["linked_license"] == lic_key:
                del TRIAL_USERS[user]
        # Delete trial license
        del TRIAL_LICENSES[lic_key]
        # Save changes
        save_data()
        return jsonify({"status": "deleted"}), 200

    return jsonify({"status": "not_found"}), 404

# ------------------------------
# ACTIVATE LICENSE (TRIAL + PERMANENT)
# ------------------------------
@app.route('/api/activate', methods=['POST'])
def activate():
    data = request.get_json()
    key = data.get("license_key", "").strip()
    hwid = data.get("hardware_id", "").strip()
    now = datetime.utcnow()

    # Check PERMANENT LICENSES
    if key in LICENSES:
        lic = LICENSES[key]
        if lic["type"] == "unlimited":
            if hwid not in lic["hwid"]:
                lic["hwid"].append(hwid)
                return jsonify({"status": "activated"}), 200
        if lic["type"] == "single":
            if lic["hwid"] == "":
                lic["hwid"] = hwid
                return jsonify({"status": "activated"}), 200
            elif lic["hwid"] == hwid:
                return jsonify({"status": "activated"}), 200
            else:
                return jsonify({"status": "blocked", "msg": "Used on another PC"}), 403

    # Check TRIAL LICENSES
    if key in TRIAL_LICENSES:
        lic = TRIAL_LICENSES[key]
        # Activate if not already active
        if lic["start_time"] is None:
            lic["start_time"] = now
            lic["activated_at"] = now
            lic["expires_at"] = now + timedelta(hours=lic["duration_hours"])
            lic["hwid"] = hwid
            save_data()
            return jsonify({"status": "activated", "msg": f"Trial active! Expires in {lic['duration_hours']}h"}), 200
        else:
            # Check if trial is already expired
            if lic["expires_at"] and now > lic["expires_at"]:
                return jsonify({"status": "expired", "msg": "Trial expired"}), 403
            # Check if same hardware
            if lic["hwid"] == hwid:
                return jsonify({"status": "activated"}), 200
            else:
                return jsonify({"status": "blocked", "msg": "Trial used on another PC"}), 403

    return jsonify({"status": "invalid"}), 403

# ------------------------------
# VERIFY LICENSE VALIDITY
# ------------------------------
@app.route('/api/verify-license', methods=['POST'])
def verify():
    data = request.get_json()
    hwid = data.get("hwid", "")
    key_hash = data.get("hash", "")
    now = datetime.utcnow()

    # Check permanent licenses
    for key, lic in LICENSES.items():
        if hashlib.sha256(key.encode()).hexdigest() == key_hash:
            if lic["type"] == "unlimited" and hwid in lic["hwid"]:
                return jsonify({"ok": True}), 200
            if lic["type"] == "single" and lic["hwid"] == hwid:
                return jsonify({"ok": True}), 200

    # Check trial licenses
    for key, lic in TRIAL_LICENSES.items():
        if hashlib.sha256(key.encode()).hexdigest() == key_hash:
            if lic["hwid"] == hwid and lic["expires_at"] and now < lic["expires_at"]:
                return jsonify({"ok": True}), 200
            if lic["expires_at"] and now > lic["expires_at"]:
                return jsonify({"expired": True}), 403
            return jsonify({"invalid": True}), 403

    return jsonify({"invalid": True}), 403

# ------------------------------
# USER LOGIN VALIDATION
# ------------------------------
@app.route('/api/validate-user', methods=['POST'])
def validate_user():
    username = request.get_json().get("username", "")
    if username in VALID_USERS or username in TRIAL_USERS:
        return jsonify({"ok": True}), 200
    return "", 403

@app.route('/api/check-password', methods=['POST'])
def check_password():
    data = request.get_json()
    username = data.get("username", "")
    password = data.get("password", "")

    # Check permanent users
    if username in VALID_USERS and VALID_USERS[username] == password:
        return jsonify({"ok": True}), 200
    # Check trial users
    if username in TRIAL_USERS and TRIAL_USERS[username]["password"] == password:
        return jsonify({"ok": True}), 200

    return "", 403

# ==================================================
# START SERVER
# ==================================================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=False)
