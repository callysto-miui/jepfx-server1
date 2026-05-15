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
ADMIN_PASSWORD = "JEPFX-ADMIN"  # ✅ CHANGE THIS!
ADMIN_KEY = "JEPFX-ADMIN-2026"

# ==================================================
# 📝 LICENSES & USERS STORAGE
# ==================================================
LICENSES = {
    "JEPFX": {"type": "unlimited", "hwid": [], "expires_at": None},
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

# This will store ALL custom activations
CUSTOM_LICENSES = {}
CUSTOM_USERS = {}

# ==================================================
# 💾 SAVE / LOAD DATA FUNCTIONS
# ==================================================
def load_data():
    global CUSTOM_LICENSES, CUSTOM_USERS
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
                CUSTOM_LICENSES = data.get("custom_licenses", {})
                CUSTOM_USERS = data.get("custom_users", {})
            print("DATA LOADED SUCCESSFULLY")
        except Exception as e:
            print(f"LOAD ERROR: {e} — CREATING NEW FILE")
            CUSTOM_LICENSES = {}
            CUSTOM_USERS = {}
            save_data()
    else:
        print("NO DATA FILE — CREATING NEW")
        save_data()

def save_data():
    data = {
        "custom_licenses": CUSTOM_LICENSES,
        "custom_users": CUSTOM_USERS
    }
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=2, default=str)
        print("DATA SAVED SUCCESSFULLY")
    except Exception as e:
        print(f"SAVE ERROR: {e}")

# Load saved data when server starts
load_data()

# ==================================================
# 🎨 ADMIN PANEL HTML — FULLY CUSTOMIZABLE
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
        .note { color: #aaa; font-size: 14px; margin: -8px 0 10px 0; }
    </style>
</head>
<body>
<div id="login-screen" class="login-box">
    <h2>ADMIN LOGIN</h2>
    <p>Enter access code to continue</p>
    <input type="password" id="password-input" placeholder="Enter code..." autocomplete="off">
    <button class="btn-primary" onclick="checkLogin()">LOGIN</button>
    <p id="error-msg" style="color: #ef4444; display: none;">Wrong code! Try again.</p>
</div>
<div id="panel" class="panel-box">
    <h1>JEPFX ADMIN PANEL</h1>
    <div class="tabs">
        <div class="tab active" onclick="showTab('create')">CREATE CUSTOM</div>
        <div class="tab" onclick="showTab('list')">VIEW ALL</div>
    </div>

    <!-- CREATE CUSTOM ACTIVATION TAB -->
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
        
        <div id="output" class="result" style="display: none;"></div>
    </div>

    <!-- VIEW ALL ACTIVATIONS TAB -->
    <div id="list" class="content">
        <h3>All Created Activations</h3>
        <button class="btn-primary" onclick="loadAll()">REFRESH</button>
        <table id="data-table">
            <tr>
                <th>USERNAME</th>
                <th>LICENSE KEY</th>
                <th>HOURS</th>
                <th>STATUS</th>
                <th>REMAINING TIME</th>
                <th>ACTION</th>
            </tr>
        </table>
    </div>
</div>

<script>
    const SERVER_URL = window.location.origin;
    const ADMIN_KEY = "{{ admin_key }}";

    // Login check
    function checkLogin() {
        const code = document.getElementById('password-input').value;
        fetch(SERVER_URL + '/api/admin/check-pass', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({code: code})
        })
        .then(res => res.json())
        .then(data => {
            if(data.ok) {
                document.getElementById('login-screen').style.display = 'none';
                document.getElementById('panel').classList.add('active');
            } else {
                document.getElementById('error-msg').style.display = 'block';
            }
        });
    }

    // Switch tabs
    function showTab(tabName) {
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.content').forEach(c => c.classList.remove('active'));
        document.querySelector(`.tab[onclick="showTab('${tabName}')"]`).classList.add('active');
        document.getElementById(tabName).classList.add('active');
        if(tabName === 'list') loadAll();
    }

    // Create custom activation
    async function makeCustom() {
        const user = document.getElementById('cust_user').value.trim();
        const pass = document.getElementById('cust_pass').value.trim();
        const lic = document.getElementById('cust_license').value.trim();
        const hrs = parseInt(document.getElementById('cust_hours').value);

        if(!user || !pass || !lic || !hrs) return alert("Fill all fields!");

        const res = await fetch(SERVER_URL + '/api/admin/create-custom', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                admin_key: ADMIN_KEY,
                username: user,
                password: pass,
                license: lic,
                hours: hrs
            })
        });
        const data = await res.json();
        document.getElementById('output').style.display = 'block';
        if(res.ok) {
            document.getElementById('output').innerHTML = `
SUCCESSFULLY CREATED
━━━━━━━━━━━━━━━━━━━━
USERNAME : ${user}
PASSWORD : ${pass}
LICENSE  : ${lic}
DURATION : ${hrs} HOURS
━━━━━━━━━━━━━━━━━━━━
READY TO USE!
            `;
            loadAll();
        } else {
            document.getElementById('output').innerHTML = 'ERROR: Username or License already exists!';
        }
    }

    // Load all data
    async function loadAll() {
        const res = await fetch(SERVER_URL + '/api/admin/get-all', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({admin_key: ADMIN_KEY})
        });
        const data = await res.json();
        const table = document.getElementById('data-table');
        table.innerHTML = `<tr><th>USERNAME</th><th>LICENSE KEY</th><th>HOURS</th><th>STATUS</th><th>REMAINING TIME</th><th>ACTION</th></tr>`;
        
        data.list.forEach(item => {
            const row = table.insertRow(-1);
            row.innerHTML = `
                <td>${item.username}</td>
                <td>${item.license}</td>
                <td>${item.hours}</td>
                <td>${item.status}</td>
                <td>${item.remaining}</td>
                <td><button class="btn-danger" onclick="deleteItem('${item.license}')">DELETE</button></td>
            `;
        });
    }

    // Delete item
    async function deleteItem(license) {
        if(!confirm('Delete this activation?')) return;
        await fetch(SERVER_URL + '/api/admin/delete', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({admin_key: ADMIN_KEY, license: license})
        });
        loadAll();
    }
</script>
</body></html>
"""

# ==================================================
# 🔐 ADMIN API ROUTES
# ==================================================
@app.route('/api/admin/check-pass', methods=['POST'])
def api_check_pass():
    return jsonify({"ok": request.get_json().get("code") == ADMIN_PASSWORD}), 200

@app.route('/admin')
def admin_page():
    return render_template_string(ADMIN_HTML.replace("{{ admin_key }}", ADMIN_KEY))

@app.route('/')
def home():
    return "SERVER RUNNING | Open /admin to access panel"

# CREATE CUSTOM ACTIVATION API
@app.route('/api/admin/create-custom', methods=['POST'])
def api_create_custom():
    data = request.get_json()
    if data.get("admin_key") != ADMIN_KEY:
        return jsonify({"error": "unauthorized"}), 403

    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    license_key = data.get("license", "").strip()
    hours = int(data.get("hours", 168))

    # Check duplicates
    if license_key in CUSTOM_LICENSES or license_key in LICENSES:
        return jsonify({"error": "exists"}), 400
    if username in CUSTOM_USERS or username in VALID_USERS:
        return jsonify({"error": "exists"}), 400

    # Save custom license
    CUSTOM_LICENSES[license_key] = {
        "hwid": "",
        "duration_hours": hours,
        "start_time": None,
        "expires_at": None,
        "activated_at": None
    }

    # Save custom user
    CUSTOM_USERS[username] = {
        "password": password,
        "linked_license": license_key
    }

    save_data()
    return jsonify({"success": True}), 200
# GET ALL ACTIVATIONS API
@app.route('/api/admin/get-all', methods=['POST'])
def api_get_all():
    data = request.get_json()
    if data.get("admin_key") != ADMIN_KEY:
        return jsonify({"error": "unauthorized"}), 403

    now = datetime.utcnow()
    result_list = []

    # Add permanent licenses
    for key, lic in LICENSES.items():
        result_list.append({
            "username": "PERMANENT",
            "license": key,
            "hours": "UNLIMITED",
            "status": "PERMANENT",
            "remaining": "FOREVER"
        })

    # Add custom/licenses
    for key, lic in CUSTOM_LICENSES.items():
        # Find linked username
        linked_user = "UNKNOWN"
        for u, ud in CUSTOM_USERS.items():
            if ud["linked_license"] == key:
                linked_user = u

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


# DELETE ACTIVATION API
@app.route('/api/admin/delete', methods=['POST'])
def api_delete():
    data = request.get_json()
    if data.get("admin_key") != ADMIN_KEY:
        return jsonify({"error": "unauthorized"}), 403

    license_key = data.get("license", "").strip()

    if license_key in CUSTOM_LICENSES:
        # Delete linked user first
        for user, user_data in list(CUSTOM_USERS.items()):
            if user_data["linked_license"] == license_key:
                del CUSTOM_USERS[user]
        # Delete license
        del CUSTOM_LICENSES[license_key]
        save_data()
        return jsonify({"success": True}), 200

    return jsonify({"error": "not_found"}), 404


# ==================================================
# 🔑 ACTIVATE & VERIFY SYSTEM — FULLY WORKING
# ==================================================
@app.route('/api/activate', methods=['POST'])
def activate():
    data = request.get_json()
    key = data.get("license_key", "").strip()
    hwid = data.get("hardware_id", "").strip()
    now = datetime.utcnow()

    # --- CHECK PERMANENT LICENSES ---
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

    # --- CHECK CUSTOM / TRIAL LICENSES ---
    if key in CUSTOM_LICENSES:
        lic = CUSTOM_LICENSES[key]
        if lic["start_time"] is None:
            # First activation: start timer
            lic["start_time"] = now.isoformat()
            lic["activated_at"] = now.isoformat()
            lic["expires_at"] = (now + timedelta(hours=lic["duration_hours"])).isoformat()
            lic["hwid"] = hwid
            save_data()
            print("TRIAL CREATED")
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

    # If license not found anywhere
    return jsonify({"status": "invalid", "msg": "License key does not exist"}), 403


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

    # Verify custom/licenses
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


@app.route('/api/validate-user', methods=['POST'])
def validate_user():
    username = request.get_json().get("username", "")
    if username in VALID_USERS or username in CUSTOM_USERS:
        return jsonify({"ok": True}), 200
    return "", 403


@app.route('/api/check-password', methods=['POST'])
def check_pass():
    data = request.get_json()
    username = data.get("username", "")
    password = data.get("password", "")
    
    # Check permanent users
    if username in VALID_USERS and VALID_USERS[username] == password:
        return jsonify({"ok": True}), 200
    
    # Check custom users
    if username in CUSTOM_USERS and CUSTOM_USERS[username]["password"] == password:
        return jsonify({"ok": True}), 200

    return "", 403


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
    <input type="password" id="password-input" placeholder="Enter code..." autocomplete="off">
    <button class="btn-primary" onclick="checkLogin()">LOGIN</button>
    <p id="error-msg" style="color: #ef4444; display: none;">Wrong code! Try again.</p>
</div>
<div id="panel" class="panel-box">
    <h1>⚡ JEPFX ADMIN PANEL</h1>
    <div class="tabs">
        <div class="tab active" onclick="showTab('create')">CREATE CUSTOM</div>
        <div class="tab" onclick="showTab('list')">VIEW ALL</div>
    </div>

    <!-- 🆕 CREATE CUSTOM ACTIVATION TAB -->
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
        <button class="btn-primary" onclick="makeCustom()">✅ CREATE NOW</button>
        
        <div id="output" class="result" style="display: none;"></div>
    </div>

    <!-- 📋 VIEW ALL ACTIVATIONS TAB -->
    <div id="list" class="content">
        <h3>All Created Activations</h3>
        <button class="btn-primary" onclick="loadAll()">🔄 REFRESH</button>
        <table id="data-table">
            <tr>
                <th>USERNAME</th>
                <th>LICENSE KEY</th>
                <th>HOURS</th>
                <th>STATUS</th>
                <th>REMAINING TIME</th>
                <th>ACTION</th>
            </tr>
        </table>
    </div>
</div>

<script>
    const SERVER_URL = window.location.origin;
    const ADMIN_KEY = "{{ admin_key }}";

    // Login check
    function checkLogin() {
        const code = document.getElementById('password-input').value;
        fetch(SERVER_URL + '/api/admin/check-pass', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({code: code})
        })
        .then(res => res.json())
        .then(data => {
            if(data.ok) {
                document.getElementById('login-screen').style.display = 'none';
                document.getElementById('panel').classList.add('active');
            } else {
                document.getElementById('error-msg').style.display = 'block';
            }
        });
    }

    // Switch tabs
    function showTab(tabName) {
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.content').forEach(c => c.classList.remove('active'));
        document.querySelector(`.tab[onclick="showTab('${tabName}')"]`).classList.add('active');
        document.getElementById(tabName).classList.add('active');
        if(tabName === 'list') loadAll();
    }

    // 🆕 Create custom activation
    async function makeCustom() {
        const user = document.getElementById('cust_user').value.trim();
        const pass = document.getElementById('cust_pass').value.trim();
        const lic = document.getElementById('cust_license').value.trim();
        const hrs = parseInt(document.getElementById('cust_hours').value);

        if(!user || !pass || !lic || !hrs) return alert("❌ Fill all fields!");

        const res = await fetch(SERVER_URL + '/api/admin/create-custom', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                admin_key: ADMIN_KEY,
                username: user,
                password: pass,
                license: lic,
                hours: hrs
            })
        });
        const data = await res.json();
        document.getElementById('output').style.display = 'block';
        if(res.ok) {
            document.getElementById('output').innerHTML = `
✅ SUCCESSFULLY CREATED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👤 USERNAME : ${user}
🔒 PASSWORD : ${pass}
🔑 LICENSE  : ${lic}
⏱️ DURATION : ${hrs} HOURS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ READY TO USE!
            `;
            loadAll();
        } else {
            document.getElementById('output').innerHTML = '❌ ERROR: Username or License already exists!';
        }
    }

    // 📋 Load all data
    async function loadAll() {
        const res = await fetch(SERVER_URL + '/api/admin/get-all', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({admin_key: ADMIN_KEY})
        });
        const data = await res.json();
        const table = document.getElementById('data-table');
        table.innerHTML = `<tr><th>USERNAME</th><th>LICENSE KEY</th><th>HOURS</th><th>STATUS</th><th>REMAINING TIME</th><th>ACTION</th></tr>`;
        
        data.list.forEach(item => {
            const row = table.insertRow(-1);
            row.innerHTML = `
                <td>${item.username}</td>
                <td>${item.license}</td>
                <td>${item.hours}</td>
                <td>${item.status}</td>
                <td>${item.remaining}</td>
                <td><button class="btn-danger" onclick="deleteItem('${item.license}')">DELETE</button></td>
            `;
        });
    }

    // 🗑️ Delete item
    async function deleteItem(license) {
        if(!confirm('Delete this activation?')) return;
        await fetch(SERVER_URL + '/api/admin/delete', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({admin_key: ADMIN_KEY, license: license})
        });
        loadAll();
    }
</script>
</body></html>
"""

# ==================================================
# 🔐 ADMIN API ROUTES
# ==================================================
@app.route('/api/admin/check-pass', methods=['POST'])
def api_check_pass():
    return jsonify({"ok": request.get_json().get("code") == ADMIN_PASSWORD}), 200

@app.route('/admin')
def admin_page():
    return render_template_string(ADMIN_HTML.replace("{{ admin_key }}", ADMIN_KEY))

@app.route('/')
def home():
    return "✅ SERVER RUNNING | Open /admin to access panel"
# 📋 GET ALL ACTIVATIONS API
@app.route('/api/admin/get-all', methods=['POST'])
def api_get_all():
    data = request.get_json()
    if data.get("admin_key") != ADMIN_KEY:
        return jsonify({"error": "unauthorized"}), 403

    now = datetime.utcnow()
    result_list = []

    # Add permanent licenses
    for key, lic in LICENSES.items():
        result_list.append({
            "username": "PERMANENT",
            "license": key,
            "hours": "UNLIMITED",
            "status": "✅ PERMANENT",
            "remaining": "FOREVER"
        })

    # Add custom/licenses
    for key, lic in CUSTOM_LICENSES.items():
        # Find linked username
        linked_user = "UNKNOWN"
        for u, ud in CUSTOM_USERS.items():
            if ud["linked_license"] == key:
                linked_user = u

        status = "NOT ACTIVATED"
        remaining = "-"

        if lic["expires_at"]:
            exp_time = datetime.fromisoformat(str(lic["expires_at"]))
            if now > exp_time:
                status = "❌ EXPIRED"
                remaining = "EXPIRED"
            else:
                status = "✅ ACTIVE"
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


# 🗑️ DELETE ACTIVATION API
@app.route('/api/admin/delete', methods=['POST'])
def api_delete():
    data = request.get_json()
    if data.get("admin_key") != ADMIN_KEY:
        return jsonify({"error": "unauthorized"}), 403

    license_key = data.get("license", "").strip()

    if license_key in CUSTOM_LICENSES:
        # Delete linked user first
        for user, user_data in list(CUSTOM_USERS.items()):
            if user_data["linked_license"] == license_key:
                del CUSTOM_USERS[user]
        # Delete license
        del CUSTOM_LICENSES[license_key]
        save_data()
        return jsonify({"success": True}), 200

    return jsonify({"error": "not_found"}), 404


# ==================================================
# 🔑 ACTIVATE & VERIFY SYSTEM — FULLY WORKING
# ==================================================
@app.route('/api/activate', methods=['POST'])
def activate():
    data = request.get_json()
    key = data.get("license_key", "").strip()
    hwid = data.get("hardware_id", "").strip()
    now = datetime.utcnow()

    # --- CHECK PERMANENT LICENSES ---
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

    # --- CHECK CUSTOM / TRIAL LICENSES ---
    if key in CUSTOM_LICENSES:
        lic = CUSTOM_LICENSES[key]
        if lic["start_time"] is None:
            # First activation: start timer
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

    # If license not found anywhere
    return jsonify({"status": "invalid", "msg": "License key does not exist"}), 403


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

    # Verify custom/licenses
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


@app.route('/api/validate-user', methods=['POST'])
def validate_user():
    username = request.get_json().get("username", "")
    if username in VALID_USERS or username in CUSTOM_USERS:
        return jsonify({"ok": True}), 200
    return "", 403


@app.route('/api/check-password', methods=['POST'])
def check_pass():
    data = request.get_json()
    username = data.get("username", "")
    password = data.get("password", "")
    
    # Check permanent users
    if username in VALID_USERS and VALID_USERS[username] == password:
        return jsonify({"ok": True}), 200
    
    # Check custom users
    if username in CUSTOM_USERS and CUSTOM_USERS[username]["password"] == password:
        return jsonify({"ok": True}), 200

    return "", 403


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
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
ADMIN_PASSWORD = "YOUR_SECRET_CODE_HERE"  # ✅ CHANGE THIS!
ADMIN_KEY = "JEPFX-ADMIN-2026"

# ==================================================
# 📝 LICENSES & USERS STORAGE
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
    "N4XCO": "N4XCO_0"
}

# This will store ALL custom activations
CUSTOM_LICENSES = {}
CUSTOM_USERS = {}

# ==================================================
# 💾 SAVE / LOAD DATA FUNCTIONS
# ==================================================
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
        print("📄 NO DATA FILE — CREATING NEW")
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

# Load saved data when server starts
load_data()

# ==================================================
# 🎨 ADMIN PANEL HTML — FULLY CUSTOMIZABLE
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
        .note { color: #aaa; font-size: 14px; margin: -8px 0 10px 0; }
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
        <div class="tab active" onclick="showTab('create')">CREATE CUSTOM</div>
        <div class="tab" onclick="showTab('list')">VIEW ALL</div>
    </div>

    <!-- 🆕 CREATE CUSTOM ACTIVATION TAB -->
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
        <button class="btn-primary" onclick="makeCustom()">✅ CREATE NOW</button>
        
        <div id="output" class="result" style="display: none;"></div>
    </div>

    <!-- 📋 VIEW ALL ACTIVATIONS TAB -->
    <div id="list" class="content">
        <h3>All Created Activations</h3>
        <button class="btn-primary" onclick="loadAll()">🔄 REFRESH</button>
        <table id="data-table">
            <tr>
                <th>USERNAME</th>
                <th>LICENSE KEY</th>
                <th>HOURS</th>
                <th>STATUS</th>
                <th>REMAINING TIME</th>
                <th>ACTION</th>
            </tr>
        </table>
    </div>
</div>

<script>
    const SERVER_URL = window.location.origin;
    const ADMIN_KEY = "{{ admin_key }}";

    // Login check
    function checkLogin() {
        const code = document.getElementById('password-input').value;
        fetch(SERVER_URL + '/api/admin/check-pass', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({code: code})
        })
        .then(res => res.json())
        .then(data => {
            if(data.ok) {
                document.getElementById('login-screen').style.display = 'none';
                document.getElementById('panel').classList.add('active');
            } else {
                document.getElementById('error-msg').style.display = 'block';
            }
        });
    }

    // Switch tabs
    function showTab(tabName) {
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.content').forEach(c => c.classList.remove('active'));
        document.querySelector(`.tab[onclick="showTab('${tabName}')"]`).classList.add('active');
        document.getElementById(tabName).classList.add('active');
        if(tabName === 'list') loadAll();
    }

    // 🆕 Create custom activation
    async function makeCustom() {
        const user = document.getElementById('cust_user').value.trim();
        const pass = document.getElementById('cust_pass').value.trim();
        const lic = document.getElementById('cust_license').value.trim();
        const hrs = parseInt(document.getElementById('cust_hours').value);

        if(!user || !pass || !lic || !hrs) return alert("❌ Fill all fields!");

        const res = await fetch(SERVER_URL + '/api/admin/create-custom', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                admin_key: ADMIN_KEY,
                username: user,
                password: pass,
                license: lic,
                hours: hrs
            })
        });
        const data = await res.json();
        document.getElementById('output').style.display = 'block';
        if(res.ok) {
            document.getElementById('output').innerHTML = `
✅ SUCCESSFULLY CREATED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👤 USERNAME : ${user}
🔒 PASSWORD : ${pass}
🔑 LICENSE  : ${lic}
⏱️ DURATION : ${hrs} HOURS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ READY TO USE!
            `;
            loadAll();
        } else {
            document.getElementById('output').innerHTML = '❌ ERROR: Username or License already exists!';
        }
    }

    // 📋 Load all data
    async function loadAll() {
        const res = await fetch(SERVER_URL + '/api/admin/get-all', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({admin_key: ADMIN_KEY})
        });
        const data = await res.json();
        const table = document.getElementById('data-table');
        table.innerHTML = `<tr><th>USERNAME</th><th>LICENSE KEY</th><th>HOURS</th><th>STATUS</th><th>REMAINING TIME</th><th>ACTION</th></tr>`;
        
        data.list.forEach(item => {
            const row = table.insertRow(-1);
            row.innerHTML = `
                <td>${item.username}</td>
                <td>${item.license}</td>
                <td>${item.hours}</td>
                <td>${item.status}</td>
                <td>${item.remaining}</td>
                <td><button class="btn-danger" onclick="deleteItem('${item.license}')">DELETE</button></td>
            `;
        });
    }

    // 🗑️ Delete item
    async function deleteItem(license) {
        if(!confirm('Delete this activation?')) return;
        await fetch(SERVER_URL + '/api/admin/delete', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({admin_key: ADMIN_KEY, license: license})
        });
        loadAll();
    }
</script>
</body></html>
"""

# ==================================================
# 🔐 ADMIN API ROUTES
# ==================================================
@app.route('/api/admin/check-pass', methods=['POST'])
def api_check_pass():
    return jsonify({"ok": request.get_json().get("code") == ADMIN_PASSWORD}), 200

@app.route('/admin')
def admin_page():
    return render_template_string(ADMIN_HTML.replace("{{ admin_key }}", ADMIN_KEY))

@app.route('/')
def home():
    return "✅ SERVER RUNNING | Open /admin to access panel"
# 📋 GET ALL ACTIVATIONS API
@app.route('/api/admin/get-all', methods=['POST'])
def api_get_all():
    data = request.get_json()
    if data.get("admin_key") != ADMIN_KEY:
        return jsonify({"error": "unauthorized"}), 403

    now = datetime.utcnow()
    result_list = []

    # Add permanent licenses
    for key, lic in LICENSES.items():
        result_list.append({
            "username": "PERMANENT",
            "license": key,
            "hours": "UNLIMITED",
            "status": "PERMANENT",
            "remaining": "FOREVER"
        })

    # Add custom/licenses
    for key, lic in CUSTOM_LICENSES.items():
        # Find linked username
        linked_user = "UNKNOWN"
        for u, ud in CUSTOM_USERS.items():
            if ud["linked_license"] == key:
                linked_user = u

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


# 🗑️ DELETE ACTIVATION API
@app.route('/api/admin/delete', methods=['POST'])
def api_delete():
    data = request.get_json()
    if data.get("admin_key") != ADMIN_KEY:
        return jsonify({"error": "unauthorized"}), 403

    license_key = data.get("license", "").strip()

    if license_key in CUSTOM_LICENSES:
        # Delete linked user first
        for user, user_data in list(CUSTOM_USERS.items()):
            if user_data["linked_license"] == license_key:
                del CUSTOM_USERS[user]
        # Delete license
        del CUSTOM_LICENSES[license_key]
        save_data()
        return jsonify({"success": True}), 200

    return jsonify({"error": "not_found"}), 404


# ==================================================
# 🔑 ACTIVATE & VERIFY SYSTEM — FULLY WORKING
# ==================================================
@app.route('/api/activate', methods=['POST'])
def activate():
    data = request.get_json()
    key = data.get("license_key", "").strip()
    hwid = data.get("hardware_id", "").strip()
    now = datetime.utcnow()

    # --- CHECK PERMANENT LICENSES ---
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

    # --- CHECK CUSTOM / TRIAL LICENSES ---
    if key in CUSTOM_LICENSES:
        lic = CUSTOM_LICENSES[key]
        if lic["start_time"] is None:
            # First activation: start timer
            lic["start_time"] = now.isoformat()
            lic["activated_at"] = now.isoformat()
            lic["expires_at"] = (now + timedelta(hours=lic["duration_hours"])).isoformat()
            lic["hwid"] = hwid
            save_data()
            print("TRIAL CREATED")
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

    # If license not found anywhere
    return jsonify({"status": "invalid", "msg": "License key does not exist"}), 403


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

    # Verify custom/licenses
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


@app.route('/api/validate-user', methods=['POST'])
def validate_user():
    username = request.get_json().get("username", "")
    if username in VALID_USERS or username in CUSTOM_USERS:
        return jsonify({"ok": True}), 200
    return "", 403


@app.route('/api/check-password', methods=['POST'])
def check_pass():
    data = request.get_json()
    username = data.get("username", "")
    password = data.get("password", "")
    
    # Check permanent users
    if username in VALID_USERS and VALID_USERS[username] == password:
        return jsonify({"ok": True}), 200
    
    # Check custom users
    if username in CUSTOM_USERS and CUSTOM_USERS[username]["password"] == password:
        return jsonify({"ok": True}), 200

    return "", 403


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
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
