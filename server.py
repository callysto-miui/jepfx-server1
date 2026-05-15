from flask import Flask, request, jsonify, render_template_string
from datetime import datetime, timedelta
import uuid
import json
import os

app = Flask(__name__)

# ==================================================
# 📂 FILE PATH — EXACT LOCATION
# ==================================================
DATA_FILE = "server_data.json"

# ==================================================
# 🔐 ADMIN DETAILS
# ==================================================
ADMIN_PASSWORD = "JEPFXADMIN"
ADMIN_KEY = "JEPFX-ADMIN-2026"

# ==================================================
# 🔑 PERMANENT LICENSES & USERS
# ==================================================
LICENSES = {
"JEPFX-2026-SECRET": {"type": "unlimited", "hwid": "", "expires_at": None},
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

# ==================================================
# 💾 DATA VARIABLES
# ==================================================
TRIAL_LICENSES = {}
TRIAL_USERS = {}

# ==================================================
# 📥 LOAD DATA — FIXED 100%
# ==================================================
def load_data():
    global TRIAL_LICENSES, TRIAL_USERS
    # Start empty
    TRIAL_LICENSES = {}
    TRIAL_USERS = {}
    
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Load ONLY if correct format
            if isinstance(data.get("trials"), dict):
                TRIAL_LICENSES = data["trials"]
            if isinstance(data.get("users"), dict):
                TRIAL_USERS = data["users"]
                
            print("✅ DATA LOADED SUCCESSFULLY")
            print(f"📋 Loaded Users: {list(TRIAL_USERS.keys())}") # DEBUG: Shows users loaded
        except Exception as e:
            print(f"❌ LOAD ERROR: {e} — Resetting file")
            save_data()
    else:
        print("📄 File missing — Creating new")
        save_data()

# ==================================================
# 📤 SAVE DATA — FIXED 100%
# ==================================================
def save_data():
    data_to_save = {
        "trials": TRIAL_LICENSES,
        "users": TRIAL_USERS
    }
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data_to_save, f, indent=2, default=str)
        print("💾 DATA SAVED SUCCESSFULLY")
    except Exception as e:
        print(f"❌ SAVE ERROR: {e}")

# ==================================================
# 🎨 ADMIN PANEL
# ==================================================
ADMIN_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>JEPFX ADMIN PANEL</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { box-sizing: border-box; font-family: Arial, sans-serif; }
        body { background: #1a103d; color: white; margin: 0; padding: 20px; }
        .login-box { max-width: 400px; margin: 50px auto; background: #241854; padding: 30px; border-radius: 10px; text-align: center; }
        .panel-box { display: none; }
        .panel-box.active { display: block; }
        h1, h2 { color: #7B61FF; }
        input, select { width: 100%; padding: 12px; margin: 10px 0; border: none; border-radius: 5px; background: #3a2b70; color: white; font-size: 16px; }
        button { padding: 12px 25px; margin: 10px 5px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; font-weight: bold; }
        .btn-primary { background: #7B61FF; color: white; }
        .btn-danger { background: #ef4444; color: white; }
        .tabs { display: flex; gap: 10px; margin-bottom: 20px; }
        .tab { padding: 12px 25px; background: #241854; border-radius: 5px; cursor: pointer; }
        .tab.active { background: #7B61FF; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; background: #241854; }
        th, td { padding: 12px; text-align: center; border-bottom: 1px solid #3a2b70; }
        th { background: #3a2b70; }
        .result { background: #241854; padding: 20px; border-radius: 5px; margin-top: 20px; white-space: pre-line; }
        .section { border: 1px solid #7B61FF; padding: 15px; border-radius: 8px; margin: 15px 0; }
    </style>
</head>
<body>
    <div id="login-screen" class="login-box">
        <h2>🔒 ADMIN LOGIN</h2>
        <p>Enter access code to continue</p>
        <input type="password" id="password-input" placeholder="Enter code..." autocomplete="off">
        <button class="btn-primary" onclick="checkLogin()">LOGIN</button>
        <p id="error-msg" style="color: #ef4444; display: none;">Wrong code! Try again.</p>
    </div>

    <div id="panel" class="panel-box">
        <h1>⚡ JEPFX ADMIN PANEL</h1>
        <div class="tabs">
            <div class="tab active" onclick="showTab('generate')">GENERATE LICENSES</div>
            <div class="tab" onclick="showTab('trials')">VIEW ALL</div>
        </div>

        <div id="generate" class="content active">
            <div class="section">
                <h3>🔄 AUTO GENERATE TRIAL LICENSE</h3>
                <label>Duration (Hours):</label>
                <input type="number" id="auto-duration" min="1" value="3" placeholder="Enter hours">
                <br>
                <button class="btn-primary" onclick="generateAutoTrial()">GENERATE (1 PC ONLY)</button>
                <div id="auto-result" class="result" style="display: none;"></div>
            </div>

            <div class="section">
                <h3>✏️ CUSTOM LICENSE (WORKS ON ANY PC)</h3>
                <label>Custom Username:</label>
                <input type="text" id="custom-user" placeholder="Leave blank for auto">
                <label>Custom Password:</label>
                <input type="text" id="custom-pass" placeholder="Leave blank for auto">
                <label>Custom License Key:</label>
                <input type="text" id="custom-key" placeholder="Leave blank for auto">
                <label>Duration (Hours):</label>
                <input type="number" id="custom-duration" min="1" value="3" placeholder="Enter hours">
                <br>
                <button class="btn-primary" onclick="generateCustomLicense()">GENERATE (UNLIMITED PC)</button>
                <div id="custom-result" class="result" style="display: none;"></div>
            </div>
        </div>
        <div id="trials" class="content">
            <h3>All Licenses & Trials</h3>
            <button class="btn-primary" onclick="loadTrials()">REFRESH LIST</button>
            <table id="trials-table">
                <tr><th>TYPE</th><th>LICENSE KEY</th><th>USERNAME</th><th>PASSWORD</th><th>DURATION</th><th>STATUS</th><th>REMAINING</th><th>ACTION</th></tr>
            </table>
        </div>
    </div>

    <script>
        const SERVER_URL = window.location.origin;
        const ADMIN_KEY = "{{ admin_key }}";

        function checkLogin() {
            const inputCode = document.getElementById('password-input').value;
            fetch(SERVER_URL + '/api/admin/check-password', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({code: inputCode})
            })
            .then(res => res.json())
            .then(data => {
                if(data.success) {
                    document.getElementById('login-screen').style.display = 'none';
                    document.getElementById('panel').classList.add('active');
                } else {
                    document.getElementById('error-msg').style.display = 'block';
                }
            });
        }

        function showTab(tabName) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.content').forEach(c => c.classList.remove('active'));
            document.querySelector(`.tab[onclick="showTab('${tabName}')"]`).classList.add('active');
            document.getElementById(tabName).classList.add('active');
            if(tabName === 'trials') loadTrials();
        }

        // ✅ AUTO GENERATE (1 PC ONLY, TIME STARTS ON ACTIVATION)
        async function generateAutoTrial() {
            const duration = document.getElementById('auto-duration').value;
            const res = await fetch(SERVER_URL + '/api/admin/generate-auto-trial', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({admin_key: ADMIN_KEY, duration_hours: parseInt(duration)})
            });
            const data = await res.json();
            document.getElementById('auto-result').style.display = 'block';
            if(res.ok) {
                document.getElementById('auto-result').innerHTML = `
✅ AUTO TRIAL CREATED
━━━━━━━━━━━━━━━━━━
🔑 LICENSE: ${data.license}
👤 USER: ${data.username}
🔒 PASS: ${data.password}
⏱️ TIME: ${duration} HOURS
🔒 LOCKS TO 1ST PC ONLY
⏳ TIME STARTS WHEN ACTIVATED
━━━━━━━━━━━━━━━━━━
                `;
                loadTrials();
            }
        }

        // ✅ CUSTOM LICENSE (ANY PC / NO LOCK)
        async function generateCustomLicense() {
            const duration = document.getElementById('custom-duration').value;
            const user = document.getElementById('custom-user').value;
            const pass = document.getElementById('custom-pass').value;
            const key = document.getElementById('custom-key').value;

            const res = await fetch(SERVER_URL + '/api/admin/generate-custom-license', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    admin_key: ADMIN_KEY,
                    duration_hours: parseInt(duration),
                    custom_username: user,
                    custom_password: pass,
                    custom_license: key
                })
            });
            const data = await res.json();
            document.getElementById('custom-result').style.display = 'block';
            if(res.ok) {
                document.getElementById('custom-result').innerHTML = `
✅ CUSTOM LICENSE CREATED
━━━━━━━━━━━━━━━━━━
🔑 LICENSE: ${data.license}
👤 USER: ${data.username}
🔒 PASS: ${data.password}
⏱️ TIME: ${duration} HOURS
♾️ WORKS ON ANY PC
━━━━━━━━━━━━━━━━━━
                `;
                loadTrials();
            }
        }

        async function loadTrials() {
            const res = await fetch(SERVER_URL + '/api/admin/get-all-trials', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({admin_key: ADMIN_KEY})
            });
            const data = await res.json();
            const table = document.getElementById('trials-table');
            table.innerHTML = `<tr><th>TYPE</th><th>LICENSE KEY</th><th>USERNAME</th><th>PASSWORD</th><th>DURATION</th><th>STATUS</th><th>REMAINING</th><th>ACTION</th></tr>`;
            
            data.trials.forEach(trial => {
                const row = table.insertRow(-1);
                row.innerHTML = `
                    <td>${trial.type}</td>
                    <td>${trial.license_key}</td>
                    <td>${trial.username}</td>
                    <td>${trial.password}</td>
                    <td>${trial.duration_hours}</td>
                    <td>${trial.status}</td>
                    <td>${trial.remaining}</td>
                    <td><button class="btn-danger" onclick="deleteTrial('${trial.license_key}')">DELETE</button></td>
                `;
            });
        }

        async function deleteTrial(key) {
            if(!confirm('Delete this license?')) return;
            await fetch(SERVER_URL + '/api/admin/delete-trial', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({admin_key: ADMIN_KEY, license_key: key})
            });
            loadTrials();
        }
    </script>
</body></html>
"""

# ==================================================
# 🔐 APIs — CORE LOGIC FIXED
# ==================================================
@app.route('/api/admin/check-password', methods=['POST'])
def check_password():
    return jsonify({"success": request.get_json().get("code") == ADMIN_PASSWORD}), 200

@app.route('/admin')
def admin_page():
    return render_template_string(ADMIN_HTML.replace("{{ admin_key }}", ADMIN_KEY))

@app.route('/')
def home():
    return "✅ SERVER RUNNING | /admin"

# ✅ API 1: AUTO GENERATE TRIAL — 1 PC ONLY / TIME STARTS ON ACTIVATION
@app.route('/api/admin/generate-auto-trial', methods=['POST'])
def generate_auto_trial():
    data = request.get_json()
    if data.get("admin_key") != ADMIN_KEY: return jsonify({"status":"denied"}),403
    
    dur = int(data.get("duration_hours",3))
    lic = f"JEPFX-TRIAL-{uuid.uuid4().hex[:8].upper()}"
    user = f"TRIAL-{uuid.uuid4().hex[:6].upper()}"
    pwd = uuid.uuid4().hex[:10].upper()

    TRIAL_LICENSES[lic] = {
    "type":"trial_locked",
    "hwid":"",
    "duration_hours":dur,
    "expires_at": None,
    "activated_at": None
    }
    TRIAL_USERS[user] = {"password":pwd,"linked_license":lic}
    save_data()
    return jsonify({"license":lic,"username":user,"password":pwd}),200

# ✅ API 2: CUSTOM LICENSE — ANY PC / NO LOCK / TIME STARTS NOW
@app.route('/api/admin/generate-custom-license', methods=['POST'])
def generate_custom_license():
    data = request.get_json()
    if data.get("admin_key") != ADMIN_KEY: return jsonify({"status":"denied"}),403
    
    dur = int(data.get("duration_hours",3))
    user = data.get("custom_username","").strip() or f"CUSTOM-{uuid.uuid4().hex[:6].upper()}"
    pwd = data.get("custom_password","").strip() or uuid.uuid4().hex[:10].upper()
    lic = data.get("custom_license","").strip() or f"JEPFX-CUSTOM-{uuid.uuid4().hex[:8].upper()}"

    TRIAL_LICENSES[lic] = {
    "type":"custom_unlocked",
    "hwid": None,
    "duration_hours":dur,
    "expires_at": (datetime.utcnow() + timedelta(hours=dur)).isoformat(),
    "activated_at": datetime.utcnow().isoformat()
    }
    TRIAL_USERS[user] = {"password":pwd,"linked_license":lic}
    save_data()
    return jsonify({"license":lic,"username":user,"password":pwd}),200

@app.route('/api/admin/get-all-trials', methods=['POST'])
def get_all():
    if request.get_json().get("admin_key") != ADMIN_KEY: return jsonify({"status":"denied"}),403
    now = datetime.utcnow()
    list_trials = []
    user_map = {u_data['linked_license']: (u, u_data['password']) for u, u_data in TRIAL_USERS.items()}

    for k,v in TRIAL_LICENSES.items():
        status = "✅ ACTIVE"
        rem = "-"
        uname, upass = "-", "-"
        typ = "❓ UNKNOWN"
        if k in user_map:
            uname, upass = user_map[k]

        if v["type"] == "trial_locked":
            typ = "🔒 AUTO (1 PC)"
            if v["expires_at"] is None:
                status = "⌛ WAITING ACTIVATION"
                rem = "TIME NOT RUNNING"
            else:
                exp = datetime.fromisoformat(v["expires_at"])
                if exp > now:
                    diff = exp - now
                    rem = f"{diff.days}d {diff.seconds//3600}h {(diff.seconds//60)%60}m"
                else:
                    status = "❌ EXPIRED"
                    rem = "EXPIRED"

        elif v["type"] == "custom_unlocked":
            typ = "♾️ CUSTOM (ANY PC)"
            if v["expires_at"]:
                exp = datetime.fromisoformat(v["expires_at"])
                if exp > now:
                    diff = exp - now
                    rem = f"{diff.days}d {diff.seconds//3600}h {(diff.seconds//60)%60}m"
                else:
                    status = "❌ EXPIRED"
                    rem = "EXPIRED"

        list_trials.append({
        "type":typ,"license_key":k,"username":uname,"password":upass,
        "duration_hours":f"{v['duration_hours']}h","status":status,"remaining":rem
        })
    return jsonify({"trials":list_trials}),200

@app.route('/api/admin/delete-trial', methods=['POST'])
def delete_trial():
    data = request.get_json()
    if data.get("admin_key") != ADMIN_KEY: return jsonify({"status":"denied"}), 403
    key = data.get("license_key", "")
    if key in TRIAL_LICENSES:
        # Delete linked user first
        user_to_delete = None
        for u, ud in TRIAL_USERS.items():
            if ud["linked_license"] == key:
                user_to_delete = u
                break
        if user_to_delete:
            del TRIAL_USERS[user_to_delete]
        del TRIAL_LICENSES[key]
        save_data()
        return jsonify({"status":"deleted"}), 200
    return jsonify({"status":"not_found"}), 404
# ==================================================
# 🔑 ACTIVATE & VERIFY — 100% WORKING
# ==================================================
@app.route('/api/activate', methods=['POST'])
def activate():
    data = request.get_json()
    key = data.get("license_key", "").strip()
    hwid = data.get("hardware_id", "").strip()
    now = datetime.utcnow()

    # --- ORIGINAL PERMANENT LICENSES ---
    if key in LICENSES:
        lic = LICENSES[key]
        if lic["type"] == "unlimited":
            return jsonify({"status":"activated"}), 200
        if lic["type"] == "single":
            if lic["hwid"] == "" or lic["hwid"] == hwid:
                lic["hwid"] = hwid
                save_data()
                return jsonify({"status":"activated"}), 200
            else:
                return jsonify({"status":"invalid_hwid"}), 403

    # --- AUTO GENERATED TRIAL (LOCKED / TIME STARTS NOW) ---
    elif key in TRIAL_LICENSES and TRIAL_LICENSES[key]["type"] == "trial_locked":
        lic = TRIAL_LICENSES[key]

        # ⏳ FIRST ACTIVATION: SET TIME & LOCK
        if lic["hwid"] == "":
            lic["hwid"] = hwid
            lic["activated_at"] = now.isoformat()
            lic["expires_at"] = (now + timedelta(hours=lic["duration_hours"])).isoformat()
            save_data()
            return jsonify({"status":"activated"}), 200

        # ALREADY ACTIVATED BEFORE
        elif lic["hwid"] == hwid:
            if datetime.fromisoformat(lic["expires_at"]) > now:
                return jsonify({"status":"activated"}), 200
            else:
                return jsonify({"status":"expired"}), 403

        # WRONG PC
        else:
            return jsonify({"status":"invalid_hwid"}), 403

    # --- CUSTOM LICENSE (UNLOCKED / ANY PC) ---
    elif key in TRIAL_LICENSES and TRIAL_LICENSES[key]["type"] == "custom_unlocked":
        lic = TRIAL_LICENSES[key]
        if lic["expires_at"] and datetime.fromisoformat(lic["expires_at"]) < now:
            return jsonify({"status":"expired"}), 403
        # ✅ NO HWID CHECK — ALLOW ANY
        return jsonify({"status":"activated"}), 200

    return jsonify({"status":"invalid_key"}), 403


@app.route('/api/verify', methods=['POST'])
def verify():
    data = request.get_json()
    key = data.get("license_key", "").strip()
    hwid = data.get("hardware_id", "").strip()
    now = datetime.utcnow()

    # --- ORIGINAL PERMANENT LICENSES ---
    if key in LICENSES:
        lic = LICENSES[key]
        if lic["type"] == "unlimited":
            return jsonify({"status":"valid"}), 200
        if lic["type"] == "single" and lic["hwid"] == hwid:
            return jsonify({"status":"valid"}), 200

    # --- AUTO GENERATED TRIAL (LOCKED) ---
    elif key in TRIAL_LICENSES and TRIAL_LICENSES[key]["type"] == "trial_locked":
        lic = TRIAL_LICENSES[key]
        # Only valid if activated, locked to this PC, and not expired
        if lic["hwid"] == hwid and lic["expires_at"]:
            exp = datetime.fromisoformat(lic["expires_at"])
            if exp > now:
                return jsonify({"status":"valid"}), 200
            else:
                return jsonify({"status":"expired"}), 403
        else:
            return jsonify({"status":"invalid"}), 403

    # --- CUSTOM LICENSE (UNLOCKED) ---
    elif key in TRIAL_LICENSES and TRIAL_LICENSES[key]["type"] == "custom_unlocked":
        lic = TRIAL_LICENSES[key]
        if lic["expires_at"]:
            exp = datetime.fromisoformat(lic["expires_at"])
            if exp > now:
                return jsonify({"status":"valid"}), 200
            else:
                return jsonify({"status":"expired"}), 403

    return jsonify({"status":"invalid"}), 403


# ✅ FINAL FIXED LOGIN — NO MORE "USER NOT FOUND"
@app.route('/api/login', methods=['POST'])
def login():
    # READ DATA SAFELY — WORKS WITH ANY CLIENT FORMAT
    try:
        data = request.get_json(force=True)
    except:
        data = request.form.to_dict()

    # CLEAN INPUTS COMPLETELY
    user_input = str(data.get("username", "")).strip()
    pass_input = str(data.get("password", "")).strip()

    print(f"[LOGIN ATTEMPT] User: '{user_input}' | Pass: '{pass_input}'")

    # --- 1. CHECK HARDCODED USERS FIRST ---
    for u, p in VALID_USERS.items():
        if u.strip() == user_input and p.strip() == pass_input:
            print("[SUCCESS] Hardcoded User OK")
            return jsonify({"status":"success"}), 200

    # --- 2. CHECK ALL GENERATED USERS ---
    for u, udata in TRIAL_USERS.items():
        if u.strip() == user_input and udata.get("password", "").strip() == pass_input:
            # User found, check license status
            linked_key = udata.get("linked_license")
            lic_data = TRIAL_LICENSES.get(linked_key)
            now = datetime.utcnow()

            print(f"[SUCCESS] Generated User OK -> License: {linked_key}")

            # Check expiry rules
            if lic_data and lic_data["type"] == "trial_locked":
                if lic_data["expires_at"] is None:
                    return jsonify({"status":"success"}), 200
                else:
                    if datetime.fromisoformat(lic_data["expires_at"]) > now:
                        return jsonify({"status":"success"}), 200
                    else:
                        return jsonify({"status":"expired"}), 403

            elif lic_data and lic_data["type"] == "custom_unlocked":
                if lic_data["expires_at"] and datetime.fromisoformat(lic_data["expires_at"]) > now:
                    return jsonify({"status":"success"}), 200
                else:
                    return jsonify({"status":"expired"}), 403

            return jsonify({"status":"success"}), 200

    # ❌ NOT FOUND AT ALL
    print("[FAILED] User or Password incorrect")
    return jsonify({"status":"invalid"}), 401


if __name__ == "__main__":
    load_data()
    app.run(host="0.0.0.0", port=5000, debug=True)
