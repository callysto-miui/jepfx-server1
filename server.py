from flask import Flask, request, jsonify
import hashlib
from datetime import datetime, timedelta
import uuid

app = Flask(__name__)

# ==================================================
# 🔑 ADMIN KEY — LOCKED FOREVER | CANNOT BE CHANGED/DELETED
# ==================================================
ADMIN_KEY = "JEPFX-ADMIN-2026"
ADMIN_KEY_HASH = hashlib.sha256(ADMIN_KEY.encode()).hexdigest()  # Permanent hash

# ==================================================
# 📝 DATABASE — CLEAN, NO DEFAULTS
# ==================================================
LICENSES = {}
VALID_USERS = {}
TRIAL_LICENSES = {}
TRIAL_USERS = {}

# ==================================================
# 🛡️ SAFE ADMIN CHECK — CANNOT FAIL
# ==================================================
def is_admin():
    try:
        data = request.get_json(force=True, silent=True)
        if not data or "admin_key" not in data:
            return False
        # Compare HASH — NEVER compare raw string, NEVER store key in DB
        received_hash = hashlib.sha256(str(data.get("admin_key","")).strip().encode()).hexdigest()
        return received_hash == ADMIN_KEY_HASH
    except:
        return False

# ==================================================
# 🚀 ROUTES — FULLY PROTECTED
# ==================================================
@app.route('/')
def home():
    return "✅ JEPFX SERVER | FULLY LOCKED"

# ⚡ GENERATE TRIAL — ✅ FIXED LINE 51 ERROR HERE
@app.route('/api/admin/generate-trial', methods=['POST'])
def generate_trial():
    if not is_admin():
        return jsonify({"status":"denied"}), 403
    data = request.get_json()
    duration_hours = int(data.get("duration_hours", 3))
    trial_license = f"JEPFX-TRIAL-{uuid.uuid4().hex[:8].upper()}"
    trial_user = f"TRIAL-{uuid.uuid4().hex[:6].upper()}"  # ✅ FIXED SYNTAX ERROR
    trial_pass = uuid.uuid4().hex[:10].upper()
    TRIAL_LICENSES[trial_license] = {
        "type": "trial", "hwid": "", "duration_hours": duration_hours,
        "start_time": None, "expires_at": None, "activated_at": None
    }
    TRIAL_USERS[trial_user] = {"password": trial_pass, "linked_license": trial_license}
    return jsonify({
        "trial_license": trial_license,
        "trial_username": trial_user,
        "trial_password": trial_pass,
        "duration_hours": duration_hours
    }), 200

# 🆕 CUSTOM ACTIVATION — BLOCK ADMIN KEY AS LICENSE
@app.route('/api/admin/add-custom-account', methods=['POST'])
def add_custom_account():
    if not is_admin():
        return jsonify({"status":"denied"}), 403
    data = request.get_json()
    username = str(data.get("username","")).strip()
    password = str(data.get("password","")).strip()
    license_key = str(data.get("license_key","")).strip()
    duration_hours = int(data.get("duration_hours", 720))
    if not username or not password or not license_key:
        return jsonify({"status":"error","msg":"Fill all fields"}),400
    # ❌ CRITICAL: BLOCK USING ADMIN KEY AS LICENSE
    if license_key == ADMIN_KEY or hashlib.sha256(license_key.encode()).hexdigest() == ADMIN_KEY_HASH:
        return jsonify({"status":"error","msg":"❌ Cannot use Admin Key as License"}),400
    # ✅ ADD SAFELY — NEVER TOUCH ADMIN KEY
    LICENSES[license_key] = {
        "type": "unlimited", "hwid": [],
        "expires_at": datetime.utcnow() + timedelta(hours=duration_hours),
        "activated_at": datetime.utcnow()
    }
    VALID_USERS[username] = password
    return jsonify({"status":"success"}),200

# 📊 GET ALL / REFRESH — 100% SAFE
@app.route('/api/admin/get-all', methods=['POST'])
def get_all():
    if not is_admin():
        return jsonify({"status":"denied"}), 403
    all_list = []
    now = datetime.utcnow()
    # LICENSES
    for lic_key, lic_data in LICENSES.items():
        status = "✅ ACTIVE" if now < lic_data["expires_at"] else "❌ EXPIRED"
        rem = lic_data["expires_at"] - now if now < lic_data["expires_at"] else None
        remaining = f"{rem.days}d {rem.seconds//3600}h" if rem else "EXPIRED"
        all_list.append({
            "type": "LICENSE", "key": lic_key, "mode": "unlimited",
            "hwid": lic_data["hwid"][:16]+"..." if lic_data["hwid"] else "-",
            "activated": lic_data["activated_at"].strftime('%Y-%m-%d %H:%M') if lic_data["activated_at"] else "-",
            "expires": lic_data["expires_at"].strftime('%Y-%m-%d %H:%M') if lic_data["expires_at"] else "-",
            "status": status, "remaining": remaining
        })
    # TRIALS
    for lic_key, lic_data in TRIAL_LICENSES.items():
        if not lic_data["start_time"]:
            status = "⭕ NOT ACTIVATED"
            remaining = "-"
        elif lic_data["expires_at"] > now:
            status = "✅ TRIAL ACTIVE"
            rem = lic_data["expires_at"] - now
            remaining = f"{rem.days}d {rem.seconds//3600}h"
        else:
            status = "❌ EXPIRED"
            remaining = "EXPIRED"
        all_list.append({
            "type": "TRIAL", "key": lic_key, "mode": "trial",
            "hwid": lic_data["hwid"][:16]+"..." if lic_data["hwid"] else "-",
            "activated": lic_data["activated_at"].strftime('%Y-%m-%d %H:%M') if lic_data["activated_at"] else "-",
            "expires": lic_data["expires_at"].strftime('%Y-%m-%d %H:%M') if lic_data["expires_at"] else "-",
            "status": status, "remaining": remaining
        })
    return jsonify({"all_items": all_list}), 200

# 🗑️ DELETE — CANNOT DELETE ADMIN KEY
@app.route('/api/admin/delete-item', methods=['POST'])
def delete_item():
    if not is_admin():
        return jsonify({"status":"denied"}), 403
    data = request.get_json()
    item_key = str(data.get("key","")).strip()
    item_type = str(data.get("type","")).strip()
    if item_key == ADMIN_KEY or hashlib.sha256(item_key.encode()).hexdigest() == ADMIN_KEY_HASH:
        return jsonify({"status":"error","msg":"❌ Cannot delete Admin Key"}),400
    if item_type == "LICENSE" and item_key in LICENSES:
        del LICENSES[item_key]
        return jsonify({"status":"deleted"}),200
    if item_type == "TRIAL" and item_key in TRIAL_LICENSES:
        del TRIAL_LICENSES[item_key]
        return jsonify({"status":"deleted"}),200
    return jsonify({"status":"not_found"}),404

# 🚀 ACTIVATE — SAFE, NO OVERWRITE
@app.route('/api/activate', methods=['POST'])
def activate():
    data = request.get_json()
    key = str(data.get("license_key","")).strip()
    hwid = str(data.get("hardware_id","")).strip()
    now = datetime.utcnow()
    if key == ADMIN_KEY or hashlib.sha256(key.encode()).hexdigest() == ADMIN_KEY_HASH:
        return jsonify({"status":"invalid","msg":"❌ Use License Key, NOT Admin Key"}),403
    if key in LICENSES:
        lic = LICENSES[key]
        if hwid not in lic["hwid"]:
            lic["hwid"].append(hwid)
        return jsonify({"status":"activated"}),200
    if key in TRIAL_LICENSES:
        lic = TRIAL_LICENSES[key]
        if not lic["start_time"]:
            lic["start_time"] = now
            lic["activated_at"] = now
            lic["expires_at"] = now + timedelta(hours=lic["duration_hours"])
            lic["hwid"] = hwid
            return jsonify({"status":"activated"}),200
        if lic["hwid"] == hwid:
            return jsonify({"status":"activated"}),200
        return jsonify({"status":"blocked","msg":"❌ Trial used on another PC"}),403
    return jsonify({"status":"invalid"}),403

# ✅ VERIFY / LOGIN — SAFE
@app.route('/api/verify-license', methods=['POST'])
def verify():
    data = request.get_json()
    hwid = str(data.get("hwid","")).strip()
    key_hash = str(data.get("hash","")).strip()
    now = datetime.utcnow()
    for k, lic in LICENSES.items():
        if hashlib.sha256(k.encode()).hexdigest() == key_hash and hwid in lic["hwid"] and lic["expires_at"] > now:
            return jsonify({"ok":True}),200
    for k, lic in TRIAL_LICENSES.items():
        if hashlib.sha256(k.encode()).hexdigest() == key_hash and lic["hwid"] == hwid and lic["expires_at"] > now:
            return jsonify({"ok":True}),200
    return jsonify({"invalid":True}),403

@app.route('/api/validate-user', methods=['POST'])
def validate_user():
    u = str(request.get_json().get("username","")).strip()
    return jsonify({"ok":True}) if u in VALID_USERS or u in TRIAL_USERS else ("",403)

@app.route('/api/check-password', methods=['POST'])
def check_pass():
    d = request.get_json()
    u = str(d.get("username","")).strip()
    p = str(d.get("password","")).strip()
    return jsonify({"ok":True}) if (u in VALID_USERS and VALID_USERS[u]==p) or (u in TRIAL_USERS and TRIAL_USERS[u]["password"]==p) else ("",403)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
