from flask import Flask, request, jsonify, render_template_string
import hashlib
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
        load_data()

# ==================================================
# 🎨 ADMIN PANEL HTML — UPDATED WITH CUSTOM FIELDS
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
            <div class="tab active" onclick="showTab('generate')">GENERATE TRIAL</div>
            <div class="tab" onclick="showTab('trials')">VIEW TRIALS</div>
        </div>

        <div id="generate" class="content active">
            <h3>Create New Trial License</h3>
            
            <label>Custom Username:</label>
            <input type="text" id="custom-user" placeholder="Leave blank for auto-generate">

            <label>Custom Password:</label>
            <input type="text" id="custom-pass" placeholder="Leave blank for auto-generate">

            <label>Custom License Key:</label>
            <input type="text" id="custom-key" placeholder="Leave blank for auto-generate">

            <label>Duration (Hours):</label>
            <input type="number" id="duration" min="1" value="3" placeholder="Enter hours (168+ allowed)">

            <br>
            <button class="btn-primary" onclick="createTrial()">GENERATE LICENSE</button>
            <div id="result" class="result" style="display: none;"></div>
        </div>
        <div id="trials" class="content">
            <h3>All Active Trials</h3>
            <button class="btn-primary" onclick="loadTrials()">REFRESH LIST</button>
            <table id="trials-table">
                <tr><th>LICENSE KEY</th><th>USERNAME</th><th>PASSWORD</th><th>DURATION</th><th>STATUS</th><th>REMAINING</th><th>ACTION</th></tr>
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

        async function createTrial() {
            const duration = document.getElementById('duration').value;
            const customUser = document.getElementById('custom-user').value;
            const customPass = document.getElementById('custom-pass').value;
            const customKey = document.getElementById('custom-key').value;

            const res = await fetch(SERVER_URL + '/api/admin/generate-trial', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    admin_key: ADMIN_KEY,
                    duration_hours: parseInt(duration),
                    custom_username: customUser,
                    custom_password: customPass,
                    custom_license: customKey
                })
            });

            const data = await res.json();
            document.getElementById('result').style.display = 'block';
            if(res.ok) {
                document.getElementById('result').innerHTML = `
✅ TRIAL CREATED
━━━━━━━━━━━━━━━━━━
🔑 LICENSE: ${data.trial_license}
👤 USER: ${data.trial_username}
🔒 PASS: ${data.trial_password}
⏱️ TIME: ${data.duration_hours} HOURS
♾️ WORKS ON ANY PC — NO LIMIT
━━━━━━━━━━━━━━━━━━
                `;
                loadTrials();
            } else {
                document.getElementById('result').innerHTML = '❌ ERROR!';
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
            table.innerHTML = `<tr><th>LICENSE KEY</th><th>USERNAME</th><th>PASSWORD</th><th>DURATION</th><th>STATUS</th><th>REMAINING</th><th>ACTION</th></tr>`;
            
            data.trials.forEach(trial => {
                const row = table.insertRow(-1);
                row.innerHTML = `
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
            if(!confirm('Delete this trial?')) return;
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
# 🔐 APIs — UPDATED: CUSTOM LICENSES = NO HWID LOCK
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

@app.route('/api/admin/generate-trial', methods=['POST'])
def generate_trial():
    data = request.get_json()
    if data.get("admin_key") != ADMIN_KEY: 
        return jsonify({"status":"denied"}),403
    
    dur = int(data.get("duration_hours",3))
    custom_user = data.get("custom_username","").strip()
    custom_pass = data.get("custom_password","").strip()
    custom_key = data.get("custom_license","").strip()

    lic = custom_key if custom_key else f"JEPFX-TRIAL-{uuid.uuid4().hex[:8].upper()}"
    user = custom_user if custom_user else f"TRIAL-{uuid.uuid4().hex[:6].upper()}"
    pwd = custom_pass if custom_pass else uuid.uuid4().hex[:10].upper()

    # ✅ NO HWID SAVE — WORKS ON ANY PC
    TRIAL_LICENSES[lic] = {
    "type":"trial_unlimited",  # <-- NEW TYPE: NO LOCK
    "hwid": None,              # <-- NO HWID STORED
    "duration_hours":dur,
    "start_time":None,
    "expires_at": (datetime.utcnow() + timedelta(hours=dur)).isoformat()
    }
    TRIAL_USERS[user] = {"password":pwd,"linked_license":lic}
    save_data()
    return jsonify({
        "trial_license":lic,"trial_username":user,"trial_password":pwd,"duration_hours":dur
    }),200

@app.route('/api/admin/get-all-trials', methods=['POST'])
def get_all():
    if request.get_json().get("admin_key") != ADMIN_KEY: 
        return jsonify({"status":"denied"}),403
    now = datetime.utcnow()
    list_trials = []
    user_map = {u_data['linked_license']: (u, u_data['password']) for u, u_data in TRIAL_USERS.items()}

    for k,v in TRIAL_LICENSES.items():
        status = "✅ ACTIVE (NO LOCK)"
        rem = "-"
        uname, upass = "-", "-"
        if k in user_map:
            uname, upass = user_map[k]

        if v["expires_at"]:
            exp = datetime.fromisoformat(v["expires_at"])
            if exp > now:
                diff = exp - now
                rem = f"{diff.days}d {diff.seconds//3600}h {(diff.seconds//60)%60}m"
            else:
                status = "❌ EXPIRED"
                rem = "EXPIRED"

        list_trials.append({
        "license_key":k,"username":uname,"password":upass,
        "duration_hours":f"{v['duration_hours']}h","status":status,"remaining":rem
        })
    return jsonify({"trials":list_trials}),200

@app.route('/api/admin/delete-trial', methods=['POST'])
def delete_trial():
    data = request.get_json()
    if data.get("admin_key") != ADMIN_KEY: 
        return jsonify({"status":"denied"}), 403
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
# 🔑 ACTIVATE & VERIFY — UPDATED FOR NO LOCK
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
                return jsonify({"status":"activated"}), 200
            else:
                return jsonify({"status":"invalid_hwid"}), 403

    # --- CUSTOM / TRIAL LICENSES — NO LOCK, ANY PC ---
    elif key in TRIAL_LICENSES:
        lic = TRIAL_LICENSES[key]
        if lic["expires_at"] and datetime.fromisoformat(lic["expires_at"]) < now:
            return jsonify({"status":"expired"}), 403
        
        # ✅ IGNORE HWID COMPLETELY — WORKS EVERYWHERE
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

    # --- CUSTOM / TRIAL LICENSES — NO LOCK, ANY PC ---
    elif key in TRIAL_LICENSES:
        lic = TRIAL_LICENSES[key]
        if lic["expires_at"]:
            exp = datetime.fromisoformat(lic["expires_at"])
            if exp > now:
                return jsonify({"status":"valid"}), 200
            else:
                return jsonify({"status":"expired"}), 403

    return jsonify({"status":"invalid"}), 403


@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    user = data.get("username", "").strip()
    pwd = data.get("password", "").strip()

    # --- ORIGINAL ADMIN/USERS ---
    if user in VALID_USERS and VALID_USERS[user] == pwd:
        return jsonify({"status":"success"}), 200

    # --- CUSTOM USERS — WORKS ANYWHERE ---
    for u, u_data in TRIAL_USERS.items():
        if u == user and u_data["password"] == pwd:
            return jsonify({"status":"success"}), 200

    return jsonify({"status":"invalid"}), 401


if __name__ == "__main__":
    load_data()
    app.run(host="0.0.0.0", port=5000, debug=True)
