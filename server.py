from flask import Flask, request, jsonify, render_template_string, Response
import hashlib
from datetime import datetime, timedelta
import uuid
import json
import os
import threading
import time
import secrets

app = Flask(__name__)

# ==================================================
# 📂 PERMANENT DATA SAVE
# ==================================================
DATA_FILE = "server_data.json"

# ==================================================
# 🔐 ADMIN SETTINGS
# ==================================================
MASTER_ADMIN = {
    "username": "JEPFX",
    "password": "JEPFXADMIN",
    "role": "master",
    "credits": 999999,
    "created_at": None
}

ADMINS = {}  # Will be loaded from JSON
MODERATORS = {}  # Will be loaded from JSON

# ==================================================
# 📝 LICENSES & USERS (Now with owner tracking)
# ==================================================
PERMANENT_LICENSES = {}
CUSTOM_ACTIVATIONS = {}
TRIAL_LICENSES = {}
TRIAL_USERS = {}
USAGE_LOGS = {}

# Each license now has an "owner" field to track who created it
# Example: TRIAL_LICENSES[key] = {"owner": "admin_username", ...}

VALID_USERS = {
    "JEPFX": "@JEPFX_1875",
}

# ==================================================
# 💰 CREDIT PRICING SYSTEM
# ==================================================
CREDIT_PRICING = {
    "trial_hour": 0.1,  # 0.1 credit per hour
    "custom_hour": 0.1,
    "custom_day": 1,
    "custom_week": 5,
    "custom_month": 10,
    "custom_year": 30,
    "custom_unlimited": 50,
    "permanent": 50
}

# ==================================================
# 💾 SAVE / LOAD DATA
# ==================================================
def load_data():
    global TRIAL_LICENSES, TRIAL_USERS, PERMANENT_LICENSES, CUSTOM_ACTIVATIONS, USAGE_LOGS, ADMINS, MODERATORS, VALID_USERS
    
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
                TRIAL_LICENSES = data.get("trials", {})
                TRIAL_USERS = data.get("users", {})
                PERMANENT_LICENSES = data.get("permanent_licenses", {})
                CUSTOM_ACTIVATIONS = data.get("custom_activations", {})
                USAGE_LOGS = data.get("usage_logs", {})
                ADMINS = data.get("admins", {})
                MODERATORS = data.get("moderators", {})
                VALID_USERS.update(data.get("valid_users", {}))
            print("✅ DATA LOADED SUCCESSFULLY")
        except Exception as e:
            print(f"⚠️ LOAD ERROR: {e}")
            reset_data()
    else:
        reset_data()

def reset_data():
    global TRIAL_LICENSES, TRIAL_USERS, PERMANENT_LICENSES, CUSTOM_ACTIVATIONS, USAGE_LOGS, ADMINS, MODERATORS
    TRIAL_LICENSES = {}
    TRIAL_USERS = {}
    PERMANENT_LICENSES = {}
    CUSTOM_ACTIVATIONS = {}
    USAGE_LOGS = {}
    ADMINS = {}
    MODERATORS = {}
    save_data()

def save_data():
    data = {
        "trials": TRIAL_LICENSES,
        "users": TRIAL_USERS,
        "permanent_licenses": PERMANENT_LICENSES,
        "custom_activations": CUSTOM_ACTIVATIONS,
        "usage_logs": USAGE_LOGS,
        "admins": ADMINS,
        "moderators": MODERATORS,
        "valid_users": VALID_USERS
    }
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=2, default=str)
        print("💾 DATA SAVED SUCCESSFULLY")
    except Exception as e:
        print(f"❌ SAVE ERROR: {e}")

load_data()

# ==================================================
# 📊 USAGE TRACKING
# ==================================================
def log_usage(license_key, event_type, details=None):
    if license_key not in USAGE_LOGS:
        USAGE_LOGS[license_key] = []
    
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "event_type": event_type,
        "details": details or {}
    }
    
    USAGE_LOGS[license_key].append(log_entry)
    
    if len(USAGE_LOGS[license_key]) > 1000:
        USAGE_LOGS[license_key] = USAGE_LOGS[license_key][-1000:]
    
    save_data()

def get_usage_stats(license_key):
    logs = USAGE_LOGS.get(license_key, [])
    
    stats = {
        "total_usage": len(logs),
        "total_activations": sum(1 for l in logs if l["event_type"] == "activation"),
        "total_verifications": sum(1 for l in logs if l["event_type"] == "verification"),
        "total_logins": sum(1 for l in logs if l["event_type"] == "login"),
        "last_used": logs[-1]["timestamp"] if logs else None,
        "unique_hwids": list(set(l["details"].get("hwid") for l in logs if "hwid" in l["details"]))
    }
    return stats

def check_admin_auth(data):
    """Check if user is admin or moderator"""
    username = data.get("admin_username", "")
    password = data.get("admin_password", "")
    
    # Check master admin
    if username == MASTER_ADMIN["username"] and password == MASTER_ADMIN["password"]:
        return {"authorized": True, "role": "master", "username": username}
    
    # Check admins
    if username in ADMINS and ADMINS[username]["password"] == password:
        return {"authorized": True, "role": "admin", "username": username, "credits": ADMINS[username]["credits"]}
    
    # Check moderators
    if username in MODERATORS and MODERATORS[username]["password"] == password:
        return {"authorized": True, "role": "moderator", "username": username, "credits": MODERATORS[username]["credits"]}
    
    return {"authorized": False}

def deduct_credits(username, amount):
    """Deduct credits from admin/moderator account (supports decimals)"""
    if username == MASTER_ADMIN["username"]:
        return True
    
    if username in ADMINS:
        if ADMINS[username]["credits"] >= amount:
            ADMINS[username]["credits"] = round(ADMINS[username]["credits"] - amount, 2)
            save_data()
            return True
        return False
    
    if username in MODERATORS:
        if MODERATORS[username]["credits"] >= amount:
            MODERATORS[username]["credits"] = round(MODERATORS[username]["credits"] - amount, 2)
            save_data()
            return True
        return False
    
    return False

def add_credits(username, amount):
    """Add credits to admin/moderator account"""
    if username in ADMINS:
        ADMINS[username]["credits"] = round(ADMINS[username]["credits"] + amount, 2)
        save_data()
        return True
    if username in MODERATORS:
        MODERATORS[username]["credits"] = round(MODERATORS[username]["credits"] + amount, 2)
        save_data()
        return True
    return False

def get_credits(username):
    if username == MASTER_ADMIN["username"]:
        return "Unlimited"
    if username in ADMINS:
        return ADMINS[username]["credits"]
    if username in MODERATORS:
        return MODERATORS[username]["credits"]
    return 0

def get_licenses_by_owner(owner, role):
    """Get licenses filtered by owner"""
    if role == "master":
        # Master sees everything
        return {
            "trials": TRIAL_LICENSES,
            "custom": CUSTOM_ACTIVATIONS,
            "permanent": PERMANENT_LICENSES
        }
    else:
        # Filter by owner
        filtered_trials = {k: v for k, v in TRIAL_LICENSES.items() if v.get("owner") == owner}
        filtered_custom = {k: v for k, v in CUSTOM_ACTIVATIONS.items() if v.get("owner") == owner}
        filtered_permanent = {k: v for k, v in PERMANENT_LICENSES.items() if v.get("owner") == owner}
        return {
            "trials": filtered_trials,
            "custom": filtered_custom,
            "permanent": filtered_permanent
        }

# ==================================================
# 🔍 MONITORING THREAD
# ==================================================
def monitor_expired_licenses():
    while True:
        try:
            now = datetime.utcnow()
            changes_made = False
            
            for key, activation in list(CUSTOM_ACTIVATIONS.items()):
                if activation.get("expires_at"):
                    exp_time = datetime.fromisoformat(activation["expires_at"])
                    if now > exp_time:
                        del CUSTOM_ACTIVATIONS[key]
                        changes_made = True
            
            for key, lic in list(PERMANENT_LICENSES.items()):
                if lic.get("expires_at"):
                    exp_time = datetime.fromisoformat(lic["expires_at"])
                    if now > exp_time:
                        del PERMANENT_LICENSES[key]
                        changes_made = True
            
            if changes_made:
                save_data()
        except Exception as e:
            print(f"⚠️ Monitor error: {e}")
        time.sleep(60)

monitor_thread = threading.Thread(target=monitor_expired_licenses, daemon=True)
monitor_thread.start()

# ==================================================
# 🎨 ADMIN PANEL HTML (Separate Dashboards)
# ==================================================
ADMIN_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>JEPFX ADMIN PANEL</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Segoe UI', Arial, sans-serif; }
        body { background: linear-gradient(135deg, #0f0c29, #302b63, #24243e); min-height: 100vh; padding: 20px; }
        .container { max-width: 1400px; margin: 0 auto; }
        
        .login-box { max-width: 400px; margin: 100px auto; background: rgba(255,255,255,0.1); backdrop-filter: blur(10px); padding: 30px; border-radius: 15px; text-align: center; }
        .login-box input { width: 100%; padding: 12px; margin: 10px 0; border: none; border-radius: 8px; background: rgba(255,255,255,0.2); color: white; }
        .login-box button { background: #7C3AED; color: white; padding: 12px 30px; border: none; border-radius: 8px; cursor: pointer; }
        
        .panel { display: none; }
        .header { background: rgba(255,255,255,0.1); border-radius: 15px; padding: 20px; margin-bottom: 20px; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 15px; margin-bottom: 20px; }
        .stat-card { background: rgba(124,58,237,0.2); padding: 15px; border-radius: 10px; text-align: center; cursor: pointer; }
        .stat-number { font-size: 28px; font-weight: bold; color: #7C3AED; }
        
        .tabs { display: flex; gap: 5px; flex-wrap: wrap; margin-bottom: 20px; }
        .tab { background: rgba(255,255,255,0.1); padding: 12px 20px; border-radius: 8px; cursor: pointer; border: none; color: white; }
        .tab.active { background: #7C3AED; }
        
        .content { display: none; background: rgba(255,255,255,0.05); border-radius: 15px; padding: 25px; }
        .content.active { display: block; }
        
        input, select, textarea { width: 100%; padding: 12px; margin: 10px 0; border: 1px solid rgba(255,255,255,0.2); border-radius: 8px; background: rgba(0,0,0,0.3); color: white; }
        button { background: #7C3AED; color: white; padding: 10px 20px; border: none; border-radius: 8px; cursor: pointer; margin: 5px; }
        .btn-danger { background: #DC2626; }
        .btn-success { background: #10B981; }
        
        table { width: 100%; border-collapse: collapse; margin-top: 20px; display: block; overflow-x: auto; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid rgba(255,255,255,0.1); }
        th { background: rgba(124,58,237,0.3); }
        tr:hover { background: rgba(255,255,255,0.05); cursor: pointer; }
        
        .result-box { background: rgba(0,0,0,0.5); padding: 20px; border-radius: 10px; margin-top: 20px; border-left: 3px solid #7C3AED; }
        .modal { display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); }
        .modal-content { background: #1a1a2e; margin: 5% auto; padding: 25px; border-radius: 15px; width: 90%; max-width: 600px; }
        .close { float: right; font-size: 28px; cursor: pointer; }
        .credit-badge { background: #10B981; padding: 5px 10px; border-radius: 20px; font-size: 12px; margin-left: 10px; }
        .master-only { background: rgba(239,68,68,0.2); border-left: 3px solid #EF4444; padding: 10px; margin: 10px 0; border-radius: 5px; }
        .owner-tag { font-size: 11px; color: #aaa; margin-left: 5px; }
    </style>
</head>
<body>
<div class="container">
    <!-- Login -->
    <div id="loginScreen" class="login-box">
        <h2>🔒 JEPFX ADMIN LOGIN</h2>
        <input type="text" id="loginUsername" placeholder="Username">
        <input type="password" id="loginPassword" placeholder="Password">
        <button onclick="login()">LOGIN</button>
        <p id="loginError" style="color: #EF4444; display: none; margin-top: 10px;">Invalid credentials!</p>
    </div>
    
    <!-- Main Panel -->
    <div id="mainPanel" class="panel">
        <div class="header">
            <h1>⚡ JEPFX ADMIN PANEL</h1>
            <p>Welcome, <span id="currentUser">-</span> | Role: <span id="currentRole">-</span> | Credits: <span id="currentCredits">0</span></p>
            <div id="masterBadge" style="display: none;" class="master-only">👑 Master Admin - You can see all licenses from all admins</div>
        </div>
        
        <div class="stats-grid" id="statsGrid">
            <div class="stat-card"><div class="stat-number" id="statTrials">0</div><div>My Trials</div></div>
            <div class="stat-card"><div class="stat-number" id="statCustom">0</div><div>My Custom</div></div>
            <div class="stat-card"><div class="stat-number" id="statPermanent">0</div><div>My Permanent</div></div>
            <div class="stat-card"><div class="stat-number" id="statUsage">0</div><div>API Calls</div></div>
        </div>
        
        <div class="tabs">
            <button class="tab active" onclick="switchTab('generateTrial')">🎲 CREATE TRIAL</button>
            <button class="tab" onclick="switchTab('customActivation')">✨ CUSTOM ACTIVATOR</button>
            <button class="tab" onclick="switchTab('permanentLicense')">🔑 PERMANENT</button>
            <button class="tab" onclick="switchTab('myLicenses')">📋 MY LICENSES</button>
            <div id="adminTab" style="display: none;"><button class="tab" onclick="switchTab('admins')">👨‍💼 MANAGE ADMINS</button></div>
            <button class="tab" onclick="switchTab('changePassword')">🔐 CHANGE PASSWORD</button>
            <button class="tab" onclick="switchTab('monitor')">📈 MONITOR</button>
        </div>
        
        <!-- Tab: Generate Trial -->
        <div id="generateTrial" class="content active">
            <h2>🎲 Generate Trial License</h2>
            <select id="trialDuration">
                <option value="3">3 Hours (0.3 credits)</option>
                <option value="6">6 Hours (0.6 credits)</option>
                <option value="12">12 Hours (1.2 credits)</option>
                <option value="24">1 Day (1 credit)</option>
                <option value="72">3 Days (3 credits)</option>
                <option value="168">1 Week (5 credits)</option>
                <option value="720">1 Month (10 credits)</option>
            </select>
            <button onclick="generateTrial()">GENERATE LICENSE</button>
            <div class="result-box" style="margin-top: 10px; font-size: 12px;">
                💡 <strong>Pricing:</strong> 0.1 credits/hour • Max 10 credits/month
            </div>
            <div id="trialResult" class="result-box" style="display: none;"></div>
        </div>
        
        <!-- Tab: Custom Activation -->
        <div id="customActivation" class="content">
            <h2>✨ Custom Activation (Multi-PC Supported)</h2>
            <input type="text" id="customUsername" placeholder="Username">
            <input type="text" id="customPassword" placeholder="Password">
            <input type="text" id="customLicense" placeholder="License Key">
            <select id="customDurationType">
                <option value="hours">Hours (0.1 credits/hour)</option>
                <option value="days">Days (1 credit/day)</option>
                <option value="weeks">Weeks (5 credits/week)</option>
                <option value="months">Months (10 credits/month)</option>
                <option value="years">Years (30 credits/year)</option>
                <option value="unlimited">Unlimited (50 credits)</option>
            </select>
            <input type="number" id="customDurationValue" placeholder="Duration value" step="0.5">
            <button onclick="createCustomActivation()">CREATE ACTIVATION</button>
            <div class="result-box" style="margin-top: 10px; font-size: 12px;">
                💡 <strong>Pricing:</strong> Hour:0.1 | Day:1 | Week:5 | Month:10 | Year:30 | Unlimited:50<br>
                🎮 <strong>Multi-PC:</strong> Supports unlimited devices simultaneously!
            </div>
            <div id="customResult" class="result-box" style="display: none;"></div>
        </div>
        
        <!-- Tab: Permanent License -->
        <div id="permanentLicense" class="content">
            <h2>🔑 Permanent License (50 Credits)</h2>
            <input type="text" id="permLicenseKey" placeholder="License Key">
            <input type="text" id="permUsername" placeholder="Username (optional)">
            <input type="text" id="permPassword" placeholder="Password (optional)">
            <button onclick="createPermanentLicense()">CREATE PERMANENT (50 CREDITS)</button>
            <div class="result-box" style="margin-top: 10px; font-size: 12px;">
                💡 Permanent license never expires and supports unlimited devices!
            </div>
            <div id="permResult" class="result-box" style="display: none;"></div>
        </div>
        
        <!-- Tab: My Licenses (Shows only licenses created by this admin) -->
        <div id="myLicenses" class="content">
            <h2>📋 My Created Licenses</h2>
            <div class="tabs" style="margin-bottom: 10px;">
                <button class="tab" onclick="showLicenseType('trials')">Trial Licenses</button>
                <button class="tab" onclick="showLicenseType('custom')">Custom Activations</button>
                <button class="tab" onclick="showLicenseType('permanent')">Permanent Licenses</button>
            </div>
            <div id="myTrialsList"></div>
            <div id="myCustomList" style="display: none;"></div>
            <div id="myPermanentList" style="display: none;"></div>
        </div>
        
        <!-- Tab: Admins Management (Master Only) -->
        <div id="admins" class="content">
            <div class="master-only">
                <h2>👑 MASTER ADMIN ONLY</h2>
                <p>You have access to all licenses and can manage other admins</p>
            </div>
            
            <h3>➕ Add New Admin/Moderator</h3>
            <input type="text" id="newAdminUser" placeholder="Username">
            <input type="password" id="newAdminPass" placeholder="Password">
            <select id="newAdminRole">
                <option value="admin">Admin (Can create licenses, uses credits)</option>
                <option value="moderator">Moderator (Limited access, uses credits)</option>
            </select>
            <input type="number" id="newAdminCredits" placeholder="Initial Credits" value="100" step="0.5">
            <button onclick="addAdmin()">ADD USER</button>
            
            <h3>📋 All Admins</h3>
            <div id="adminsList"></div>
            
            <h3>📋 All Moderators</h3>
            <div id="moderatorsList"></div>
            
            <h3>💰 Credit Management</h3>
            <input type="text" id="creditUsername" placeholder="Username">
            <input type="number" id="creditAmount" placeholder="Amount (+ or -)" step="0.5">
            <button onclick="manageCredits()">UPDATE CREDITS</button>
            
            <h3>📊 All Licenses (System Wide)</h3>
            <button onclick="loadAllLicenses()">REFRESH ALL LICENSES</button>
            <div id="allLicensesList"></div>
        </div>
        
        <!-- Tab: Change Password -->
        <div id="changePassword" class="content">
            <h2>🔐 Change Your Password</h2>
            <input type="password" id="oldPassword" placeholder="Current Password">
            <input type="password" id="newPassword" placeholder="New Password">
            <input type="password" id="confirmPassword" placeholder="Confirm New Password">
            <button onclick="changePassword()">UPDATE PASSWORD</button>
            <div id="passwordResult" class="result-box" style="display: none;"></div>
        </div>
        
        <!-- Tab: Monitor -->
        <div id="monitor" class="content">
            <h2>📈 My Usage Monitor</h2>
            <button onclick="loadMonitor()">REFRESH</button>
            <div id="monitorData" class="result-box"></div>
        </div>
    </div>
</div>

<!-- Usage Modal -->
<div id="usageModal" class="modal">
    <div class="modal-content">
        <span class="close" onclick="closeModal()">&times;</span>
        <h2 id="modalTitle">Usage Details</h2>
        <div id="modalBody"></div>
    </div>
</div>

<script>
    const API_URL = window.location.origin;
    let currentUser = null;
    let currentRole = null;
    
    async function login() {
        const username = document.getElementById('loginUsername').value;
        const password = document.getElementById('loginPassword').value;
        
        const res = await fetch(API_URL + '/api/admin/login', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({username: username, password: password})
        });
        const data = await res.json();
        
        if(data.success) {
            currentUser = username;
            currentRole = data.role;
            document.getElementById('currentUser').textContent = username;
            document.getElementById('currentRole').textContent = data.role;
            document.getElementById('currentCredits').textContent = data.credits || 'Unlimited';
            
            if(data.role === 'master') {
                document.getElementById('masterBadge').style.display = 'block';
                document.getElementById('adminTab').style.display = 'block';
            }
            
            document.getElementById('loginScreen').style.display = 'none';
            document.getElementById('mainPanel').style.display = 'block';
            loadStats();
            loadMyLicenses();
        } else {
            document.getElementById('loginError').style.display = 'block';
        }
    }
    
    function switchTab(tabId) {
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.content').forEach(c => c.classList.remove('active'));
        event.target.classList.add('active');
        document.getElementById(tabId).classList.add('active');
        
        if(tabId === 'myLicenses') loadMyLicenses();
        if(tabId === 'admins' && currentRole === 'master') {
            loadAdmins();
            loadAllLicenses();
        }
        if(tabId === 'monitor') loadMonitor();
    }
    
    function showLicenseType(type) {
        document.getElementById('myTrialsList').style.display = 'none';
        document.getElementById('myCustomList').style.display = 'none';
        document.getElementById('myPermanentList').style.display = 'none';
        
        if(type === 'trials') document.getElementById('myTrialsList').style.display = 'block';
        if(type === 'custom') document.getElementById('myCustomList').style.display = 'block';
        if(type === 'permanent') document.getElementById('myPermanentList').style.display = 'block';
    }
    
    async function loadStats() {
        const res = await fetch(API_URL + '/api/admin/get-stats', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({admin_username: currentUser, admin_password: document.getElementById('loginPassword').value})
        });
        const data = await res.json();
        if(data.success) {
            document.getElementById('statTrials').textContent = data.trials;
            document.getElementById('statCustom').textContent = data.custom;
            document.getElementById('statPermanent').textContent = data.permanent;
            document.getElementById('statUsage').textContent = data.total_usage;
            document.getElementById('currentCredits').textContent = data.user_credits || 'Unlimited';
        }
    }
    
    async function generateTrial() {
        const duration = document.getElementById('trialDuration').value;
        const res = await fetch(API_URL + '/api/admin/generate-trial', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                admin_username: currentUser,
                admin_password: document.getElementById('loginPassword').value,
                duration_hours: parseInt(duration)
            })
        });
        const data = await res.json();
        const resultDiv = document.getElementById('trialResult');
        resultDiv.style.display = 'block';
        if(data.success) {
            resultDiv.innerHTML = `✅ TRIAL CREATED!<br>🔑 License: ${data.license_key}<br>👤 User: ${data.username}<br>🔒 Pass: ${data.password}<br>⏱️ Duration: ${duration} hours<br>💰 Credits used: ${data.credits_used}<br>💳 Remaining: ${data.remaining_credits}`;
            loadStats();
            loadMyLicenses();
        } else {
            resultDiv.innerHTML = `❌ ERROR: ${data.error}`;
        }
    }
    
    async function createCustomActivation() {
        const username = document.getElementById('customUsername').value;
        const password = document.getElementById('customPassword').value;
        const license = document.getElementById('customLicense').value;
        const durationType = document.getElementById('customDurationType').value;
        const durationValue = parseFloat(document.getElementById('customDurationValue').value);
        
        if(!username || !password || !license) {
            alert('Please fill all fields!');
            return;
        }
        
        const res = await fetch(API_URL + '/api/admin/create-custom-activation', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                admin_username: currentUser,
                admin_password: document.getElementById('loginPassword').value,
                username: username,
                password: password,
                license_key: license,
                duration_type: durationType,
                duration_value: durationValue
            })
        });
        const data = await res.json();
        const resultDiv = document.getElementById('customResult');
        resultDiv.style.display = 'block';
        if(data.success) {
            resultDiv.innerHTML = `✅ CUSTOM ACTIVATION CREATED!<br>🔑 License: ${license}<br>👤 User: ${username}<br>🔒 Pass: ${password}<br>📅 Expires: ${data.expires_at || 'NEVER'}<br>💰 Credits used: ${data.credits_used}<br>💳 Remaining: ${data.remaining_credits}<br>🎮 MULTI-PC SUPPORT: Unlimited devices!`;
            document.getElementById('customUsername').value = '';
            document.getElementById('customPassword').value = '';
            document.getElementById('customLicense').value = '';
            document.getElementById('customDurationValue').value = '';
            loadStats();
            loadMyLicenses();
        } else {
            resultDiv.innerHTML = `❌ ERROR: ${data.error}`;
        }
    }
    
    async function createPermanentLicense() {
        const license = document.getElementById('permLicenseKey').value;
        const username = document.getElementById('permUsername').value;
        const password = document.getElementById('permPassword').value;
        
        if(!license) {
            alert('License key required!');
            return;
        }
        
        const res = await fetch(API_URL + '/api/admin/create-permanent-license', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                admin_username: currentUser,
                admin_password: document.getElementById('loginPassword').value,
                license_key: license,
                username: username,
                password: password
            })
        });
        const data = await res.json();
        const resultDiv = document.getElementById('permResult');
        resultDiv.style.display = 'block';
        if(data.success) {
            resultDiv.innerHTML = `✅ PERMANENT LICENSE CREATED! (50 credits)<br>🔑 License: ${license}<br>💰 Remaining Credits: ${data.remaining_credits}<br>🎮 Supports unlimited devices!`;
            document.getElementById('permLicenseKey').value = '';
            document.getElementById('permUsername').value = '';
            document.getElementById('permPassword').value = '';
            loadStats();
            loadMyLicenses();
        } else {
            resultDiv.innerHTML = `❌ ERROR: ${data.error}`;
        }
    }
    
    async function loadMyLicenses() {
        await loadMyTrials();
        await loadMyCustom();
        await loadMyPermanent();
    }
    
    async function loadMyTrials() {
        const res = await fetch(API_URL + '/api/admin/get-my-trials', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({admin_username: currentUser, admin_password: document.getElementById('loginPassword').value})
        });
        const data = await res.json();
        let html = '<table><tr><th>License Key</th><th>Duration</th><th>HWIDs</th><th>Expires</th><th>Status</th><th>Usage</th><th>Action</th></tr>';
        data.trials.forEach(trial => {
            html += `<tr onclick="showUsageDetails('${trial.license_key}')">
                        <td>${trial.license_key}</td>
                        <td>${trial.duration_hours}</td>
                        <td>${trial.hwid_count || 0} device(s)</td>
                        <td>${trial.expires_at || '-'}</td>
                        <td>${trial.status}</td>
                        <td>${trial.usage_count || 0}</td>
                        <td><button class="btn-danger" onclick="event.stopPropagation(); deleteTrial('${trial.license_key}')">Delete</button></td>
                     </tr>`;
        });
        html += '</table>';
        document.getElementById('myTrialsList').innerHTML = html;
    }
    
    async function loadMyCustom() {
        const res = await fetch(API_URL + '/api/admin/get-my-custom', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({admin_username: currentUser, admin_password: document.getElementById('loginPassword').value})
        });
        const data = await res.json();
        let html = '<table><tr><th>License Key</th><th>Username</th><th>HWIDs</th><th>Expires</th><th>Status</th><th>Usage</th><th>Action</th></tr>';
        data.activations.forEach(act => {
            const hwidList = act.hwids || [];
            html += `<tr onclick="showUsageDetails('${act.license_key}')">
                        <td>${act.license_key}</td>
                        <td>${act.username}</td>
                        <td>${hwidList.length} device(s)</td>
                        <td>${act.expires_at || 'NEVER'}</td>
                        <td class="${act.status === 'ACTIVE' ? 'success' : 'warning'}">${act.status}</td>
                        <td>${act.usage_count || 0}</td>
                        <td><button class="btn-danger" onclick="event.stopPropagation(); deleteCustomActivation('${act.license_key}')">Delete</button></td>
                     </tr>`;
        });
        html += '</table>';
        document.getElementById('myCustomList').innerHTML = html;
    }
    
    async function loadMyPermanent() {
        const res = await fetch(API_URL + '/api/admin/get-my-permanent', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({admin_username: currentUser, admin_password: document.getElementById('loginPassword').value})
        });
        const data = await res.json();
        let html = '<tr><tr><th>License Key</th><th>Username</th><th>HWIDs</th><th>Expires</th><th>Status</th><th>Usage</th><th>Action</th></tr>';
        data.licenses.forEach(lic => {
            const hwidList = lic.hwids || [];
            html += `<tr onclick="showUsageDetails('${lic.license_key}')">
                        <td>${lic.license_key}</td>
                        <td>${lic.username || '-'}</td>
                        <td>${hwidList.length} device(s)</td>
                        <td>${lic.expires_at || 'UNLIMITED'}</td>
                        <td>${lic.status}</td>
                        <td>${lic.usage_count || 0}</td>
                        <td><button class="btn-danger" onclick="event.stopPropagation(); deletePermanentLicense('${lic.license_key}')">Delete</button></td>
                     </tr>`;
        });
        html += '</table>';
        document.getElementById('myPermanentList').innerHTML = html;
    }
    
    async function loadAdmins() {
        const res = await fetch(API_URL + '/api/admin/get-admins', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({admin_username: currentUser, admin_password: document.getElementById('loginPassword').value})
        });
        const data = await res.json();
        
        let adminsHtml = '<tr> hilab<th>Username</th><th>Credits</th><th>Created</th><th>Action</th></tr>';
        data.admins.forEach(admin => {
            adminsHtml += `<tr>
                <td>${admin.username}</td>
                <td>${admin.credits}</td>
                <td>${admin.created_at || '-'}</td>
                <td><button class="btn-danger" onclick="deleteAdmin('${admin.username}')">Delete</button></td>
            </tr>`;
        });
        adminsHtml += '</table>';
        document.getElementById('adminsList').innerHTML = adminsHtml;
        
        let modsHtml = '<table><tr><th>Username</th><th>Credits</th><th>Created</th><th>Action</th></tr>';
        data.moderators.forEach(mod => {
            modsHtml += `<tr>
                <td>${mod.username}</td>
                <td>${mod.credits}</td>
                <td>${mod.created_at || '-'}</td>
                <td><button class="btn-danger" onclick="deleteModerator('${mod.username}')">Delete</button></td>
             </tr>`;
        });
        modsHtml += '</table>';
        document.getElementById('moderatorsList').innerHTML = modsHtml;
    }
    
    async function loadAllLicenses() {
        const res = await fetch(API_URL + '/api/admin/get-all-licenses', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({admin_username: currentUser, admin_password: document.getElementById('loginPassword').value})
        });
        const data = await res.json();
        
        let html = '<h4>All Trial Licenses</h4><table><tr><th>License Key</th><th>Owner</th><th>HWIDs</th><th>Expires</th><th>Status</th></tr>';
        data.all_trials.forEach(trial => {
            html += `<tr><td>${trial.license_key}</td><td>${trial.owner || 'Unknown'}</td><td>${trial.hwid_count}</td><td>${trial.expires_at || '-'}</td><td>${trial.status}</td></tr>`;
        });
        html += '</table><h4>All Custom Activations</h4><table><tr><th>License Key</th><th>Owner</th><th>Username</th><th>HWIDs</th><th>Expires</th></tr>';
        data.all_custom.forEach(custom => {
            html += `<tr><td>${custom.license_key}</td><td>${custom.owner || 'Unknown'}</td><td>${custom.username}</td><td>${custom.hwid_count}</td><td>${custom.expires_at || 'NEVER'}</td></tr>`;
        });
        html += '</table><h4>All Permanent Licenses</h4><table><tr><th>License Key</th><th>Owner</th><th>Username</th><th>HWIDs</th></tr>';
        data.all_permanent.forEach(perm => {
            html += `<tr><td>${perm.license_key}</td><td>${perm.owner || 'Unknown'}</td><td>${perm.username || '-'}</td><td>${perm.hwid_count}</td></tr>`;
        });
        html += '</table>';
        document.getElementById('allLicensesList').innerHTML = html;
    }
    
    async function addAdmin() {
        const username = document.getElementById('newAdminUser').value;
        const password = document.getElementById('newAdminPass').value;
        const role = document.getElementById('newAdminRole').value;
        const credits = parseFloat(document.getElementById('newAdminCredits').value);
        
        const res = await fetch(API_URL + '/api/admin/add-admin', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                admin_username: currentUser,
                admin_password: document.getElementById('loginPassword').value,
                new_username: username,
                new_password: password,
                role: role,
                credits: credits
            })
        });
        const data = await res.json();
        if(data.success) {
            alert('User added successfully!');
            document.getElementById('newAdminUser').value = '';
            document.getElementById('newAdminPass').value = '';
            loadAdmins();
        } else {
            alert('Error: ' + data.error);
        }
    }
    
    async function manageCredits() {
        const username = document.getElementById('creditUsername').value;
        const amount = parseFloat(document.getElementById('creditAmount').value);
        
        const res = await fetch(API_URL + '/api/admin/manage-credits', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                admin_username: currentUser,
                admin_password: document.getElementById('loginPassword').value,
                target_username: username,
                amount: amount
            })
        });
        const data = await res.json();
        if(data.success) {
            alert(`Credits updated! New balance: ${data.new_balance}`);
            document.getElementById('creditUsername').value = '';
            document.getElementById('creditAmount').value = '';
            loadAdmins();
            if(username === currentUser) loadStats();
        } else {
            alert('Error: ' + data.error);
        }
    }
    
    async function changePassword() {
        const oldPass = document.getElementById('oldPassword').value;
        const newPass = document.getElementById('newPassword').value;
        const confirmPass = document.getElementById('confirmPassword').value;
        
        if(newPass !== confirmPass) {
            alert('New passwords do not match!');
            return;
        }
        
        const res = await fetch(API_URL + '/api/admin/change-password', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                username: currentUser,
                old_password: oldPass,
                new_password: newPass
            })
        });
        const data = await res.json();
        const resultDiv = document.getElementById('passwordResult');
        resultDiv.style.display = 'block';
        if(data.success) {
            resultDiv.innerHTML = '✅ Password changed successfully! Please login again.';
            setTimeout(() => {
                location.reload();
            }, 2000);
        } else {
            resultDiv.innerHTML = '❌ Error: ' + data.error;
        }
    }
    
    async function deleteAdmin(username) {
        if(!confirm(`Delete admin ${username}?`)) return;
        const res = await fetch(API_URL + '/api/admin/delete-admin', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                admin_username: currentUser,
                admin_password: document.getElementById('loginPassword').value,
                target_username: username,
                role: 'admin'
            })
        });
        const data = await res.json();
        if(data.success) loadAdmins();
    }
    
    async function deleteModerator(username) {
        if(!confirm(`Delete moderator ${username}?`)) return;
        const res = await fetch(API_URL + '/api/admin/delete-admin', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                admin_username: currentUser,
                admin_password: document.getElementById('loginPassword').value,
                target_username: username,
                role: 'moderator'
            })
        });
        const data = await res.json();
        if(data.success) loadAdmins();
    }
    
    async function deleteTrial(key) {
        if(!confirm('Delete this trial?')) return;
        await fetch(API_URL + '/api/admin/delete-trial', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({admin_username: currentUser, admin_password: document.getElementById('loginPassword').value, license_key: key})
        });
        loadMyTrials();
        loadStats();
    }
    
    async function deleteCustomActivation(key) {
        if(!confirm('Delete this activation?')) return;
        await fetch(API_URL + '/api/admin/delete-custom-activation', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({admin_username: currentUser, admin_password: document.getElementById('loginPassword').value, license_key: key})
        });
        loadMyCustom();
        loadStats();
    }
    
    async function deletePermanentLicense(key) {
        if(!confirm('Delete this license?')) return;
        await fetch(API_URL + '/api/admin/delete-permanent-license', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({admin_username: currentUser, admin_password: document.getElementById('loginPassword').value, license_key: key})
        });
        loadMyPermanent();
        loadStats();
    }
    
    async function showUsageDetails(licenseKey) {
        const res = await fetch(API_URL + '/api/admin/get-license-usage', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({admin_username: currentUser, admin_password: document.getElementById('loginPassword').value, license_key: licenseKey})
        });
        const data = await res.json();
        
        document.getElementById('modalTitle').innerHTML = `📊 Usage: ${licenseKey}`;
        document.getElementById('modalBody').innerHTML = `
            <div class="stats-grid">
                <div class="stat-card"><div class="stat-number">${data.total_usage}</div><div>Total Calls</div></div>
                <div class="stat-card"><div class="stat-number">${data.activations}</div><div>Activations</div></div>
                <div class="stat-card"><div class="stat-number">${data.verifications}</div><div>Verifications</div></div>
                <div class="stat-card"><div class="stat-number">${data.unique_hwids}</div><div>Unique PCs</div></div>
            </div>
            <p><strong>Last Used:</strong> ${data.last_used || 'Never'}</p>
            <div class="result-box"><strong>HWIDs:</strong><br>${data.hwid_list.map(h => '• ' + h).join('<br>') || 'None'}</div>
        `;
        document.getElementById('usageModal').style.display = 'block';
    }
    
    async function loadMonitor() {
        const res = await fetch(API_URL + '/api/admin/get-monitor-data', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({admin_username: currentUser, admin_password: document.getElementById('loginPassword').value})
        });
        const data = await res.json();
        document.getElementById('monitorData').innerHTML = `
            📊 MY USAGE STATISTICS<br><br>
            🔹 My Trial Licenses: ${data.my_trials}<br>
            🔹 My Custom Activations: ${data.my_custom}<br>
            🔹 My Permanent Licenses: ${data.my_permanent}<br>
            🔹 Total API Calls from my licenses: ${data.my_api_calls}<br>
            🔹 Active Users (HWIDs): ${data.active_users}<br><br>
            ⏰ Server Time: ${data.server_time}
        `;
    }
    
    function closeModal() {
        document.getElementById('usageModal').style.display = 'none';
    }
    
    setInterval(() => {
        if(document.getElementById('mainPanel').style.display === 'block') {
            loadStats();
        }
    }, 30000);
</script>
</body>
</html>
"""

# ==================================================
# 🔐 API ENDPOINTS (With Owner Tracking)
# ==================================================

@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    data = request.get_json()
    username = data.get("username", "")
    password = data.get("password", "")
    
    if username == MASTER_ADMIN["username"] and password == MASTER_ADMIN["password"]:
        return jsonify({"success": True, "role": "master", "credits": "Unlimited"}), 200
    
    if username in ADMINS and ADMINS[username]["password"] == password:
        return jsonify({"success": True, "role": "admin", "credits": ADMINS[username]["credits"]}), 200
    
    if username in MODERATORS and MODERATORS[username]["password"] == password:
        return jsonify({"success": True, "role": "moderator", "credits": MODERATORS[username]["credits"]}), 200
    
    return jsonify({"success": False}), 401

@app.route('/api/admin/change-password', methods=['POST'])
def change_password():
    data = request.get_json()
    username = data.get("username", "")
    old_password = data.get("old_password", "")
    new_password = data.get("new_password", "")
    
    if username == MASTER_ADMIN["username"]:
        if old_password == MASTER_ADMIN["password"]:
            MASTER_ADMIN["password"] = new_password
            return jsonify({"success": True}), 200
        return jsonify({"success": False, "error": "Wrong password"}), 401
    
    if username in ADMINS:
        if ADMINS[username]["password"] == old_password:
            ADMINS[username]["password"] = new_password
            save_data()
            return jsonify({"success": True}), 200
        return jsonify({"success": False, "error": "Wrong password"}), 401
    
    if username in MODERATORS:
        if MODERATORS[username]["password"] == old_password:
            MODERATORS[username]["password"] = new_password
            save_data()
            return jsonify({"success": True}), 200
    
    return jsonify({"success": False, "error": "User not found"}), 404

@app.route('/api/admin/get-stats', methods=['POST'])
def get_stats():
    data = request.get_json()
    auth = check_admin_auth(data)
    if not auth["authorized"]:
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    licenses = get_licenses_by_owner(auth["username"], auth["role"])
    
    total_usage = 0
    for key in licenses["trials"]:
        total_usage += len(USAGE_LOGS.get(key, []))
    for key in licenses["custom"]:
        total_usage += len(USAGE_LOGS.get(key, []))
    for key in licenses["permanent"]:
        total_usage += len(USAGE_LOGS.get(key, []))
    
    return jsonify({
        "success": True,
        "trials": len(licenses["trials"]),
        "custom": len(licenses["custom"]),
        "permanent": len(licenses["permanent"]),
        "total_usage": total_usage,
        "user_credits": auth.get("credits", "Unlimited")
    }), 200

@app.route('/api/admin/generate-trial', methods=['POST'])
def generate_trial():
    data = request.get_json()
    auth = check_admin_auth(data)
    if not auth["authorized"]:
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    dur = int(data.get("duration_hours", 3))
    credits_cost = round(dur * 0.1, 2)
    
    if auth["role"] != "master":
        if not deduct_credits(auth["username"], credits_cost):
            return jsonify({"success": False, "error": f"Insufficient credits. Need {credits_cost} credits"}), 400
    
    lic = f"JEPFX-TRIAL-{uuid.uuid4().hex[:8].upper()}"
    user = f"TRIAL-{uuid.uuid4().hex[:6].upper()}"
    pwd = uuid.uuid4().hex[:10].upper()
    
    TRIAL_LICENSES[lic] = {
        "type": "trial",
        "owner": auth["username"],
        "hwids": [],
        "duration_hours": dur,
        "start_time": None,
        "expires_at": None,
        "activated_at": None
    }
    TRIAL_USERS[user] = {"password": pwd, "linked_license": lic}
    save_data()
    
    remaining = get_credits(auth["username"])
    
    return jsonify({
        "success": True,
        "license_key": lic,
        "username": user,
        "password": pwd,
        "duration_hours": dur,
        "credits_used": credits_cost,
        "remaining_credits": remaining
    }), 200

@app.route('/api/admin/create-custom-activation', methods=['POST'])
def create_custom_activation():
    data = request.get_json()
    auth = check_admin_auth(data)
    if not auth["authorized"]:
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    license_key = data.get("license_key", "").strip().upper()
    duration_type = data.get("duration_type", "hours")
    duration_value = float(data.get("duration_value", 0))
    
    if not username or not password or not license_key:
        return jsonify({"success": False, "error": "Missing required fields"}), 400
    
    now = datetime.utcnow()
    expires_at = None
    credits_cost = 0
    
    if duration_type == "hours":
        credits_cost = round(duration_value * CREDIT_PRICING["custom_hour"], 2)
        expires_at = now + timedelta(hours=duration_value)
    elif duration_type == "days":
        credits_cost = round(duration_value * CREDIT_PRICING["custom_day"], 2)
        expires_at = now + timedelta(days=duration_value)
    elif duration_type == "weeks":
        credits_cost = round(duration_value * CREDIT_PRICING["custom_week"], 2)
        expires_at = now + timedelta(weeks=duration_value)
    elif duration_type == "months":
        credits_cost = round(duration_value * CREDIT_PRICING["custom_month"], 2)
        expires_at = now + timedelta(days=duration_value * 30)
    elif duration_type == "years":
        credits_cost = round(duration_value * CREDIT_PRICING["custom_year"], 2)
        expires_at = now + timedelta(days=duration_value * 365)
    elif duration_type == "unlimited":
        credits_cost = CREDIT_PRICING["custom_unlimited"]
        expires_at = None
    
    if auth["role"] != "master":
        if not deduct_credits(auth["username"], credits_cost):
            return jsonify({"success": False, "error": f"Insufficient credits. Need {credits_cost} credits"}), 400
    
    CUSTOM_ACTIVATIONS[license_key] = {
        "username": username,
        "password": password,
        "license_key": license_key,
        "owner": auth["username"],
        "hwids": [],
        "expires_at": expires_at.isoformat() if expires_at else None,
        "created_at": now.isoformat(),
        "activated": False
    }
    
    VALID_USERS[username] = password
    save_data()
    
    remaining = get_credits(auth["username"])
    
    return jsonify({
        "success": True,
        "expires_at": expires_at.isoformat() if expires_at else "NEVER",
        "credits_used": credits_cost,
        "remaining_credits": remaining
    }), 200

@app.route('/api/admin/create-permanent-license', methods=['POST'])
def create_permanent_license():
    data = request.get_json()
    auth = check_admin_auth(data)
    if not auth["authorized"]:
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    license_key = data.get("license_key", "").strip().upper()
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    
    if not license_key:
        return jsonify({"success": False, "error": "License key required"}), 400
    
    if auth["role"] != "master":
        if not deduct_credits(auth["username"], CREDIT_PRICING["permanent"]):
            return jsonify({"success": False, "error": f"Insufficient credits. Need {CREDIT_PRICING['permanent']} credits"}), 400
    
    PERMANENT_LICENSES[license_key] = {
        "type": "permanent",
        "owner": auth["username"],
        "username": username if username else None,
        "password": password if password else None,
        "hwids": [],
        "expires_at": None,
        "created_at": datetime.utcnow().isoformat()
    }
    
    if username and password:
        VALID_USERS[username] = password
    
    save_data()
    
    remaining = get_credits(auth["username"])
    
    return jsonify({
        "success": True,
        "remaining_credits": remaining
    }), 200

# ==================================================
# 📋 MY LICENSES ENDPOINTS (Filtered by owner)
# ==================================================

@app.route('/api/admin/get-my-trials', methods=['POST'])
def get_my_trials():
    data = request.get_json()
    auth = check_admin_auth(data)
    if not auth["authorized"]:
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    now = datetime.utcnow()
    list_trials = []
    
    for k, v in TRIAL_LICENSES.items():
        if v.get("owner") == auth["username"] or auth["role"] == "master":
            status = "NOT ACTIVATED"
            if v.get("expires_at"):
                exp = datetime.fromisoformat(v["expires_at"])
                if exp > now:
                    status = "ACTIVE"
                else:
                    status = "EXPIRED"
            
            usage_count = len(USAGE_LOGS.get(k, []))
            hwid_count = len(v.get("hwids", []))
            
            list_trials.append({
                "license_key": k,
                "duration_hours": f"{v['duration_hours']}h",
                "hwid_count": hwid_count,
                "expires_at": v.get("expires_at") or "-",
                "status": status,
                "usage_count": usage_count
            })
    
    return jsonify({"trials": list_trials}), 200

@app.route('/api/admin/get-my-custom', methods=['POST'])
def get_my_custom():
    data = request.get_json()
    auth = check_admin_auth(data)
    if not auth["authorized"]:
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    now = datetime.utcnow()
    list_custom = []
    
    for k, v in CUSTOM_ACTIVATIONS.items():
        if v.get("owner") == auth["username"] or auth["role"] == "master":
            status = "ACTIVE"
            if v.get("expires_at"):
                exp = datetime.fromisoformat(v["expires_at"])
                if now > exp:
                    status = "EXPIRED"
            
            usage_count = len(USAGE_LOGS.get(k, []))
            
            list_custom.append({
                "license_key": k,
                "username": v.get("username"),
                "hwids": v.get("hwids", []),
                "expires_at": v.get("expires_at") or "UNLIMITED",
                "status": status,
                "usage_count": usage_count
            })
    
    return jsonify({"activations": list_custom}), 200

@app.route('/api/admin/get-my-permanent', methods=['POST'])
def get_my_permanent():
    data = request.get_json()
    auth = check_admin_auth(data)
    if not auth["authorized"]:
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    list_permanent = []
    
    for k, v in PERMANENT_LICENSES.items():
        if v.get("owner") == auth["username"] or auth["role"] == "master":
            usage_count = len(USAGE_LOGS.get(k, []))
            
            list_permanent.append({
                "license_key": k,
                "username": v.get("username"),
                "hwids": v.get("hwids", []),
                "expires_at": v.get("expires_at") or "UNLIMITED",
                "status": "ACTIVE",
                "usage_count": usage_count
            })
    
    return jsonify({"licenses": list_permanent}), 200

@app.route('/api/admin/get-all-licenses', methods=['POST'])
def get_all_licenses():
    data = request.get_json()
    auth = check_admin_auth(data)
    if not auth["authorized"] or auth["role"] != "master":
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    now = datetime.utcnow()
    all_trials = []
    for k, v in TRIAL_LICENSES.items():
        status = "NOT ACTIVATED"
        if v.get("expires_at"):
            exp = datetime.fromisoformat(v["expires_at"])
            if exp > now:
                status = "ACTIVE"
            else:
                status = "EXPIRED"
        
        all_trials.append({
            "license_key": k,
            "owner": v.get("owner", "Unknown"),
            "hwid_count": len(v.get("hwids", [])),
            "expires_at": v.get("expires_at") or "-",
            "status": status
        })
    
    all_custom = []
    for k, v in CUSTOM_ACTIVATIONS.items():
        all_custom.append({
            "license_key": k,
            "owner": v.get("owner", "Unknown"),
            "username": v.get("username"),
            "hwid_count": len(v.get("hwids", [])),
            "expires_at": v.get("expires_at") or "NEVER"
        })
    
    all_permanent = []
    for k, v in PERMANENT_LICENSES.items():
        all_permanent.append({
            "license_key": k,
            "owner": v.get("owner", "Unknown"),
            "username": v.get("username"),
            "hwid_count": len(v.get("hwids", []))
        })
    
    return jsonify({
        "all_trials": all_trials,
        "all_custom": all_custom,
        "all_permanent": all_permanent
    }), 200

@app.route('/api/admin/get-admins', methods=['POST'])
def get_admins():
    data = request.get_json()
    auth = check_admin_auth(data)
    if not auth["authorized"] or auth["role"] != "master":
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    admins_list = [{"username": k, "credits": v["credits"], "created_at": v.get("created_at")} for k, v in ADMINS.items()]
    mods_list = [{"username": k, "credits": v["credits"], "created_at": v.get("created_at")} for k, v in MODERATORS.items()]
    
    return jsonify({"admins": admins_list, "moderators": mods_list}), 200

@app.route('/api/admin/add-admin', methods=['POST'])
def add_admin():
    data = request.get_json()
    auth = check_admin_auth(data)
    if not auth["authorized"] or auth["role"] != "master":
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    new_username = data.get("new_username", "")
    new_password = data.get("new_password", "")
    role = data.get("role", "admin")
    credits = float(data.get("credits", 100))
    
    if not new_username or not new_password:
        return jsonify({"success": False, "error": "Username and password required"}), 400
    
    if role == "admin":
        ADMINS[new_username] = {
            "password": new_password,
            "credits": credits,
            "created_at": datetime.utcnow().isoformat()
        }
    else:
        MODERATORS[new_username] = {
            "password": new_password,
            "credits": credits,
            "created_at": datetime.utcnow().isoformat()
        }
    
    save_data()
    return jsonify({"success": True}), 200

@app.route('/api/admin/manage-credits', methods=['POST'])
def manage_credits():
    data = request.get_json()
    auth = check_admin_auth(data)
    if not auth["authorized"] or auth["role"] != "master":
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    target_username = data.get("target_username", "")
    amount = float(data.get("amount", 0))
    
    if target_username in ADMINS:
        ADMINS[target_username]["credits"] = round(ADMINS[target_username]["credits"] + amount, 2)
        new_balance = ADMINS[target_username]["credits"]
        save_data()
        return jsonify({"success": True, "new_balance": new_balance}), 200
    
    if target_username in MODERATORS:
        MODERATORS[target_username]["credits"] = round(MODERATORS[target_username]["credits"] + amount, 2)
        new_balance = MODERATORS[target_username]["credits"]
        save_data()
        return jsonify({"success": True, "new_balance": new_balance}), 200
    
    return jsonify({"success": False, "error": "User not found"}), 404

@app.route('/api/admin/delete-admin', methods=['POST'])
def delete_admin():
    data = request.get_json()
    auth = check_admin_auth(data)
    if not auth["authorized"] or auth["role"] != "master":
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    target_username = data.get("target_username", "")
    role = data.get("role", "admin")
    
    if role == "admin" and target_username in ADMINS:
        del ADMINS[target_username]
        save_data()
        return jsonify({"success": True}), 200
    
    if role == "moderator" and target_username in MODERATORS:
        del MODERATORS[target_username]
        save_data()
        return jsonify({"success": True}), 200
    
    return jsonify({"success": False, "error": "User not found"}), 404

@app.route('/api/admin/get-monitor-data', methods=['POST'])
def get_monitor_data():
    data = request.get_json()
    auth = check_admin_auth(data)
    if not auth["authorized"]:
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    licenses = get_licenses_by_owner(auth["username"], auth["role"])
    
    my_api_calls = 0
    for key in licenses["trials"]:
        my_api_calls += len(USAGE_LOGS.get(key, []))
    for key in licenses["custom"]:
        my_api_calls += len(USAGE_LOGS.get(key, []))
    for key in licenses["permanent"]:
        my_api_calls += len(USAGE_LOGS.get(key, []))
    
    active_users = set()
    for logs in USAGE_LOGS.values():
        for log in logs[-10:]:
            if "hwid" in log.get("details", {}):
                active_users.add(log["details"]["hwid"])
    
    return jsonify({
        "my_trials": len(licenses["trials"]),
        "my_custom": len(licenses["custom"]),
        "my_permanent": len(licenses["permanent"]),
        "my_api_calls": my_api_calls,
        "active_users": len(active_users),
        "server_time": datetime.utcnow().isoformat()
    }), 200

@app.route('/api/admin/delete-trial', methods=['POST'])
def delete_trial():
    data = request.get_json()
    auth = check_admin_auth(data)
    if not auth["authorized"]:
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    key = data.get("license_key", "")
    
    if key in TRIAL_LICENSES:
        # Check ownership
        if auth["role"] != "master" and TRIAL_LICENSES[key].get("owner") != auth["username"]:
            return jsonify({"success": False, "error": "Not your license"}), 403
        
        for user, user_data in list(TRIAL_USERS.items()):
            if user_data.get("linked_license") == key:
                del TRIAL_USERS[user]
        del TRIAL_LICENSES[key]
        save_data()
        return jsonify({"success": True}), 200
    return jsonify({"success": False, "error": "Not found"}), 404

@app.route('/api/admin/delete-custom-activation', methods=['POST'])
def delete_custom_activation():
    data = request.get_json()
    auth = check_admin_auth(data)
    if not auth["authorized"]:
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    key = data.get("license_key", "")
    
    if key in CUSTOM_ACTIVATIONS:
        if auth["role"] != "master" and CUSTOM_ACTIVATIONS[key].get("owner") != auth["username"]:
            return jsonify({"success": False, "error": "Not your license"}), 403
        
        del CUSTOM_ACTIVATIONS[key]
        save_data()
        return jsonify({"success": True}), 200
    return jsonify({"success": False, "error": "Not found"}), 404

@app.route('/api/admin/delete-permanent-license', methods=['POST'])
def delete_permanent_license():
    data = request.get_json()
    auth = check_admin_auth(data)
    if not auth["authorized"]:
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    key = data.get("license_key", "")
    
    if key in PERMANENT_LICENSES:
        if auth["role"] != "master" and PERMANENT_LICENSES[key].get("owner") != auth["username"]:
            return jsonify({"success": False, "error": "Not your license"}), 403
        
        del PERMANENT_LICENSES[key]
        save_data()
        return jsonify({"success": True}), 200
    return jsonify({"success": False, "error": "Not found"}), 404

@app.route('/api/admin/get-license-usage', methods=['POST'])
def get_license_usage():
    data = request.get_json()
    auth = check_admin_auth(data)
    if not auth["authorized"]:
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    license_key = data.get("license_key", "")
    
    # Check if user has access to this license
    has_access = False
    if auth["role"] == "master":
        has_access = True
    else:
        if license_key in TRIAL_LICENSES and TRIAL_LICENSES[license_key].get("owner") == auth["username"]:
            has_access = True
        elif license_key in CUSTOM_ACTIVATIONS and CUSTOM_ACTIVATIONS[license_key].get("owner") == auth["username"]:
            has_access = True
        elif license_key in PERMANENT_LICENSES and PERMANENT_LICENSES[license_key].get("owner") == auth["username"]:
            has_access = True
    
    if not has_access:
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    stats = get_usage_stats(license_key)
    
    return jsonify({
        "total_usage": stats["total_usage"],
        "activations": stats["total_activations"],
        "verifications": stats["total_verifications"],
        "last_used": stats["last_used"],
        "unique_hwids": len(stats["unique_hwids"]),
        "hwid_list": stats["unique_hwids"]
    }), 200

# ==================================================
# 🔑 ACTIVATION ENDPOINTS (Same as before)
# ==================================================

@app.route('/api/activate', methods=['POST'])
def activate():
    data = request.get_json()
    key = data.get("license_key", "").strip().upper()
    hwid = data.get("hardware_id", "").strip()
    now = datetime.utcnow()
    
    if key in CUSTOM_ACTIVATIONS:
        activation = CUSTOM_ACTIVATIONS[key]
        
        if activation.get("expires_at"):
            exp_time = datetime.fromisoformat(activation["expires_at"])
            if now > exp_time:
                return jsonify({"status": "expired"}), 403
        
        if "hwids" not in activation:
            activation["hwids"] = []
        
        if hwid not in activation["hwids"]:
            activation["hwids"].append(hwid)
            save_data()
        
        log_usage(key, "activation", {"hwid": hwid})
        
        return jsonify({
            "status": "activated",
            "msg": f"Activated on {len(activation['hwids'])} device(s)"
        }), 200
    
    if key in PERMANENT_LICENSES:
        lic = PERMANENT_LICENSES[key]
        
        if "hwids" not in lic:
            lic["hwids"] = []
        
        if hwid not in lic["hwids"]:
            lic["hwids"].append(hwid)
            save_data()
        
        log_usage(key, "activation", {"hwid": hwid})
        return jsonify({"status": "activated", "msg": f"Activated on {len(lic['hwids'])} device(s)"}), 200
    
    if key in TRIAL_LICENSES:
        lic = TRIAL_LICENSES[key]
        
        if "hwids" not in lic:
            lic["hwids"] = []
        
        if lic.get("expires_at"):
            exp_time = datetime.fromisoformat(lic["expires_at"])
            if now > exp_time:
                return jsonify({"status": "expired"}), 403
        
        if lic["start_time"] is None:
            lic["start_time"] = now.isoformat()
            lic["expires_at"] = (now + timedelta(hours=lic["duration_hours"])).isoformat()
        
        if hwid not in lic["hwids"]:
            lic["hwids"].append(hwid)
            save_data()
        
        log_usage(key, "activation", {"hwid": hwid})
        return jsonify({"status": "activated", "msg": f"Trial activated on {len(lic['hwids'])} device(s)"}), 200
    
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
    
    return jsonify({"status": "invalid"}), 403

@app.route('/api/verify-license', methods=['POST'])
def verify():
    data = request.get_json()
    hwid = data.get("hwid", "")
    key_hash = data.get("hash", "")
    now = datetime.utcnow()
    
    for key, activation in CUSTOM_ACTIVATIONS.items():
        if hashlib.sha256(key.encode()).hexdigest() == key_hash:
            if activation.get("expires_at"):
                exp_time = datetime.fromisoformat(activation["expires_at"])
                if now > exp_time:
                    return jsonify({"expired": True}), 403
            if hwid in activation.get("hwids", []):
                log_usage(key, "verification", {"hwid": hwid})
                return jsonify({"ok": True}), 200
            return jsonify({"invalid": True}), 403
    
    for key, lic in PERMANENT_LICENSES.items():
        if hashlib.sha256(key.encode()).hexdigest() == key_hash:
            if hwid in lic.get("hwids", []):
                log_usage(key, "verification", {"hwid": hwid})
                return jsonify({"ok": True}), 200
            return jsonify({"invalid": True}), 403
    
    for key, lic in TRIAL_LICENSES.items():
        if hashlib.sha256(key.encode()).hexdigest() == key_hash:
            if lic.get("expires_at"):
                exp_time = datetime.fromisoformat(lic["expires_at"])
                if now > exp_time:
                    return jsonify({"expired": True}), 403
            if hwid in lic.get("hwids", []):
                log_usage(key, "verification", {"hwid": hwid})
                return jsonify({"ok": True}), 200
            return jsonify({"invalid": True}), 403
    
    for key, lic in LICENSES.items():
        if hashlib.sha256(key.encode()).hexdigest() == key_hash:
            if lic["type"] == "unlimited" and hwid in lic["hwid"]:
                return jsonify({"ok": True}), 200
            if lic["type"] == "single" and lic["hwid"] == hwid:
                return jsonify({"ok": True}), 200
            return jsonify({"invalid": True}), 403
    
    return jsonify({"invalid": True}), 403

@app.route('/api/validate-user', methods=['POST'])
def validate_user():
    username = request.get_json().get("username", "")
    
    for key, activation in CUSTOM_ACTIVATIONS.items():
        if activation["username"] == username:
            log_usage(key, "validation", {"username": username})
            return jsonify({"ok": True}), 200
    
    if username in VALID_USERS or username in TRIAL_USERS:
        return jsonify({"ok": True}), 200
    
    return "", 403

@app.route('/api/check-password', methods=['POST'])
def check_pass():
    data = request.get_json()
    username = data.get("username", "")
    password = data.get("password", "")
    
    for key, activation in CUSTOM_ACTIVATIONS.items():
        if activation["username"] == username and activation["password"] == password:
            log_usage(key, "login", {"username": username})
            return jsonify({"ok": True}), 200
    
    if (username in VALID_USERS and VALID_USERS[username] == password) or \
       (username in TRIAL_USERS and TRIAL_USERS[username]["password"] == password):
        return jsonify({"ok": True}), 200
    
    return "", 403

@app.route('/admin')
def admin_page():
    return render_template_string(ADMIN_HTML)

@app.route('/')
def home():
    return jsonify({
        "status": "online",
        "message": "JEPFX License Server Running",
        "endpoints": {
            "activate": "/api/activate",
            "verify": "/api/verify-license",
            "validate_user": "/api/validate-user",
            "check_password": "/api/check-password",
            "admin": "/admin"
        }
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)