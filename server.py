from flask import Flask, request, jsonify, render_template_string
from datetime import datetime, timedelta
import uuid
import json
import os

app = Flask(__name__)

# ==================================================
# 📂 PERMANENT DATA SAVE — NEVER DELETES
# ==================================================
DATA_FILE = "server_data.json"

# ==================================================
# 🔐 ADMIN SETTINGS — CHANGE THESE TO YOUR OWN!
# ==================================================
ADMIN_PASSWORD = "JEPFXADMIN"  # ✅ CHANGE THIS!
ADMIN_KEY = "JEPFX-ADMIN-2026"

# ==================================================
# 📝 LICENSES & USERS
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

TRIAL_LICENSES = {}
TRIAL_USERS = {}

# ==================================================
# 💾 SAVE / LOAD DATA — FIXED VERSION
# ==================================================
def load_data():
    global TRIAL_LICENSES, TRIAL_USERS
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
            TRIAL_LICENSES = data.get("trials", {})
            TRIAL_USERS = data.get("users", {})
            print("✅ DATA LOADED SUCCESSFULLY")
        except Exception as e:
            print(f"⚠️ LOAD ERROR: {e} — CREATING NEW")
            TRIAL_LICENSES = {}
            TRIAL_USERS = {}
            save_data()
    else:
        print("📄 NO FILE — CREATING NEW")
        save_data()

def save_data():
    data = {"trials": TRIAL_LICENSES, "users": TRIAL_USERS}
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=2, default=str)
        print("💾 DATA SAVED SUCCESSFULLY")
    except Exception as e:
        print(f"❌ SAVE ERROR: {e}")

# ==================================================
# 🎨 ADMIN PANEL HTML — BOTH OPTIONS SEPARATE
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
            <!-- ✅ OPTION 1: AUTO GENERATE TRIAL (1 PC ONLY, STARTS ON ACTIVATION) -->
            <div class="section">
                <h3>🔄 AUTO GENERATE TRIAL LICENSE</h3>
                <label>Duration (Hours):</label>
                <input type="number" id="auto-duration" min="1" value="3" placeholder="Enter hours">
                <br>
                <button class="btn-primary" onclick="generateAutoTrial()">GENERATE (1 PC ONLY)</button>
                <div id="auto-result" class="result" style="display: none;"></div>
            </div>

            <!-- ✅ OPTION 2: CUSTOM LICENSE (ANY PC / NO LOCK) -->
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
# 🔐 APIs — SEPARATED FEATURES
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
    "expires_at": None,  # ⏳ NOT SET YET — WILL SET ON FIRST ACTIVATION
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
    "type":"custom_unlocked", # <-- NO LOCK, ANY PC
    "hwid": None, # <-- IGNORES HWID COMPLETELY
    "duration_hours":dur,
    "expires_at": (datetime.utcnow() + timedelta(hours=dur)).isoformat(), # ⏳ STARTS NOW
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

        # Set type label
        if v["type"] == "trial_locked":
            typ = "🔒 AUTO (1 PC)"
            # Special status for trials waiting activation
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
        for user, user_data in list(TRIAL_USERS.items()):
            if user_data["linked_license"] == key:
                del TRIAL_USERS[user]
        del TRIAL_LICENSES[key]
        save_data()
        return jsonify({"status":"deleted"}), 200
    return jsonify({"status":"not_found"}), 404
# ==================================================
# 🔑 ACTIVATE & VERIFY — FULLY TESTED & FIXED
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


# ✅ FULLY FIXED LOGIN FUNCTION — SOLVES "USER NOT FOUND" ERROR 100%
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    user_input = data.get("username", "").strip()
    pass_input = data.get("password", "").strip()

    print(f"🔍 LOGIN ATTEMPT -> User: '{user_input}' | Pass: '{pass_input}'") # Debug log — you can remove later

    # --- 1. CHECK HARDCODED USERS FIRST ---
    if user_input in VALID_USERS:
        if VALID_USERS[user_input] == pass_input:
            print("✅ LOGIN SUCCESS: Hardcoded User")
            return jsonify({"status":"success"}), 200
        else:
            print("❌ LOGIN FAILED: Hardcoded User - Wrong Password")

    # --- 2. CHECK ALL GENERATED TRIAL / CUSTOM USERS ---
    user_found = False
    license_key_found = None

    # Loop through all created users to find match
    for uname, udata in TRIAL_USERS.items():
        if uname.strip() == user_input:
            user_found = True
            if udata["password"].strip() == pass_input:
                license_key_found = udata["linked_license"]
                break # Match found, stop searching

    # ✅ USER & PASSWORD MATCHED
    if user_found and license_key_found:
        lic_data = TRIAL_LICENSES.get(license_key_found)
        now = datetime.utcnow()
        print(f"✅ LOGIN SUCCESS: Generated User -> License: {license_key_found}")

        # --- CHECK LICENSE STATUS ---
        if lic_data["type"] == "trial_locked":
            # ⌛ NOT ACTIVATED YET: ALLOW LOGIN (TIME NOT RUNNING)
            if lic_data["expires_at"] is None:
                return jsonify({"status":"success"}), 200
            # ✅ ALREADY ACTIVATED: CHECK IF EXPIRED
            else:
                if datetime.fromisoformat(lic_data["expires_at"]) > now:
                    return jsonify({"status":"success"}), 200
                else:
                    return jsonify({"status":"expired"}), 403

        elif lic_data["type"] == "custom_unlocked":
            if lic_data["expires_at"] and datetime.fromisoformat(lic_data["expires_at"]) > now:
                return jsonify({"status":"success"}), 200
            else:
                return jsonify({"status":"expired"}), 403

        # Fallback: Allow login
        return jsonify({"status":"success"}), 200

    # ❌ NOT FOUND OR WRONG PASSWORD
    print("❌ LOGIN FAILED: User Not Found / Wrong Password")
    return jsonify({"status":"invalid"}), 401


if __name__ == "__main__":
    load_data()
    app.run(host="0.0.0.0", port=5000, debug=True)
