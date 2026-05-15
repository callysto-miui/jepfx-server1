from flask import Flask, request, jsonify, render_template_string
import hashlib
from datetime import datetime, timedelta
import json
import os

app = Flask(__name__)

# -------------------------- CONFIGURATION --------------------------
DATA_FILE = "server_data.json"
ADMIN_PASSWORD = "ADMINJEPFX"
ADMIN_KEY = "JEPFX-ADMIN-2026"

# -------------------------- DATABASE --------------------------
LICENSES = {
    "JEPFX-2026-SECRET": {"type": "unlimited", "hwid": [], "expires_at": None},
    "JEPFX-2026-001": {"type": "single", "hwid": "", "expires_at": None},
    "JEPFX-2026-002": {"type": "single", "hwid": "", "expires_at": None},
    "JEPFX-2026-003": {"type": "single", "hwid": "", "expires_at": None},
    "JEPFX-2026-004": {"type": "single", "hwid": "", "expires_at": None},
    "JEPFX-2026-005": {"type": "single", "hwid": "", "expires_at": None}
}

VALID_USERS = {
    "JEPFX": "@JEPFX_1875",
    "SEAN": "SEAN_0",
    "N4XCO": "N4XCO_0"
}

CUSTOM_LICENSES = {}
CUSTOM_USERS = {}

# -------------------------- SAVE / LOAD SYSTEM --------------------------
def load_data():
    global CUSTOM_LICENSES, CUSTOM_USERS
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
                CUSTOM_LICENSES = data.get("custom_licenses", {})
                CUSTOM_USERS = data.get("custom_users", {})
            print("✅ DATA LOADED SUCCESSFULLY")
        except Exception as e:
            print(f"⚠️ LOAD ERROR: {e} — CREATING NEW FILE")
            CUSTOM_LICENSES = {}
            CUSTOM_USERS = {}
            save_data()
    else:
        print("ℹ️ NO DATA FILE — CREATING NEW")
        save_data()

def save_data():
    data = {
        "custom_licenses": CUSTOM_LICENSES,
        "custom_users": CUSTOM_USERS
    }
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=2, default=str)
        print("💾 DATA SAVED SUCCESSFULLY")
    except Exception as e:
        print(f"❌ SAVE ERROR: {e}")

# Load data when server starts
load_data()

# -------------------------- ADMIN PANEL HTML --------------------------
ADMIN_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>JEPFX ADMIN PANEL</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * {box-sizing:border-box; font-family:Arial,sans-serif;}
        body {background:#1a103d; color:white; margin:0; padding:20px;}
        .login-box {max-width:400px; margin:50px auto; background:#241854; padding:30px; border-radius:10px; text-align:center;}
        .panel-box {display:none;}
        .panel-box.active {display:block;}
        h1,h2 {color:#7B61FF;}
        input {width:100%; padding:12px; margin:10px 0; border:none; border-radius:5px; background:#3a2b70; color:white; font-size:16px;}
        button {padding:12px 25px; margin:10px 5px; border:none; border-radius:5px; cursor:pointer; font-size:16px; font-weight:bold;}
        .btn-primary {background:#7B61FF; color:white;}
        .btn-danger {background:#ef4444; color:white;}
        .tabs {display:flex; gap:10px; margin-bottom:20px;}
        .tab {padding:12px 25px; background:#241854; border-radius:5px; cursor:pointer;}
        .tab.active {background:#7B61FF;}
        table {width:100%; border-collapse:collapse; margin-top:20px; background:#241854;}
        th,td {padding:12px; text-align:center; border-bottom:1px solid #3a2b70;}
        th {background:#3a2b70;}
        .result {background:#241854; padding:20px; border-radius:5px; margin-top:20px; white-space:pre-line;}
        .note {color:#aaa; font-size:14px; margin:-8px 0 10px 0;}
    </style>
</head>
<body>

<div id="login-screen" class="login-box">
    <h2>ADMIN LOGIN</h2>
    <p>Enter access code to continue</p>
    <input type="password" id="password-input" placeholder="Enter code..." autocomplete="off">
    <button class="btn-primary" onclick="checkLogin()">LOGIN</button>
    <p id="error-msg" style="color:#ef4444; display:none;">Wrong code! Try again.</p>
</div>
<div id="panel" class="panel-box">
    <h1>JEPFX ADMIN PANEL</h1>
    <div class="tabs">
        <div class="tab active" onclick="showTab('create')">CREATE CUSTOM</div>
        <div class="tab" onclick="showTab('list')">VIEW ALL</div>
    </div>

    <div id="create" class="content active">
        <h3>Create Custom Activation</h3>
        <label>Custom Username:</label>
        <input type="text" id="cust_user" placeholder="e.g. USER_001" required>

        <label>Custom Password:</label>
        <input type="text" id="cust_pass" placeholder="e.g. PASS_999" required>

        <label>Custom License Key:</label>
        <input type="text" id="cust_license" placeholder="e.g. MY-LICENSE-777" required>

        <label>Duration (Hours):</label>
        <input type="number" id="cust_hours" placeholder="e.g. 168, 500, 1000..." min="1" value="168" required>
        <p class="note">*You can input ANY number, even higher than 168</p>

        <br>
        <button class="btn-primary" onclick="makeCustom()">CREATE NOW</button>
        <div id="output" class="result" style="display:none;"></div>
    </div>

    <div id="list" class="content">
        <h3>All Created Activations</h3>
        <button class="btn-primary" onclick="loadAll()">REFRESH</button>
        <table id="data-table">
            <tr><th>USERNAME</th><th>LICENSE KEY</th><th>HOURS</th><th>STATUS</th><th>REMAINING TIME</th><th>ACTION</th></tr>
        </table>
    </div>
</div>

<script>
const SERVER_URL = window.location.origin;
const ADMIN_KEY = "{{ admin_key }}";

function checkLogin(){
    const code=document.getElementById('password-input').value;
    fetch(SERVER_URL+'/api/admin/check-pass',{
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({code:code})
    })
    .then(r=>r.json())
    .then(d=>{
        if(d.ok){
            document.getElementById('login-screen').style.display='none';
            document.getElementById('panel').classList.add('active');
        }else{
            document.getElementById('error-msg').style.display='block';
        }
    })
}

function showTab(n){
    document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
    document.querySelectorAll('.content').forEach(c=>c.classList.remove('active'));
    document.querySelector('.tab[onclick=\"showTab(\\''+n+'\\')\"]').classList.add('active');
    document.getElementById(n).classList.add('active');
    if(n==='list') loadAll();
}

async function makeCustom(){
    const u=document.getElementById('cust_user').value.trim();
    const p=document.getElementById('cust_pass').value.trim();
    const l=document.getElementById('cust_license').value.trim();
    const h=parseInt(document.getElementById('cust_hours').value);
    if(!u||!p||!l||!h) return alert('Fill all fields!');

    const r=await fetch(SERVER_URL+'/api/admin/create-custom',{
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({admin_key:ADMIN_KEY,username:u,password:p,license:l,hours:h})
    });
    const d=await r.json();
    document.getElementById('output').style.display='block';
    if(r.ok){
        document.getElementById('output').innerHTML='SUCCESSFULLY CREATED\n--------------------\nUSERNAME : '+u+'\nPASSWORD : '+p+'\nLICENSE  : '+l+'\nDURATION : '+h+' HOURS\n--------------------\nREADY TO USE!';
        loadAll();
    }else{
        document.getElementById('output').innerHTML='ERROR: Username or License already exists!';
    }
}

async function loadAll(){
    const r=await fetch(SERVER_URL+'/api/admin/get-all',{
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({admin_key:ADMIN_KEY})
    });
    const d=await r.json();
    const tbl=document.getElementById('data-table');
    tbl.innerHTML='<tr><th>USERNAME</th><th>LICENSE KEY</th><th>HOURS</th><th>STATUS</th><th>REMAINING TIME</th><th>ACTION</th></tr>';
    d.list.forEach(i=>{
        const row=tbl.insertRow(-1);
        row.innerHTML='<td>'+i.username+'</td><td>'+i.license+'</td><td>'+i.hours+'</td><td>'+i.status+'</td><td>'+i.remaining+'</td><td><button class=\"btn-danger\" onclick=\"deleteItem(\\''+i.license+'\\')\">DELETE</button></td>';
    })
}

async function deleteItem(l){
    if(!confirm('Delete this activation?')) return;
    await fetch(SERVER_URL+'/api/admin/delete',{
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({admin_key:ADMIN_KEY,license:l})
    });
    loadAll();
}
</script>

</body>
</html>
"""

# -------------------------- ADMIN ROUTES --------------------------
@app.route('/api/admin/check-pass', methods=['POST'])
def api_check_pass():
    return jsonify({"ok": request.get_json().get("code") == ADMIN_PASSWORD}), 200

@app.route('/admin')
def admin_page():
    return render_template_string(ADMIN_HTML.replace("{{ admin_key }}", ADMIN_KEY))

@app.route('/')
def home():
    return "SERVER RUNNING | Open /admin to access panel"

@app.route('/api/admin/create-custom', methods=['POST'])
def api_create_custom():
    data = request.get_json()
    if data.get("admin_key") != ADMIN_KEY:
        return jsonify({"error": "unauthorized"}), 403

    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    license_key = data.get("license", "").strip()
    hours = int(data.get("hours", 168))

    if license_key in CUSTOM_LICENSES or license_key in LICENSES:
        return jsonify({"error": "exists"}), 400
    if username in CUSTOM_USERS or username in VALID_USERS:
        return jsonify({"error": "exists"}), 400

    CUSTOM_LICENSES[license_key] = {
        "hwid": "",
        "duration_hours": hours,
        "start_time": None,
        "expires_at": None,
        "activated_at": None
    }
    CUSTOM_USERS[username] = {"password": password, "linked_license": license_key}
    save_data()
    return jsonify({"success": True}), 200
# -------------------------- GET ALL ACTIVATIONS --------------------------
@app.route('/api/admin/get-all', methods=['POST'])
def api_get_all():
    data = request.get_json()
    if data.get("admin_key") != ADMIN_KEY:
        return jsonify({"error": "unauthorized"}), 403

    now = datetime.utcnow()
    result_list = []

    # Permanent licenses
    for key, lic in LICENSES.items():
        result_list.append({
            "username": "PERMANENT",
            "license": key,
            "hours": "UNLIMITED",
            "status": "PERMANENT",
            "remaining": "FOREVER"
        })

    # Custom / trial licenses
    for key, lic in CUSTOM_LICENSES.items():
        linked_user = "UNKNOWN"
        for user, user_data in CUSTOM_USERS.items():
            if user_data["linked_license"] == key:
                linked_user = user

        status = "NOT ACTIVATED"
        remaining = "-"

        if lic["expires_at"]:
            exp_time = datetime.fromisoformat(str(lic["expires_at"]))
            if now > exp_time:
                status = "EXPIRED"
                remaining = "EXPIRED"
            else:
                status = "ACTIVE"
                diff = exp_time - now
                remaining = f"{diff.days}d {diff.seconds//3600}h {(diff.seconds//60)%60}m"

        result_list.append({
            "username": linked_user,
            "license": key,
            "hours": lic["duration_hours"],
            "status": status,
            "remaining": remaining
        })

    return jsonify({"list": result_list}), 200


# -------------------------- DELETE ACTIVATION --------------------------
@app.route('/api/admin/delete', methods=['POST'])
def api_delete():
    data = request.get_json()
    if data.get("admin_key") != ADMIN_KEY:
        return jsonify({"error": "unauthorized"}), 403

    license_key = data.get("license", "").strip()

    if license_key in CUSTOM_LICENSES:
        # Delete linked user
        for user, user_data in list(CUSTOM_USERS.items()):
            if user_data["linked_license"] == license_key:
                del CUSTOM_USERS[user]
        # Delete license
        del CUSTOM_LICENSES[license_key]
        save_data()
        return jsonify({"success": True}), 200

    return jsonify({"error": "not_found"}), 404


# -------------------------- ACTIVATE SYSTEM --------------------------
@app.route('/api/activate', methods=['POST'])
def activate():
    data = request.get_json()
    key = data.get("license_key", "").strip()
    hwid = data.get("hardware_id", "").strip()
    now = datetime.utcnow()

    # Permanent licenses
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

    # Custom / trial licenses
    if key in CUSTOM_LICENSES:
        lic = CUSTOM_LICENSES[key]
        if lic["start_time"] is None:
            lic["start_time"] = now.isoformat()
            lic["activated_at"] = now.isoformat()
            lic["expires_at"] = (now + timedelta(hours=lic["duration_hours"])).isoformat()
            lic["hwid"] = hwid
            save_data()
            return jsonify({
                "status": "activated",
                "msg": f"Activated! Expires in {lic['duration_hours']} hours"
            }), 200
        else:
            exp_time = datetime.fromisoformat(str(lic["expires_at"]))
            if now > exp_time:
                return jsonify({"status": "expired", "msg": "License already expired"}), 403
            if lic["hwid"] == hwid:
                return jsonify({"status": "activated"}), 200
            else:
                return jsonify({"status": "blocked", "msg": "Used on another PC"}), 403

    return jsonify({"status": "invalid", "msg": "License key does not exist"}), 403


# -------------------------- VERIFY LICENSE --------------------------
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

    # Check custom licenses
    for key, lic in CUSTOM_LICENSES.items():
        if hashlib.sha256(key.encode()).hexdigest() == key_hash:
            if not lic.get("expires_at"):
                return jsonify({"invalid": True}), 403
            exp_time = datetime.fromisoformat(str(lic["expires_at"]))
            if lic["hwid"] == hwid and now < exp_time:
                return jsonify({"ok": True}), 200
            if now > exp_time:
                return jsonify({"expired": True}), 403
            return jsonify({"invalid": True}), 403

    return jsonify({"invalid": True}), 403


# -------------------------- VALIDATE USER --------------------------
@app.route('/api/validate-user', methods=['POST'])
def validate_user():
    username = request.get_json().get("username", "")
    if username in VALID_USERS or username in CUSTOM_USERS:
        return jsonify({"ok": True}), 200
    return "", 403


# -------------------------- CHECK PASSWORD --------------------------
@app.route('/api/check-password', methods=['POST'])
def check_pass():
    data = request.get_json()
    username = data.get("username", "")
    password = data.get("password", "")

    if username in VALID_USERS and VALID_USERS[username] == password:
        return jsonify({"ok": True}), 200

    if username in CUSTOM_USERS and CUSTOM_USERS[username]["password"] == password:
        return jsonify({"ok": True}), 200

    return "", 403


# -------------------------- FIXED FOR RENDER --------------------------
# No app.run() here — Render uses gunicorn server:app automatically
