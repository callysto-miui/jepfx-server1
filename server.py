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
# 🎨 ADMIN PANEL HTML
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
        <label>Duration:</label>
        <select id="duration">
            <option value="3">3 Hours</option>
            <option value="6">6 Hours</option>
            <option value="12">12 Hours</option>
            <option value="24">1 Day</option>
            <option value="168">7 Days</option>
        </select>
        <br>
        <button class="btn-primary" onclick="createTrial()">GENERATE LICENSE</button>
        <div id="result" class="result" style="display: none;"></div>
    </div>

    <div id="trials" class="content">
        <h3>All Active Trials</h3>
        <button class="btn-primary" onclick="loadTrials()">REFRESH LIST</button>
        <table id="trials-table">
            <tr><th>LICENSE KEY</th><th>DURATION</th><th>STATUS</th><th>REMAINING</th><th>ACTION</th></tr>
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
        const res = await fetch(SERVER_URL + '/api/admin/generate-trial', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({admin_key: ADMIN_KEY, duration_hours: parseInt(duration)})
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
        table.innerHTML = `<tr><th>LICENSE KEY</th><th>DURATION</th><th>STATUS</th><th>REMAINING</th><th>ACTION</th></tr>`;
        data.trials.forEach(trial => {
            const row = table.insertRow(-1);
            row.innerHTML = `
                <td>${trial.license_key}</td>
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
# 🔐 APIs
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
    if data.get("admin_key") != ADMIN_KEY: return jsonify({"status":"denied"}),403
    dur = int(data.get("duration_hours",3))
    lic = f"JEPFX-TRIAL-{uuid.uuid4().hex[:8].upper()}"
    user = f"TRIAL-{uuid.uuid4().hex[:6].upper()}"
    pwd = uuid.uuid4().hex[:10].upper()

    TRIAL_LICENSES[lic] = {
        "type":"trial","hwid":"","duration_hours":dur,
        "start_time":None,"expires_at":None,"activated_at":None
    }
    TRIAL_USERS[user] = {"password":pwd,"linked_license":lic}
    save_data()
    return jsonify({"trial_license":lic,"trial_username":user,"trial_password":pwd,"duration_hours":dur}),200

@app.route('/api/admin/get-all-trials', methods=['POST'])
def get_all():
    if request.get_json().get("admin_key") != ADMIN_KEY: return jsonify({"status":"denied"}),403
    now = datetime.utcnow()
    list_trials = []
    for k,v in TRIAL_LICENSES.items():
        status = "NOT ACTIVATED"
        rem = "-"
        if v["expires_at"]:
            exp = datetime.fromisoformat(v["expires_at"])
            if exp > now:
                status = "✅ ACTIVE"
                diff = exp - now
                rem = f"{diff.days}d {diff.seconds//3600}h {(diff.seconds//60)%60}m"
            else:
                status = "❌ EXPIRED"
                rem = "EXPIRED"
        list_trials.append({
            "license_key":k,"duration_hours":f"{v['duration_hours']}h",
            "hwid":v["hwid"] or "-","activated_at":v["activated_at"] or "-",
            "expires_at":v["expires_at"] or "-","status":status,"remaining":rem
        })
    return jsonify({"trials":list_trials}),200
@app.route('/api/admin/delete-trial', methods=['POST'])
def delete_trial():
    data = request.get_json()
    if data.get("admin_key") != ADMIN_KEY: 
        return jsonify({"status":"denied"}), 403
    key = data.get("license_key", "")
    if key in TRIAL_LICENSES:
        # Delete linked user account too
        for user, user_data in list(TRIAL_USERS.items()):
            if user_data["linked_license"] == key:
                del TRIAL_USERS[user]
        del TRIAL_LICENSES[key]
        save_data()
        return jsonify({"status":"deleted"}), 200
    return jsonify({"status":"not_found"}), 404

# ==================================================
# 🔑 ACTIVATE & VERIFY — ✅ FULLY FIXED & WORKING
# ==================================================
@app.route('/api/activate', methods=['POST'])
def activate():
    data = request.get_json()
    key = data.get("license_key", "").strip()
    hwid = data.get("hardware_id", "").strip()
    now = datetime.utcnow()

    # Check Permanent Licenses first
    if key in LICENSES:
        lic = LICENSES[key]
        if lic["type"] == "unlimited":
            if hwid not in lic["hwid"]:
                lic["hwid"].append(hwid)
            return jsonify({"status":"activated"}), 200
        if lic["type"] == "single":
            if lic["hwid"] == "":
                lic["hwid"] = hwid
                return jsonify({"status":"activated"}), 200
            elif lic["hwid"] == hwid:
                return jsonify({"status":"activated"}), 200
            else:
                return jsonify({"status":"blocked", "msg":"Used on another PC"}), 403

    # ✅ Check Trial Licenses — FIXED LOGIC HERE
    if key in TRIAL_LICENSES:
        lic = TRIAL_LICENSES[key]
        if lic["start_time"] is None:
            # First time activation: start timer
            lic["start_time"] = now.isoformat()
            lic["activated_at"] = now.isoformat()
            lic["expires_at"] = (now + timedelta(hours=lic["duration_hours"])).isoformat()
            lic["hwid"] = hwid
            save_data()
            return jsonify({
                "status":"activated",
                "msg":f"Trial activated! Expires in {lic['duration_hours']} hours"
            }), 200
        else:
            exp_time = datetime.fromisoformat(str(lic["expires_at"]))
            if now > exp_time:
                return jsonify({"status":"expired", "msg":"Trial already expired"}), 403
            if lic["hwid"] == hwid:
                return jsonify({"status":"activated"}), 200
            else:
                return jsonify({"status":"blocked", "msg":"Trial used on another PC"}), 403

    return jsonify({"status":"invalid", "msg":"License key does not exist"}), 403


@app.route('/api/verify-license', methods=['POST'])
def verify():
    data = request.get_json()
    hwid = data.get("hwid", "")
    key_hash = data.get("hash", "")
    now = datetime.utcnow()

    # Verify permanent licenses
    for key, lic in LICENSES.items():
        if hashlib.sha256(key.encode()).hexdigest() == key_hash:
            if lic["type"] == "unlimited" and hwid in lic["hwid"]:
                return jsonify({"ok": True}), 200
            if lic["type"] == "single" and lic["hwid"] == hwid:
                return jsonify({"ok": True}), 200

    # Verify trial licenses
    for key, lic in TRIAL_LICENSES.items():
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


@app.route('/api/validate-user', methods=['POST'])
def validate_user():
    username = request.get_json().get("username", "")
    if username in VALID_USERS or username in TRIAL_USERS:
        return jsonify({"ok": True}), 200
    return "", 403


@app.route('/api/check-password', methods=['POST'])
def check_pass():
    data = request.get_json()
    username = data.get("username", "")
    password = data.get("password", "")
    
    if (username in VALID_USERS and VALID_USERS[username] == password) or \
       (username in TRIAL_USERS and TRIAL_USERS[username]["password"] == password):
        return jsonify({"ok": True}), 200
    return "", 403


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
