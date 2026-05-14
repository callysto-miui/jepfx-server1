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
# Password protection: only people who know this code can open /admin
ADMIN_PASSWORD = "JEPFX-ADMIN"  # ✅ CHANGE THIS TO WHATEVER YOU WANT!
ADMIN_KEY = "JEPFX-ADMIN-2026"  # Keep this same or change, no problem

# ==================================================
# 📝 YOUR LICENSES & USERS
# ==================================================
LICENSES = {
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

TRIAL_LICENSES = {}
TRIAL_USERS = {}

# ==================================================
# 💾 SAVE & LOAD DATA — KEEPS TRIALS FOREVER
# ==================================================
def load_data():
    global TRIAL_LICENSES, TRIAL_USERS
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
                TRIAL_LICENSES = data.get("trials", {})
                TRIAL_USERS = data.get("users", {})
            print("✅ DATA LOADED - ALL TRIALS SAVED!")
        except:
            TRIAL_LICENSES = {}
            TRIAL_USERS = {}
            save_data()
    else:
        save_data()

def save_data():
    data = {"trials": TRIAL_LICENSES, "users": TRIAL_USERS}
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2, default=str)

load_data()

# ==================================================
# 🎨 ADMIN PANEL HTML — OPENS AT /admin
# ==================================================
ADMIN_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>JEPFX ADMIN PANEL</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { box-sizing: border-box; font-family: Arial, sans-serif; }
        body { 
            background: #1a103d; 
            color: white; 
            margin: 0; 
            padding: 20px;
        }
        .login-box {
            max-width: 400px;
            margin: 50px auto;
            background: #241854;
            padding: 30px;
            border-radius: 10px;
            text-align: center;
        }
        .panel-box {
            display: none;
        }
        .panel-box.active {
            display: block;
        }
        h1, h2 { color: #7B61FF; }
        input, select {
            width: 100%;
            padding: 12px;
            margin: 10px 0;
            border: none;
            border-radius: 5px;
            background: #3a2b70;
            color: white;
            font-size: 16px;
        }
        button {
            padding: 12px 25px;
            margin: 10px 5px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
            font-weight: bold;
        }
        .btn-primary { background: #7B61FF; color: white; }
        .btn-danger { background: #ef4444; color: white; }
        .tabs {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }
        .tab {
            padding: 12px 25px;
            background: #241854;
            border-radius: 5px;
            cursor: pointer;
        }
        .tab.active {
            background: #7B61FF;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
            background: #241854;
        }
        th, td {
            padding: 12px;
            text-align: center;
            border-bottom: 1px solid #3a2b70;
        }
        th { background: #3a2b70; }
        .result {
            background: #241854;
            padding: 20px;
            border-radius: 5px;
            margin-top: 20px;
            white-space: pre-line;
        }
    </style>
</head>
<body>

<!-- 🔐 LOGIN SCREEN -->
<div id="login-screen" class="login-box">
    <h2>🔒 ADMIN LOGIN</h2>
    <p>Enter access code to continue</p>
    <input type="password" id="password-input" placeholder="Enter code..." autocomplete="off">
    <button class="btn-primary" onclick="checkLogin()">LOGIN</button>
    <p id="error-msg" style="color: #ef4444; display: none;">Wrong code! Try again.</p>
</div>
<!-- 📊 ADMIN PANEL -->
<div id="panel" class="panel-box">
    <h1>⚡ JEPFX ADMIN PANEL</h1>
    
    <div class="tabs">
        <div class="tab active" onclick="showTab('generate')">GENERATE TRIAL</div>
        <div class="tab" onclick="showTab('trials')">VIEW TRIALS</div>
    </div>

    <!-- GENERATE TRIAL -->
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

    <!-- VIEW ALL TRIALS -->
    <div id="trials" class="content">
        <h3>All Active Trials</h3>
        <button class="btn-primary" onclick="loadTrials()">REFRESH LIST</button>
        <table id="trials-table">
            <tr>
                <th>LICENSE KEY</th>
                <th>DURATION</th>
                <th>STATUS</th>
                <th>REMAINING</th>
                <th>ACTION</th>
            </tr>
        </table>
    </div>
</div>

<script>
    const SERVER_URL = window.location.origin;
    const ADMIN_KEY = "{{ admin_key }}";

    // 🔐 CHECK LOGIN
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
        })
        .catch(() => {
            document.getElementById('error-msg').style.display = 'block';
        });
    }

    // 📌 SWITCH TABS
    function showTab(tabName) {
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.content').forEach(c => c.classList.remove('active'));
        document.querySelector(`.tab[onclick="showTab('${tabName}')"]`).classList.add('active');
        document.getElementById(tabName).classList.add('active');
        if(tabName == 'trials') loadTrials();
    }

    // ➕ CREATE NEW TRIAL
    async function createTrial() {
        const duration = document.getElementById('duration').value;
        try {
            const res = await fetch(SERVER_URL + '/api/admin/generate-trial', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    admin_key: ADMIN_KEY,
                    duration_hours: parseInt(duration)
                })
            });
            const data = await res.json();
            
            if(res.ok) {
                document.getElementById('result').style.display = 'block';
                document.getElementById('result').innerHTML = `
✅ TRIAL CREATED SUCCESSFULLY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔑 LICENSE : ${data.trial_license}
👤 USERNAME : ${data.trial_username}
🔒 PASSWORD : ${data.trial_password}
⏱️ DURATION : ${data.duration_hours} HOURS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
`;
                loadTrials();
            } else {
                document.getElementById('result').style.display = 'block';
                document.getElementById('result').innerHTML = '❌ ERROR: Wrong code or server issue!';
            }
        } catch(err) {
            document.getElementById('result').style.display = 'block';
            document.getElementById('result').innerHTML = '❌ SERVER OFFLINE!';
        }
    }

    // 📋 LOAD ALL TRIALS
    async function loadTrials() {
        try {
            const res = await fetch(SERVER_URL + '/api/admin/get-all-trials', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({admin_key: ADMIN_KEY})
            });
            const data = await res.json();
            
            const table = document.getElementById('trials-table');
            table.innerHTML = `
                <tr>
                    <th>LICENSE KEY</th>
                    <th>DURATION</th>
                    <th>STATUS</th>
                    <th>REMAINING</th>
                    <th>ACTION</th>
                </tr>
            `;

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
        } catch(err) {
            alert('Error loading data!');
        }
    }

    // 🗑️ DELETE TRIAL
    async function deleteTrial(key) {
        if(!confirm('Delete this trial? This cannot be undone!')) return;
        
        try {
            await fetch(SERVER_URL + '/api/admin/delete-trial', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({admin_key: ADMIN_KEY, license_key: key})
            });
            loadTrials();
        } catch(err) {
            alert('Error deleting!');
        }
    }
</script>

</body>
</html>
"""

# ==================================================
# 🔐 PASSWORD CHECK API
# ==================================================
@app.route('/api/admin/check-password', methods=['POST'])
def check_password():
    data = request.get_json()
    input_code = data.get("code", "")
    
    if input_code == ADMIN_PASSWORD:
        return jsonify({"success": True}), 200
    return jsonify({"success": False}), 403

# ==================================================
# 📝 ADMIN PANEL PAGE — OPENS AT jepfx-tool-server.onrender.com/admin
# ==================================================
@app.route('/admin')
def admin_page():
    # Replace variables in HTML
    html = ADMIN_HTML.replace("{{ admin_key }}", ADMIN_KEY)
    return render_template_string(html)

# ==================================================
# 🚀 ALL OTHER API ROUTES
# ==================================================
@app.route('/')
def home():
    return "✅ JEPFX SERVER | OPEN ADMIN PANEL AT /admin"

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

    save_data()
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
            "activated_at": lic_data["activated_at"] if lic_data["activated_at"] else "-",
            "expires_at": lic_data["expires_at"] if lic_data["expires_at"] else "-",
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
        # Delete linked user too
        for user, udata in list(TRIAL_USERS.items()):
            if udata["linked_license"] == lic_key:
                del TRIAL_USERS[user]
        del TRIAL_LICENSES[lic_key]
        save_data()  # Save changes
        return jsonify({"status": "deleted"}), 200
    return jsonify({"status": "not_found"}), 404

# ==================================================
# 🔑 LICENSE ACTIVATION & VERIFICATION (FOR USERS)
# ==================================================
@app.route('/api/activate', methods=['POST'])
def activate():
    data = request.get_json()
    key = data.get("license_key", "").strip()
    hwid = data.get("hardware_id", "").strip()
    now = datetime.utcnow()

    # Check permanent licenses first
    if key in LICENSES:
        lic = LICENSES[key]
        if lic["type"] == "unlimited":
            if hwid not in lic["hwid"]:
                lic["hwid"].append(hwid)
                return jsonify({"status": "activated"}), 200
            else:
                return jsonify({"status": "activated"}), 200
        if lic["type"] == "single":
            if lic["hwid"] == "":
                lic["hwid"] = hwid
                return jsonify({"status": "activated"}), 200
            elif lic["hwid"] == hwid:
                return jsonify({"status": "activated"}), 200
            else:
                return jsonify({"status": "blocked","msg":"Used on another PC"}), 403

    # Check trial licenses
    if key in TRIAL_LICENSES:
        lic = TRIAL_LICENSES[key]
        if lic["start_time"] is None:
            # First activation — start timer
            lic["start_time"] = now.isoformat()
            lic["activated_at"] = now.isoformat()
            lic["expires_at"] = (now + timedelta(hours=lic["duration_hours"])).isoformat()
            lic["hwid"] = hwid
            save_data()
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

    # Verify permanent licenses
    for key, lic in LICENSES.items():
        if hashlib.sha256(key.encode()).hexdigest() == key_hash:
            if lic["type"]=="unlimited" and hwid in lic["hwid"]:
                return jsonify({"ok":True}), 200
            if lic["type"]=="single" and lic["hwid"]==hwid:
                return jsonify({"ok":True}), 200

    # Verify trial licenses
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
