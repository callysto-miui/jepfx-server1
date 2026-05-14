from flask import Flask, request, jsonify
import hashlib
from datetime import datetime, timedelta
import uuid
import json
import os

app = Flask(__name__)

# 📂 THIS FILE SAVES ALL YOUR TRIALS PERMANENTLY — NEVER DELETES
DATA_FILE = "server_data.json"

# ==================================================
# 📝 LICENSES & USERS - EDIT THESE AS NEEDED
# ==================================================
LICENSES = {
    "JEPFX-2026-SECRET": {
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

TRIAL_LICENSES = {}
TRIAL_USERS = {}

# ==================================================
# 💾 SAVE / LOAD DATA — THE MAGIC THAT PREVENTS DELETION
# ==================================================
def load_data():
    global TRIAL_LICENSES, TRIAL_USERS
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
                TRIAL_LICENSES = data.get("trials", {})
                TRIAL_USERS = data.get("users", {})
            print("✅ DATA LOADED SUCCESSFULLY — ALL TRIALS RESTORED")
        except Exception as e:
            print(f"⚠️ LOAD ERROR: {e} | CREATING NEW FILE")
            TRIAL_LICENSES = {}
            TRIAL_USERS = {}
            save_data()
    else:
        print("📄 NO DATA FILE FOUND — CREATING NEW ONE")
        save_data()

def save_data():
    data = {"trials": TRIAL_LICENSES, "users": TRIAL_USERS}
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=2, default=str)
    except Exception as e:
        print(f"❌ SAVE ERROR: {e}")

# ==================================================
# 🔑 ADMIN KEY — SAME AS APP_ADMIN.PY
# ==================================================
ADMIN_KEY = "JEPFX-ADMIN-2026"

# ⚡️ LOAD ALL TRIALS IMMEDIATELY WHEN SERVER WAKES UP
load_data()

# ==================================================
# 🚀 ALL ROUTES SAME AS BEFORE
# ==================================================
@app.route('/')
def home():
    return "✅ JEPFX SERVER | PERMANENT + TRIAL + MONITOR"

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

    save_data()  # 💾 SAVE IMMEDIATELY AFTER CREATING
    return jsonify({
        "trial_license": trial_license,
        "trial_username": trial_user,
        "trial_password": trial_pass,
        "duration_hours": duration_hours
    }), 200

@app.route('/api/admin/get-all-trials', methods=['POST'])
def get_all_trials():
    data = request.get_json()
    if not data or data.get("admin_key") != ADMIN_KEY:
        return jsonify({"status": "denied"}), 403

    trials_list = []
    now = datetime.utcnow()

    for lic_key, lic_data in TRIAL_LICENSES.items():
        status = "NOT ACTIVATED"
        remaining = "-"

        if lic_data["start_time"] and lic_data["expires_at"]:
            # Convert string back to datetime
            exp_time = datetime.fromisoformat(str(lic_data["expires_at"]))
            if exp_time > now:
                status = "✅ ACTIVE"
                rem = exp_time - now
                remaining = f"{rem.days}d {rem.seconds//3600}h {(rem.seconds//60)%60}m"
            else:
                status = "❌ EXPIRED"
                remaining = "EXPIRED"

        trials_list.append({
            "license_key": lic_key,
            "duration_hours": f"{lic_data['duration_hours']}h",
            "hwid": lic_data["hwid"] if lic_data["hwid"] else "-",
            "activated_at": lic_data["activated_at"],
            "expires_at": lic_data["expires_at"],
            "status": status,
            "remaining": remaining
        })

    return jsonify({"trials": trials_list}), 200

@app.route('/api/admin/delete-trial', methods=['POST'])
def delete_trial():
    data = request.get_json()
    if not data or data.get("admin_key") != ADMIN_KEY:
        return jsonify({"status": "denied"}), 403

    lic_key = data.get("license_key", "")
    if lic_key in TRIAL_LICENSES:
        for user, udata in list(TRIAL_USERS.items()):
            if udata["linked_license"] == lic_key:
                del TRIAL_USERS[user]
        del TRIAL_LICENSES[lic_key]
        save_data()  # 💾 SAVE AFTER DELETE
        return jsonify({"status": "deleted"}), 200
    return jsonify({"status": "not_found"}), 404

@app.route('/api/activate', methods=['POST'])
def activate():
    data = request.get_json()
    key = data.get("license_key", "").strip()
    hwid = data.get("hardware_id", "").strip()
    now = datetime.utcnow()

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
                return jsonify({"status": "blocked","msg":"Used on another PC"}), 403

    if key in TRIAL_LICENSES:
        lic = TRIAL_LICENSES[key]
        if lic["start_time"] is None:
            lic["start_time"] = now.isoformat()
            lic["activated_at"] = now.isoformat()
            lic["expires_at"] = (now + timedelta(hours=lic["duration_hours"])).isoformat()
            lic["hwid"] = hwid
            save_data()  # 💾 SAVE AFTER ACTIVATION
            return jsonify({"status":"activated","msg":f"Trial active! Expires in {lic['duration_hours']}h"}), 200
        else:
            exp_time = datetime.fromisoformat(str(lic["expires_at"]))
            if now > exp_time:
                return jsonify({"status":"expired","msg":"Trial expired"}), 403
            if lic["hwid"] == hwid:
                return jsonify({"status":"activated"}), 200
            else:
                return jsonify({"status":"blocked","msg":"Trial used on another PC"}), 403

    return jsonify({"status":"invalid"}), 403

@app.route('/api/verify-license', methods=['POST'])
def verify():
    data = request.get_json()
    hwid = data.get("hwid", "")
    key_hash = data.get("hash", "")
    now = datetime.utcnow()

    for key, lic in LICENSES.items():
        if hashlib.sha256(key.encode()).hexdigest() == key_hash:
            if lic["type"]=="unlimited" and hwid in lic["hwid"]:
                return jsonify({"ok":True}), 200
            if lic["type"]=="single" and lic["hwid"]==hwid:
                return jsonify({"ok":True}), 200

    for key, lic in TRIAL_LICENSES.items():
        if hashlib.sha256(key.encode()).hexdigest() == key_hash:
            exp_time = datetime.fromisoformat(str(lic["expires_at"]))
            if lic["hwid"]==hwid and now < exp_time:
                return jsonify({"ok":True}), 200
            if now > exp_time:
                return jsonify({"expired":True}), 403
            return jsonify({"invalid":True}), 403

    return jsonify({"invalid":True}), 403

@app.route('/api/validate-user', methods=['POST'])
def validate_user():
    u = request.get_json().get("username","")
    if u in VALID_USERS or u in TRIAL_USERS:
        return jsonify({"ok":True}), 200
    return "", 403

@app.route('/api/check-password', methods=['POST'])
def check_pass():
    d = request.get_json()
    u = d.get("username","")
    p = d.get("password","")
    if (u in VALID_USERS and VALID_USERS[u]==p) or (u in TRIAL_USERS and TRIAL_USERS[u]["password"]==p):
        return jsonify({"ok":True}), 200
    return "", 403

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
    
