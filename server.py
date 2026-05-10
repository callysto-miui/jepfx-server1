from flask import Flask, request, jsonify
import hashlib
from datetime import datetime, timedelta
import uuid

app = Flask(__name__)

# 🔑 EXACT KEY — BOTH SIDES MUST BE SAME
ADMIN_KEY = "JEPFX-ADMIN-2026"

# 📝 DATABASE
LICENSES = {}
VALID_USERS = {}
TRIAL_LICENSES = {}
TRIAL_USERS = {}

# 🛡️ ADMIN CHECK — SIMPLE, NO HASH, NO TRICKS, 100% RELIABLE
def is_admin():
    try:
        data = request.get_json(force=True, silent=True)
        if not data:
            return False
        received = str(data.get("admin_key", "")).strip()
        return received == ADMIN_KEY
    except:
        return False

# 🚀 ROUTES
@app.route('/')
def home():
    return "✅ SERVER RUNNING"

# ⚡ GENERATE TRIAL
@app.route('/api/admin/generate-trial', methods=['POST'])
def generate_trial():
    if not is_admin():
        return jsonify({"status":"denied"}), 403
    data = request.get_json()
    dur = int(data.get("duration_hours", 3))
    trial_lic = f"JEPFX-TRIAL-{uuid.uuid4().hex[:8].upper()}"
    trial_user = f"TRIAL-{uuid.uuid4().hex[:6].upper()}"
    trial_pass = uuid.uuid4().hex[:10].upper()
    TRIAL_LICENSES[trial_lic] = {
        "type":"trial", "hwid":"", "duration_hours":dur,
        "start_time":None, "expires_at":None, "activated_at":None
    }
    TRIAL_USERS[trial_user] = {"password":trial_pass, "linked_license":trial_lic}
    return jsonify({"trial_license":trial_lic, "trial_username":trial_user, "trial_password":trial_pass, "duration_hours":dur}), 200

# ➕ CUSTOM ACTIVATION
@app.route('/api/admin/add-custom-account', methods=['POST'])
def add_custom():
    if not is_admin():
        return jsonify({"status":"denied"}), 403
    data = request.get_json()
    user = str(data.get("username","")).strip()
    pwd = str(data.get("password","")).strip()
    lic = str(data.get("license_key","")).strip()
    dur = int(data.get("duration_hours", 720))
    if not user or not pwd or not lic:
        return jsonify({"status":"error"}),400
    if lic == ADMIN_KEY:
        return jsonify({"status":"error"}),400
    LICENSES[lic] = {
        "type":"unlimited", "hwid":[],
        "expires_at":datetime.utcnow() + timedelta(hours=dur),
        "activated_at":datetime.utcnow()
    }
    VALID_USERS[user] = pwd
    return jsonify({"status":"success"}),200

# 📊 GET ALL / REFRESH — ✅ FIXED FOREVER
@app.route('/api/admin/get-all', methods=['POST'])
def get_all():
    print("🔍 REFRESH REQUEST RECEIVED") # DEBUG LOG
    if not is_admin():
        print("❌ ADMIN KEY WRONG") # DEBUG LOG
        return jsonify({"status":"denied"}), 403
    print("✅ ADMIN KEY CORRECT — SENDING DATA") # DEBUG LOG
    all_list = []
    now = datetime.utcnow()
    # LICENSES
    for k, v in LICENSES.items():
        active = "✅ ACTIVE" if v["expires_at"] > now else "❌ EXPIRED"
        rem = v["expires_at"] - now if v["expires_at"] > now else None
        rem_str = f"{rem.days}d {rem.seconds//3600}h" if rem else "EXPIRED"
        all_list.append({
            "type":"LICENSE", "key":k, "mode":"unlimited",
            "hwid":v["hwid"][:16]+"..." if v["hwid"] else "-",
            "activated":v["activated_at"].strftime('%Y-%m-%d %H:%M'),
            "expires":v["expires_at"].strftime('%Y-%m-%d %H:%M'),
            "status":active, "remaining":rem_str
        })
    # TRIALS
    for k, v in TRIAL_LICENSES.items():
        if not v["start_time"]:
            st = "⭕ NOT ACTIVATED"; rem_str = "-"
        elif v["expires_at"] > now:
            st = "✅ TRIAL ACTIVE"; rem = v["expires_at"] - now; rem_str = f"{rem.days}d {rem.seconds//3600}h"
        else:
            st = "❌ EXPIRED"; rem_str = "EXPIRED"
        all_list.append({
            "type":"TRIAL", "key":k, "mode":"trial",
            "hwid":v["hwid"][:16]+"..." if v["hwid"] else "-",
            "activated":v["activated_at"].strftime('%Y-%m-%d %H:%M') if v["activated_at"] else "-",
            "expires":v["expires_at"].strftime('%Y-%m-%d %H:%M') if v["expires_at"] else "-",
            "status":st, "remaining":rem_str
        })
    return jsonify({"all_items":all_list}), 200

# 🗑️ DELETE
@app.route('/api/admin/delete-item', methods=['POST'])
def delete_item():
    if not is_admin():
        return jsonify({"status":"denied"}), 403
    data = request.get_json()
    key = str(data.get("key","")).strip()
    typ = str(data.get("type","")).strip()
    if key == ADMIN_KEY:
        return jsonify({"status":"error"}),400
    if typ == "LICENSE" and key in LICENSES: del LICENSES[key]; return jsonify({"status":"ok"}),200
    if typ == "TRIAL" and key in TRIAL_LICENSES: del TRIAL_LICENSES[key]; return jsonify({"status":"ok"}),200
    return jsonify({"status":"notfound"}),404

# 🔓 ACTIVATE
@app.route('/api/activate', methods=['POST'])
def activate():
    data = request.get_json()
    key = str(data.get("license_key","")).strip()
    hwid = str(data.get("hardware_id","")).strip()
    now = datetime.utcnow()
    if key == ADMIN_KEY: return jsonify({"status":"invalid"}),403
    if key in LICENSES:
        lic = LICENSES[key]
        if hwid not in lic["hwid"]: lic["hwid"].append(hwid)
        return jsonify({"status":"ok"}),200
    if key in TRIAL_LICENSES:
        lic = TRIAL_LICENSES[key]
        if not lic["start_time"]:
            lic["start_time"]=now; lic["activated_at"]=now; lic["expires_at"]=now+timedelta(hours=lic["duration_hours"]); lic["hwid"]=hwid
            return jsonify({"status":"ok"}),200
        if lic["hwid"]==hwid: return jsonify({"status":"ok"}),200
        return jsonify({"status":"blocked"}),403
    return jsonify({"status":"invalid"}),403

# ✅ VERIFY / LOGIN
@app.route('/api/verify-license', methods=['POST'])
def verify():
    data = request.get_json()
    hwid = str(data.get("hwid","")).strip()
    key_hash = str(data.get("hash","")).strip()
    now = datetime.utcnow()
    for k,v in LICENSES.items():
        if hashlib.sha256(k.encode()).hexdigest()==key_hash and hwid in v["hwid"] and v["expires_at"]>now: return jsonify({"ok":True}),200
    for k,v in TRIAL_LICENSES.items():
        if hashlib.sha256(k.encode()).hexdigest()==key_hash and v["hwid"]==hwid and v["expires_at"]>now: return jsonify({"ok":True}),200
    return jsonify({"invalid":True}),403

@app.route('/api/validate-user', methods=['POST'])
def val_user():
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
