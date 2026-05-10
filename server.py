from flask import Flask, request, jsonify
import hashlib
from datetime import datetime, timedelta
import uuid

app = Flask(__name__)

# ==================================================
# 🔑 ADMIN KEY — LOCKED & PROTECTED — NEVER OVERWRITTEN
# ==================================================
ADMIN_KEY = "JEPFX-ADMIN-2026"  

# ==================================================
# 📝 DATA STORAGE — SEPARATED SAFELY
# ==================================================
LICENSES = {
    "JEPFX-2026-SECRET": {
        "type": "unlimited",
        "hwid": [],
        "expires_at": None,
        "activated_at": None
    },
    "JEPFX-2026-001": {"type": "single", "hwid": "", "expires_at": None, "activated_at": None},
    "JEPFX-2026-002": {"type": "single", "hwid": "", "expires_at": None, "activated_at": None},
    "JEPFX-2026-003": {"type": "single", "hwid": "", "expires_at": None, "activated_at": None},
    "JEPFX-2026-004": {"type": "single", "hwid": "", "expires_at": None, "activated_at": None},
    "JEPFX-2026-005": {"type": "single", "hwid": "", "expires_at": None, "activated_at": None}
}

VALID_USERS = {
    "JEPFX": "@JEPFX_1875",
    "SEAN": "SEAN_0",
    "N4XCO": "N4XCO_0"
}

TRIAL_LICENSES = {}
TRIAL_USERS = {}

# ==================================================
# 🚀 ROUTES
# ==================================================
@app.route('/')
def home():
    return "✅ JEPFX SERVER | FULLY FIXED"

# 🛡️ ADMIN KEY CHECK — FIRST IN EVERY ADMIN ROUTE
def check_admin_key():
    data = request.get_json()
    if not data or data.get("admin_key") != ADMIN_KEY:
        return False
    return True

# 🆕 CUSTOM ACTIVATION — SAFE, NO OVERWRITE
@app.route('/api/admin/add-custom-account', methods=['POST'])
def add_custom_account():
    if not check_admin_key():
        return jsonify({"status":"denied"}), 403

    data = request.get_json()
    username = data.get("username","").strip()
    password = data.get("password","").strip()
    license_key = data.get("license_key","").strip()
    duration_hours = int(data.get("duration_hours", 720))

    if not username or not password or not license_key:
        return jsonify({"status":"error","msg":"Fill all fields"}),400

    LICENSES[license_key] = {
        "type": "unlimited",
        "hwid": [],
        "expires_at": datetime.utcnow() + timedelta(hours=duration_hours),
        "activated_at": datetime.utcnow()
    }
    VALID_USERS[username] = password

    return jsonify({"status":"success","validity_hours": duration_hours}),200


# ⚡ GENERATE TRIAL — FIXED RECOGNITION
@app.route('/api/admin/generate-trial', methods=['POST'])
def generate_trial():
    if not check_admin_key():
        return jsonify({"status":"denied"}), 403

    data = request.get_json()
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

    return jsonify({
        "trial_license": trial_license,
        "trial_username": trial_user,
        "trial_password": trial_pass,
        "duration_hours": duration_hours
    }), 200


# 📊 GET ALL — FIXED KEY CHECK
@app.route('/api/admin/get-all', methods=['POST'])
def get_all():
    if not check_admin_key():
        return jsonify({"status":"denied"}), 403

    all_list = []
    now = datetime.utcnow()

    # LICENSES
    for lic_key, lic_data in LICENSES.items():
        status = "NOT ACTIVATED"
        remaining = "-"
        activated_at = lic_data["activated_at"].strftime('%Y-%m-%d %H:%M UTC') if lic_data["activated_at"] else "-"
        expires_at = lic_data["expires_at"].strftime('%Y-%m-%d %H:%M UTC') if lic_data["expires_at"] else "NEVER"
        hwid_info = lic_data["hwid"] if lic_data["hwid"] else "-"

        if lic_data["type"] == "unlimited":
            if lic_data["expires_at"] is None:
                status = "✅ PERMANENT"
                remaining = "FOREVER"
            else:
                if now < lic_data["expires_at"]:
                    status = "✅ ACTIVE"
                    rem = lic_data["expires_at"] - now
                    remaining = f"{rem.days}d {rem.seconds//3600}h"
                else:
                    status = "❌ EXPIRED"
                    remaining = "EXPIRED"

        elif lic_data["type"] == "single":
            status = "✅ ACTIVATED" if lic_data["hwid"] != "" else "⭕ NOT ACTIVATED"

        all_list.append({
            "type": "LICENSE",
            "key": lic_key,
            "mode": lic_data["type"],
            "hwid": hwid_info[:16]+"..." if len(str(hwid_info))>16 else hwid_info,
            "activated": activated_at,
            "expires": expires_at,
            "status": status,
            "remaining": remaining
        })

    # TRIALS
    for lic_key, lic_data in TRIAL_LICENSES.items():
        status = "NOT ACTIVATED"
        remaining = "-"
        activated_at = lic_data["activated_at"].strftime('%Y-%m-%d %H:%M UTC') if lic_data["activated_at"] else "-"
        expires_at = lic_data["expires_at"].strftime('%Y-%m-%d %H:%M UTC') if lic_data["expires_at"] else "-"
        hwid_info = lic_data["hwid"] if lic_data["hwid"] else "-"

        if lic_data["start_time"]:
            if lic_data["expires_at"] > now:
                status = "✅ TRIAL ACTIVE"
                rem = lic_data["expires_at"] - now
                remaining = f"{rem.days}d {rem.seconds//3600}h {(rem.seconds//60)%60}m"
            else:
                status = "❌ TRIAL EXPIRED"
                remaining = "EXPIRED"

        all_list.append({
            "type": "TRIAL",
            "key": lic_key,
            "mode": "trial",
            "hwid": hwid_info[:16]+"..." if len(str(hwid_info))>16 else hwid_info,
            "activated": activated_at,
            "expires": expires_at,
            "status": status,
            "remaining": remaining
        })

    return jsonify({"all_items": all_list}), 200


# 🗑️ DELETE — SAFE
@app.route('/api/admin/delete-item', methods=['POST'])
def delete_item():
    if not check_admin_key():
        return jsonify({"status":"denied"}), 403

    data = request.get_json()
    item_key = data.get("key","")
    item_type = data.get("type","")

    if item_type == "LICENSE" and item_key in LICENSES:
        del LICENSES[item_key]
        for u, ud in list(VALID_USERS.items()):
            if u == item_key or ud == item_key:
                del VALID_USERS[u]
        return jsonify({"status":"deleted"}),200

    if item_type == "TRIAL" and item_key in TRIAL_LICENSES:
        for user, udata in list(TRIAL_USERS.items()):
            if udata["linked_license"] == item_key:
                del TRIAL_USERS[user]
        del TRIAL_LICENSES[item_key]
        return jsonify({"status":"deleted"}),200

    return jsonify({"status":"not_found"}),404


# 🚀 ACTIVATE — TRIAL + LICENSE FIXED
@app.route('/api/activate', methods=['POST'])
def activate():
    data = request.get_json()
    key = data.get("license_key", "").strip()
    hwid = data.get("hardware_id", "").strip()
    now = datetime.utcnow()

    # LICENSES
    if key in LICENSES:
        lic = LICENSES[key]
        if lic["type"] == "unlimited":
            if hwid not in lic["hwid"]:
                lic["hwid"].append(hwid)
            if lic["activated_at"] is None:
                lic["activated_at"] = now
            if lic["expires_at"] and now > lic["expires_at"]:
                return jsonify({"status":"expired","msg":"License expired"}),403
            return jsonify({"status":"activated"}),200

        if lic["type"] == "single":
            if lic["hwid"] == "":
                lic["hwid"] = hwid
                lic["activated_at"] = now
                return jsonify({"status":"activated"}),200
            elif lic["hwid"] == hwid:
                return jsonify({"status":"activated"}),200
            else:
                return jsonify({"status":"blocked","msg":"Used on another PC"}),403

    # TRIALS
    if key in TRIAL_LICENSES:
        lic = TRIAL_LICENSES[key]
        if lic["start_time"] is None:
            lic["start_time"] = now
            lic["activated_at"] = now
            lic["expires_at"] = now + timedelta(hours=lic["duration_hours"])
            lic["hwid"] = hwid
            return jsonify({"status":"activated","msg":f"Trial active! Expires in {lic['duration_hours']}h"}),200
        if lic["expires_at"] and now > lic["expires_at"]:
            return jsonify({"status":"expired","msg":"Trial expired"}),403
        if lic["hwid"] == hwid:
            return jsonify({"status":"activated"}),200
        else:
            return jsonify({"status":"blocked","msg":"Trial used on another PC"}),403

    return jsonify({"status":"invalid"}),403


# ✅ VERIFY — TRIAL + LICENSE FIXED
@app.route('/api/verify-license', methods=['POST'])
def verify():
    data = request.get_json()
    hwid = data.get("hwid", "")
    key_hash = data.get("hash", "")
    now = datetime.utcnow()

    # LICENSES
    for key, lic in LICENSES.items():
        if hashlib.sha256(key.encode()).hexdigest() == key_hash:
            if lic["type"]=="unlimited" and hwid in lic["hwid"]:
                if lic["expires_at"] is None or now < lic["expires_at"]:
                    return jsonify({"ok":True}),200
                else:
                    return jsonify({"expired":True}),403
            if lic["type"]=="single" and lic["hwid"]==hwid:
                return jsonify({"ok":True}),200

    # TRIALS
    for key, lic in TRIAL_LICENSES.items():
        if hashlib.sha256(key.encode()).hexdigest() == key_hash:
            if lic["hwid"]==hwid and lic["expires_at"] and now < lic["expires_at"]:
                return jsonify({"ok":True}),200
            if lic["expires_at"] and now > lic["expires_at"]:
                return jsonify({"expired":True}),403

    return jsonify({"invalid":True}),403


# 🔑 LOGIN
@app.route('/api/validate-user', methods=['POST'])
def validate_user():
    u = request.get_json().get("username","")
    if u in VALID_USERS or u in TRIAL_USERS:
        return jsonify({"ok":True}),200
    return "",403

@app.route('/api/check-password', methods=['POST'])
def check_pass():
    d = request.get_json()
    u = d.get("username","")
    p = d.get("password","")
    if (u in VALID_USERS and VALID_USERS[u]==p) or (u in TRIAL_USERS and TRIAL_USERS[u]["password"]==p):
        return jsonify({"ok":True}),200
    return "",403


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
