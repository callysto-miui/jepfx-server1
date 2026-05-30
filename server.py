from flask import Flask, request, jsonify, render_template_string
import hashlib
from datetime import datetime, timedelta
import uuid
import json
import os
import threading
import time

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
PERMANENT_LICENSES = {}  # Will be loaded from JSON
CUSTOM_ACTIVATIONS = {}  # Custom activations with time limits

LICENSES = {
    "JEPFX_0": {"type": "unlimited", "hwid": [], "expires_at": None},
    "RHYZ_0": {"type": "unlimited", "hwid": [], "expires_at": None},
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
# 📊 USAGE TRACKING
# ==================================================
USAGE_LOGS = {}  # license_key -> list of usage events

# ==================================================
# 💾 SAVE / LOAD DATA — FIXED VERSION
# ==================================================
def load_data():
    global TRIAL_LICENSES, TRIAL_USERS, PERMANENT_LICENSES, CUSTOM_ACTIVATIONS, USAGE_LOGS
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
                TRIAL_LICENSES = data.get("trials", {})
                TRIAL_USERS = data.get("users", {})
                PERMANENT_LICENSES = data.get("permanent_licenses", {})
                CUSTOM_ACTIVATIONS = data.get("custom_activations", {})
                USAGE_LOGS = data.get("usage_logs", {})
            print("✅ DATA LOADED SUCCESSFULLY")
        except Exception as e:
            print(f"⚠️ LOAD ERROR: {e} — CREATING NEW")
            TRIAL_LICENSES = {}
            TRIAL_USERS = {}
            PERMANENT_LICENSES = {}
            CUSTOM_ACTIVATIONS = {}
            USAGE_LOGS = {}
            save_data()
    else:
        print("📄 NO FILE — CREATING NEW")
        save_data()

def save_data():
    data = {
        "trials": TRIAL_LICENSES, 
        "users": TRIAL_USERS,
        "permanent_licenses": PERMANENT_LICENSES,
        "custom_activations": CUSTOM_ACTIVATIONS,
        "usage_logs": USAGE_LOGS
    }
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=2, default=str)
        print("💾 DATA SAVED SUCCESSFULLY")
    except Exception as e:
        print(f"❌ SAVE ERROR: {e}")

load_data()

# ==================================================
# 📊 USAGE TRACKING FUNCTION
# ==================================================
def log_usage(license_key, event_type, details=None):
    """Log usage events for a license key"""
    if license_key not in USAGE_LOGS:
        USAGE_LOGS[license_key] = []
    
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "event_type": event_type,  # "activation", "verification", "login", "validation"
        "details": details or {}
    }
    
    USAGE_LOGS[license_key].append(log_entry)
    
    # Keep only last 1000 entries per license to prevent memory issues
    if len(USAGE_LOGS[license_key]) > 1000:
        USAGE_LOGS[license_key] = USAGE_LOGS[license_key][-1000:]
    
    save_data()
    print(f"📊 USAGE LOGGED: {license_key} - {event_type}")

def get_usage_stats(license_key):
    """Get usage statistics for a license key"""
    logs = USAGE_LOGS.get(license_key, [])
    
    stats = {
        "total_activations": 0,
        "total_verifications": 0,
        "total_logins": 0,
        "total_validations": 0,
        "last_used": None,
        "first_used": None,
        "unique_hwids": set(),
        "hourly_usage": {},
        "daily_usage": {},
        "recent_events": []
    }
    
    for log in logs:
        # Count by event type
        if log["event_type"] == "activation":
            stats["total_activations"] += 1
        elif log["event_type"] == "verification":
            stats["total_verifications"] += 1
        elif log["event_type"] == "login":
            stats["total_logins"] += 1
        elif log["event_type"] == "validation":
            stats["total_validations"] += 1
        
        # Track HWIDs
        if "hwid" in log.get("details", {}):
            stats["unique_hwids"].add(log["details"]["hwid"])
        
        # Track timestamps
        timestamp = datetime.fromisoformat(log["timestamp"])
        if not stats["first_used"] or timestamp < stats["first_used"]:
            stats["first_used"] = timestamp
        if not stats["last_used"] or timestamp > stats["last_used"]:
            stats["last_used"] = timestamp
        
        # Hourly usage
        hour_key = timestamp.strftime("%Y-%m-%d %H:00")
        stats["hourly_usage"][hour_key] = stats["hourly_usage"].get(hour_key, 0) + 1
        
        # Daily usage
        day_key = timestamp.strftime("%Y-%m-%d")
        stats["daily_usage"][day_key] = stats["daily_usage"].get(day_key, 0) + 1
    
    # Convert set to list for JSON serialization
    stats["unique_hwids"] = list(stats["unique_hwids"])
    
    # Get last 20 events
    stats["recent_events"] = logs[-20:][::-1]  # Most recent first
    
    # Add total usage count
    stats["total_usage"] = len(logs)
    
    return stats

# ==================================================
# 🔍 MONITORING THREAD — Checks expired licenses
# ==================================================
def monitor_expired_licenses():
    """Background thread to monitor and cleanup expired licenses"""
    while True:
        try:
            now = datetime.utcnow()
            changes_made = False
            
            # Check custom activations
            for key, activation in list(CUSTOM_ACTIVATIONS.items()):
                if activation.get("expires_at"):
                    exp_time = datetime.fromisoformat(activation["expires_at"])
                    if now > exp_time:
                        del CUSTOM_ACTIVATIONS[key]
                        changes_made = True
                        print(f"🗑️ Removed expired activation: {key}")
            
            # Check permanent licenses with expiry
            for key, lic in list(PERMANENT_LICENSES.items()):
                if lic.get("expires_at"):
                    exp_time = datetime.fromisoformat(lic["expires_at"])
                    if now > exp_time:
                        del PERMANENT_LICENSES[key]
                        changes_made = True
                        print(f"🗑️ Removed expired permanent license: {key}")
            
            # Check trial licenses
            for key, lic in list(TRIAL_LICENSES.items()):
                if lic.get("expires_at"):
                    exp_time = datetime.fromisoformat(lic["expires_at"])
                    if now > exp_time and lic.get("hwid"):
                        # Mark as expired but don't delete for history
                        lic["expired"] = True
                        changes_made = True
            
            if changes_made:
                save_data()
                
        except Exception as e:
            print(f"⚠️ Monitor error: {e}")
        
        time.sleep(60)  # Check every minute

# Start monitoring thread
monitor_thread = threading.Thread(target=monitor_expired_licenses, daemon=True)
monitor_thread.start()

# ==================================================
# 🎨 ADMIN PANEL HTML with Usage Tracking
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
        input, select, textarea { width: 100%; padding: 12px; margin: 10px 0; border: none; border-radius: 5px; background: #3a2b70; color: white; font-size: 16px; }
        button { padding: 12px 25px; margin: 10px 5px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; font-weight: bold; }
        .btn-primary { background: #7B61FF; color: white; }
        .btn-danger { background: #ef4444; color: white; }
        .btn-success { background: #10b981; color: white; }
        .btn-info { background: #3b82f6; color: white; }
        .tabs { display: flex; gap: 10px; margin-bottom: 20px; flex-wrap: wrap; }
        .tab { padding: 12px 25px; background: #241854; border-radius: 5px; cursor: pointer; }
        .tab.active { background: #7B61FF; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; background: #241854; overflow-x: auto; display: block; }
        th, td { padding: 12px; text-align: center; border-bottom: 1px solid #3a2b70; }
        th { background: #3a2b70; }
        .result { background: #241854; padding: 20px; border-radius: 5px; margin-top: 20px; white-space: pre-line; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px; }
        .stat-card { background: #241854; padding: 15px; border-radius: 10px; text-align: center; cursor: pointer; transition: transform 0.2s; }
        .stat-card:hover { transform: scale(1.05); background: #2d2068; }
        .stat-number { font-size: 32px; font-weight: bold; color: #7B61FF; }
        .warning { color: #f59e0b; }
        .success { color: #10b981; }
        .modal { display: none; position: fixed; z-index: 1; left: 0; top: 0; width: 100%; height: 100%; overflow: auto; background-color: rgba(0,0,0,0.8); }
        .modal-content { background-color: #241854; margin: 5% auto; padding: 20px; border: 1px solid #7B61FF; width: 90%; max-width: 1200px; border-radius: 10px; max-height: 80%; overflow-y: auto; }
        .close { color: #aaa; float: right; font-size: 28px; font-weight: bold; cursor: pointer; }
        .close:hover { color: white; }
        .usage-stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; margin: 20px 0; }
        .usage-card { background: #3a2b70; padding: 10px; border-radius: 5px; text-align: center; }
        .event-log { background: #1a103d; padding: 10px; margin: 5px 0; border-radius: 5px; font-family: monospace; font-size: 12px; }
        .clickable-row { cursor: pointer; }
        .clickable-row:hover { background: #3a2b70; }
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
    
    <!-- Stats -->
    <div class="stats" id="stats">
        <div class="stat-card" onclick="showTab('trials')">
            <div class="stat-number" id="stat-trials">0</div>
            <div>Trial Licenses</div>
        </div>
        <div class="stat-card" onclick="showTab('permanent')">
            <div class="stat-number" id="stat-permanent">0</div>
            <div>Permanent Licenses</div>
        </div>
        <div class="stat-card" onclick="showTab('activations')">
            <div class="stat-number" id="stat-custom">0</div>
            <div>Custom Activations</div>
        </div>
        <div class="stat-card" onclick="showTab('usage-analytics')">
            <div class="stat-number" id="stat-total-usage">0</div>
            <div>Total API Calls</div>
        </div>
    </div>
    
    <div class="tabs">
        <div class="tab active" onclick="showTab('generate')">🎲 GENERATE TRIAL</div>
        <div class="tab" onclick="showTab('custom')">✨ CUSTOM ACTIVATOR</div>
        <div class="tab" onclick="showTab('permanent')">🔑 PERMANENT LICENSES</div>
        <div class="tab" onclick="showTab('trials')">📋 VIEW TRIALS</div>
        <div class="tab" onclick="showTab('activations')">👥 ACTIVATIONS</div>
        <div class="tab" onclick="showTab('usage-analytics')">📊 USAGE ANALYTICS</div>
        <div class="tab" onclick="showTab('stats-page')">📈 MONITOR</div>
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

    <div id="custom" class="content">
        <h3>✨ Custom Activation Creator</h3>
        <label>Custom Username:</label>
        <input type="text" id="custom-username" placeholder="Enter username...">
        <label>Custom Password:</label>
        <input type="text" id="custom-password" placeholder="Enter password...">
        <label>License Key:</label>
        <input type="text" id="custom-license" placeholder="Enter license key...">
        <label>Duration Type:</label>
        <select id="duration-type">
            <option value="hours">Hours</option>
            <option value="days">Days</option>
            <option value="months">Months</option>
            <option value="years">Years</option>
            <option value="unlimited">Unlimited</option>
        </select>
        <label>Duration Value:</label>
        <input type="number" id="duration-value" placeholder="Enter duration...">
        <br>
        <button class="btn-primary" onclick="createCustomActivation()">CREATE ACTIVATION</button>
        <div id="custom-result" class="result" style="display: none;"></div>
    </div>

    <div id="permanent" class="content">
        <h3>🔑 Manage Permanent Licenses</h3>
        <label>License Key:</label>
        <input type="text" id="perm-license" placeholder="Enter license key...">
        <label>Username (optional):</label>
        <input type="text" id="perm-username" placeholder="Enter username...">
        <label>Password (optional):</label>
        <input type="text" id="perm-password" placeholder="Enter password...">
        <label>Expiry Date (optional):</label>
        <input type="datetime-local" id="perm-expiry">
        <br>
        <button class="btn-primary" onclick="createPermanentLicense()">CREATE PERMANENT LICENSE</button>
        <button class="btn-primary" onclick="loadPermanentLicenses()">REFRESH LIST</button>
        <table id="permanent-table">
            <tr><th>LICENSE KEY</th><th>USERNAME</th><th>HWID</th><th>EXPIRES</th><th>STATUS</th><th>USAGE</th><th>ACTION</th></tr>
        </table>
    </div>

    <div id="trials" class="content">
        <h3>All Active Trials</h3>
        <button class="btn-primary" onclick="loadTrials()">REFRESH LIST</button>
        <table id="trials-table">
            <tr><th>LICENSE KEY</th><th>DURATION</th><th>HWID</th><th>EXPIRES</th><th>STATUS</th><th>REMAINING</th><th>USAGE</th><th>ACTION</th></tr>
        </table>
    </div>

    <div id="activations" class="content">
        <h3>👥 Custom Activations</h3>
        <button class="btn-primary" onclick="loadCustomActivations()">REFRESH LIST</button>
        <table id="activations-table">
            <tr><th>LICENSE KEY</th><th>USERNAME</th><th>PASSWORD</th><th>HWID</th><th>EXPIRES</th><th>STATUS</th><th>USAGE</th><th>ACTION</th></tr>
        </table>
    </div>

    <div id="usage-analytics" class="content">
        <h3>📊 License Usage Analytics</h3>
        <p>Click on any license to see detailed usage statistics</p>
        <input type="text" id="search-license" placeholder="Search license key..." onkeyup="filterLicenses()" style="width: 100%;">
        <button class="btn-primary" onclick="loadUsageAnalytics()">REFRESH</button>
        <table id="usage-table">
            <thead>
                <tr><th>LICENSE KEY</th><th>TYPE</th><th>TOTAL USES</th><th>ACTIVATIONS</th><th>VERIFICATIONS</th><th>LOGINS</th><th>LAST USED</th><th>UNIQUE HWIDS</th></tr>
            </thead>
            <tbody id="usage-table-body">
            </tbody>
        </table>
    </div>

    <div id="stats-page" class="content">
        <h3>📈 System Monitor</h3>
        <button class="btn-primary" onclick="loadMonitorData()">REFRESH</button>
        <div id="monitor-data" class="result">
            Loading...
        </div>
    </div>
</div>

<!-- Usage Details Modal -->
<div id="usageModal" class="modal">
    <div class="modal-content">
        <span class="close" onclick="closeModal()">&times;</span>
        <h2 id="modal-title">License Usage Details</h2>
        <div id="modal-content"></div>
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
                loadStats();
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
        if(tabName === 'permanent') loadPermanentLicenses();
        if(tabName === 'activations') loadCustomActivations();
        if(tabName === 'stats-page') loadMonitorData();
        if(tabName === 'usage-analytics') loadUsageAnalytics();
    }

    async function loadStats() {
        const res = await fetch(SERVER_URL + '/api/admin/get-stats', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({admin_key: ADMIN_KEY})
        });
        const data = await res.json();
        document.getElementById('stat-trials').textContent = data.trials;
        document.getElementById('stat-permanent').textContent = data.permanent;
        document.getElementById('stat-custom').textContent = data.custom;
        document.getElementById('stat-total-usage').textContent = data.total_usage || 0;
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
            loadStats();
        } else {
            document.getElementById('result').innerHTML = '❌ ERROR!';
        }
    }

    async function createCustomActivation() {
        const username = document.getElementById('custom-username').value;
        const password = document.getElementById('custom-password').value;
        const license = document.getElementById('custom-license').value;
        const durationType = document.getElementById('duration-type').value;
        const durationValue = parseInt(document.getElementById('duration-value').value);
        
        if(!username || !password || !license) {
            alert('Please fill all fields!');
            return;
        }
        
        const res = await fetch(SERVER_URL + '/api/admin/create-custom-activation', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                admin_key: ADMIN_KEY,
                username: username,
                password: password,
                license_key: license,
                duration_type: durationType,
                duration_value: durationValue
            })
        });
        const data = await res.json();
        document.getElementById('custom-result').style.display = 'block';
        if(res.ok) {
            document.getElementById('custom-result').innerHTML = `
✅ CUSTOM ACTIVATION CREATED
━━━━━━━━━━━━━━━━━━━━━━━━━━
🔑 LICENSE: ${license}
👤 USERNAME: ${username}
🔒 PASSWORD: ${password}
⏰ TYPE: ${durationType.toUpperCase()}
📅 EXPIRES: ${data.expires_at || 'NEVER'}
━━━━━━━━━━━━━━━━━━━━━━━━━━
            `;
            document.getElementById('custom-username').value = '';
            document.getElementById('custom-password').value = '';
            document.getElementById('custom-license').value = '';
            document.getElementById('duration-value').value = '';
            loadCustomActivations();
            loadStats();
        } else {
            document.getElementById('custom-result').innerHTML = '❌ ERROR: ' + (data.error || 'Unknown error');
        }
    }

    async function createPermanentLicense() {
        const license = document.getElementById('perm-license').value;
        const username = document.getElementById('perm-username').value;
        const password = document.getElementById('perm-password').value;
        const expiry = document.getElementById('perm-expiry').value;
        
        if(!license) {
            alert('Please enter license key!');
            return;
        }
        
        const res = await fetch(SERVER_URL + '/api/admin/create-permanent-license', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                admin_key: ADMIN_KEY,
                license_key: license,
                username: username,
                password: password,
                expires_at: expiry
            })
        });
        const data = await res.json();
        if(res.ok) {
            alert('✅ Permanent license created!');
            document.getElementById('perm-license').value = '';
            document.getElementById('perm-username').value = '';
            document.getElementById('perm-password').value = '';
            document.getElementById('perm-expiry').value = '';
            loadPermanentLicenses();
            loadStats();
        } else {
            alert('❌ Error: ' + (data.error || 'Unknown error'));
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
        table.innerHTML = `<tr><th>LICENSE KEY</th><th>DURATION</th><th>HWID</th><th>EXPIRES</th><th>STATUS</th><th>REMAINING</th><th>USAGE</th><th>ACTION</th></tr>`;
        data.trials.forEach(trial => {
            const row = table.insertRow(-1);
            row.className = 'clickable-row';
            row.onclick = () => showUsageDetails(trial.license_key);
            row.innerHTML = `
                <td>${trial.license_key}</td>
                <td>${trial.duration_hours}</td>
                <td>${trial.hwid || '-'}</td>
                <td>${trial.expires_at || '-'}</td>
                <td class="${trial.status.includes('ACTIVE') ? 'success' : 'warning'}">${trial.status}</td>
                <td>${trial.remaining}</td>
                <td><span class="stat-number" style="font-size: 16px;">${trial.usage_count || 0}</span></td>
                <td><button class="btn-danger" onclick="event.stopPropagation(); deleteTrial('${trial.license_key}')">DELETE</button></td>
            `;
        });
    }

    async function loadPermanentLicenses() {
        const res = await fetch(SERVER_URL + '/api/admin/get-permanent-licenses', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({admin_key: ADMIN_KEY})
        });
        const data = await res.json();
        const table = document.getElementById('permanent-table');
        table.innerHTML = `<tr><th>LICENSE KEY</th><th>USERNAME</th><th>HWID</th><th>EXPIRES</th><th>STATUS</th><th>USAGE</th><th>ACTION</th></tr>`;
        data.licenses.forEach(lic => {
            const row = table.insertRow(-1);
            row.className = 'clickable-row';
            row.onclick = () => showUsageDetails(lic.license_key);
            row.innerHTML = `
                <td>${lic.license_key}</td>
                <td>${lic.username || '-'}</td>
                <td>${lic.hwid || '-'}</td>
                <td>${lic.expires_at || 'UNLIMITED'}</td>
                <td class="${lic.status === 'ACTIVE' ? 'success' : 'warning'}">${lic.status}</td>
                <td><span class="stat-number" style="font-size: 16px;">${lic.usage_count || 0}</span></td>
                <td><button class="btn-danger" onclick="event.stopPropagation(); deletePermanentLicense('${lic.license_key}')">DELETE</button></td>
            `;
        });
    }

    async function loadCustomActivations() {
        const res = await fetch(SERVER_URL + '/api/admin/get-custom-activations', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({admin_key: ADMIN_KEY})
        });
        const data = await res.json();
        const table = document.getElementById('activations-table');
        table.innerHTML = `<tr><th>LICENSE KEY</th><th>USERNAME</th><th>PASSWORD</th><th>HWID</th><th>EXPIRES</th><th>STATUS</th><th>USAGE</th><th>ACTION</th></tr>`;
        data.activations.forEach(act => {
            const row = table.insertRow(-1);
            row.className = 'clickable-row';
            row.onclick = () => showUsageDetails(act.license_key);
            row.innerHTML = `
                <td>${act.license_key}</td>
                <td>${act.username}</td>
                <td>${act.password}</td>
                <td>${act.hwid || '-'}</td>
                <td>${act.expires_at || 'UNLIMITED'}</td>
                <td class="${act.status === 'ACTIVE' ? 'success' : 'warning'}">${act.status}</td>
                <td><span class="stat-number" style="font-size: 16px;">${act.usage_count || 0}</span></td>
                <td><button class="btn-danger" onclick="event.stopPropagation(); deleteCustomActivation('${act.license_key}')">DELETE</button></td>
            `;
        });
    }

    async function loadUsageAnalytics() {
        const res = await fetch(SERVER_URL + '/api/admin/get-usage-analytics', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({admin_key: ADMIN_KEY})
        });
        const data = await res.json();
        const tbody = document.getElementById('usage-table-body');
        tbody.innerHTML = '';
        
        data.licenses.forEach(lic => {
            const row = tbody.insertRow(-1);
            row.className = 'clickable-row';
            row.onclick = () => showUsageDetails(lic.license_key);
            row.innerHTML = `
                <td><strong>${lic.license_key}</strong></td>
                <td>${lic.type}</td>
                <td>${lic.total_usage}</td>
                <td>${lic.activations}</td>
                <td>${lic.verifications}</td>
                <td>${lic.logins}</td>
                <td>${lic.last_used || 'Never'}</td>
                <td>${lic.unique_hwids}</td>
            `;
        });
    }

    async function showUsageDetails(licenseKey) {
        const res = await fetch(SERVER_URL + '/api/admin/get-license-usage', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({admin_key: ADMIN_KEY, license_key: licenseKey})
        });
        const data = await res.json();
        
        const modal = document.getElementById('usageModal');
        const modalContent = document.getElementById('modal-content');
        document.getElementById('modal-title').innerHTML = `📊 Usage Details: ${licenseKey}`;
        
        modalContent.innerHTML = `
            <div class="usage-stats">
                <div class="usage-card">
                    <strong>Total Usage</strong><br>
                    <span class="stat-number" style="font-size: 24px;">${data.stats.total_usage}</span>
                </div>
                <div class="usage-card">
                    <strong>Activations</strong><br>
                    <span class="stat-number" style="font-size: 24px;">${data.stats.total_activations}</span>
                </div>
                <div class="usage-card">
                    <strong>Verifications</strong><br>
                    <span class="stat-number" style="font-size: 24px;">${data.stats.total_verifications}</span>
                </div>
                <div class="usage-card">
                    <strong>Logins</strong><br>
                    <span class="stat-number" style="font-size: 24px;">${data.stats.total_logins}</span>
                </div>
                <div class="usage-card">
                    <strong>Unique HWIDs</strong><br>
                    <span class="stat-number" style="font-size: 24px;">${data.stats.unique_hwids.length}</span>
                </div>
            </div>
            
            <h4>📅 First Used: ${data.stats.first_used || 'Never'}</h4>
            <h4>⏰ Last Used: ${data.stats.last_used || 'Never'}</h4>
            
            <h4>🖥️ HWIDs Used:</h4>
            <div class="result">
                ${data.stats.unique_hwids.map(hwid => `• ${hwid}`).join('<br>') || 'No HWIDs recorded'}
            </div>
            
            <h4>📈 Daily Usage:</h4>
            <div class="result">
                ${Object.entries(data.stats.daily_usage).map(([date, count]) => `• ${date}: ${count} requests`).join('<br>') || 'No data'}
            </div>
            
            <h4>📊 Recent Events (Last 20):</h4>
            <div class="event-log">
                ${data.stats.recent_events.map(event => `
                    <div class="event-log">
                        [${new Date(event.timestamp).toLocaleString()}] 
                        <strong>${event.event_type.toUpperCase()}</strong>
                        ${event.details.hwid ? ` - HWID: ${event.details.hwid.substring(0, 16)}...` : ''}
                        ${event.details.username ? ` - User: ${event.details.username}` : ''}
                    </div>
                `).join('') || 'No events recorded'}
            </div>
        `;
        
        modal.style.display = 'block';
    }

    function closeModal() {
        document.getElementById('usageModal').style.display = 'none';
    }

    function filterLicenses() {
        const searchTerm = document.getElementById('search-license').value.toLowerCase();
        const rows = document.querySelectorAll('#usage-table-body tr');
        rows.forEach(row => {
            const text = row.textContent.toLowerCase();
            row.style.display = text.includes(searchTerm) ? '' : 'none';
        });
    }

    async function loadMonitorData() {
        const res = await fetch(SERVER_URL + '/api/admin/get-monitor-data', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({admin_key: ADMIN_KEY})
        });
        const data = await res.json();
        document.getElementById('monitor-data').innerHTML = `
            <strong>📊 LICENSE STATUS MONITOR</strong><br><br>
            🔹 TRIAL LICENSES: ${data.stats.trials}<br>
            🔹 PERMANENT LICENSES: ${data.stats.permanent}<br>
            🔹 CUSTOM ACTIVATIONS: ${data.stats.custom}<br>
            🔹 ACTIVE USERS: ${data.stats.active_users}<br>
            🔹 EXPIRED LICENSES: ${data.stats.expired}<br>
            🔹 TOTAL API CALLS: ${data.stats.total_api_calls}<br><br>
            <strong>⏰ CURRENT SERVER TIME:</strong> ${data.server_time}<br>
            <strong>🔄 LAST MONITOR CHECK:</strong> ${data.last_check}<br><br>
            <strong>⚠️ EXPIRING SOON (Next 24h):</strong><br>
            ${data.expiring_soon.map(e => `  • ${e.license_key} - Expires: ${e.expires_at}`).join('<br>') || '  None'}
        `;
    }

    async function deleteTrial(key) {
        if(!confirm('Delete this trial?')) return;
        await fetch(SERVER_URL + '/api/admin/delete-trial', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({admin_key: ADMIN_KEY, license_key: key})
        });
        loadTrials();
        loadStats();
    }

    async function deletePermanentLicense(key) {
        if(!confirm('Delete this permanent license?')) return;
        await fetch(SERVER_URL + '/api/admin/delete-permanent-license', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({admin_key: ADMIN_KEY, license_key: key})
        });
        loadPermanentLicenses();
        loadStats();
    }

    async function deleteCustomActivation(key) {
        if(!confirm('Delete this activation?')) return;
        await fetch(SERVER_URL + '/api/admin/delete-custom-activation', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({admin_key: ADMIN_KEY, license_key: key})
        });
        loadCustomActivations();
        loadStats();
    }

    // Auto-refresh stats every 30 seconds
    setInterval(() => {
        if(document.getElementById('panel').classList.contains('active')) {
            loadStats();
        }
    }, 30000);
    
    // Close modal when clicking outside
    window.onclick = function(event) {
        const modal = document.getElementById('usageModal');
        if (event.target == modal) {
            modal.style.display = 'none';
        }
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

@app.route('/api/admin/get-stats', methods=['POST'])
def get_stats():
    if request.get_json().get("admin_key") != ADMIN_KEY:
        return jsonify({"status": "denied"}), 403
    
    total_usage = sum(len(logs) for logs in USAGE_LOGS.values())
    
    return jsonify({
        "trials": len(TRIAL_LICENSES),
        "permanent": len(PERMANENT_LICENSES),
        "custom": len(CUSTOM_ACTIVATIONS),
        "total_usage": total_usage
    }), 200

@app.route('/api/admin/get-usage-analytics', methods=['POST'])
def get_usage_analytics():
    if request.get_json().get("admin_key") != ADMIN_KEY:
        return jsonify({"status": "denied"}), 403
    
    all_licenses = []
    
    # Combine all license types
    for key in TRIAL_LICENSES:
        stats = get_usage_stats(key)
        all_licenses.append({
            "license_key": key,
            "type": "Trial",
            "total_usage": stats["total_usage"],
            "activations": stats["total_activations"],
            "verifications": stats["total_verifications"],
            "logins": stats["total_logins"],
            "last_used": stats["last_used"].isoformat() if stats["last_used"] else None,
            "unique_hwids": len(stats["unique_hwids"])
        })
    
    for key in PERMANENT_LICENSES:
        stats = get_usage_stats(key)
        all_licenses.append({
            "license_key": key,
            "type": "Permanent",
            "total_usage": stats["total_usage"],
            "activations": stats["total_activations"],
            "verifications": stats["total_verifications"],
            "logins": stats["total_logins"],
            "last_used": stats["last_used"].isoformat() if stats["last_used"] else None,
            "unique_hwids": len(stats["unique_hwids"])
        })
    
    for key in CUSTOM_ACTIVATIONS:
        stats = get_usage_stats(key)
        all_licenses.append({
            "license_key": key,
            "type": "Custom",
            "total_usage": stats["total_usage"],
            "activations": stats["total_activations"],
            "verifications": stats["total_verifications"],
            "logins": stats["total_logins"],
            "last_used": stats["last_used"].isoformat() if stats["last_used"] else None,
            "unique_hwids": len(stats["unique_hwids"])
        })
    
    # Sort by total usage (most used first)
    all_licenses.sort(key=lambda x: x["total_usage"], reverse=True)
    
    return jsonify({"licenses": all_licenses}), 200

@app.route('/api/admin/get-license-usage', methods=['POST'])
def get_license_usage():
    if request.get_json().get("admin_key") != ADMIN_KEY:
        return jsonify({"status": "denied"}), 403
    
    license_key = request.get_json().get("license_key", "")
    stats = get_usage_stats(license_key)
    
    # Convert datetime objects to strings
    if stats["first_used"]:
        stats["first_used"] = stats["first_used"].isoformat()
    if stats["last_used"]:
        stats["last_used"] = stats["last_used"].isoformat()
    
    return jsonify({"stats": stats}), 200

@app.route('/api/admin/generate-trial', methods=['POST'])
def generate_trial():
    data = request.get_json()
    if data.get("admin_key") != ADMIN_KEY: 
        return jsonify({"status": "denied"}), 403
    dur = int(data.get("duration_hours", 3))
    lic = f"JEPFX-TRIAL-{uuid.uuid4().hex[:8].upper()}"
    user = f"TRIAL-{uuid.uuid4().hex[:6].upper()}"
    pwd = uuid.uuid4().hex[:10].upper()

    TRIAL_LICENSES[lic] = {
        "type": "trial",
        "hwid": "",
        "duration_hours": dur,
        "start_time": None,
        "expires_at": None,
        "activated_at": None
    }
    TRIAL_USERS[user] = {"password": pwd, "linked_license": lic}
    save_data()
    return jsonify({
        "trial_license": lic,
        "trial_username": user,
        "trial_password": pwd,
        "duration_hours": dur
    }), 200

@app.route('/api/admin/create-custom-activation', methods=['POST'])
def create_custom_activation():
    data = request.get_json()
    if data.get("admin_key") != ADMIN_KEY:
        return jsonify({"status": "denied"}), 403
    
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    license_key = data.get("license_key", "").strip().upper()
    duration_type = data.get("duration_type", "hours")
    duration_value = data.get("duration_value", 0)
    
    if not username or not password or not license_key:
        return jsonify({"error": "Missing required fields"}), 400
    
    # Calculate expiry
    now = datetime.utcnow()
    expires_at = None
    
    if duration_type != "unlimited" and duration_value > 0:
        if duration_type == "hours":
            expires_at = now + timedelta(hours=duration_value)
        elif duration_type == "days":
            expires_at = now + timedelta(days=duration_value)
        elif duration_type == "months":
            expires_at = now + timedelta(days=duration_value * 30)
        elif duration_type == "years":
            expires_at = now + timedelta(days=duration_value * 365)
    
    # Store custom activation
    CUSTOM_ACTIVATIONS[license_key] = {
        "username": username,
        "password": password,
        "license_key": license_key,
        "hwid": "",
        "expires_at": expires_at.isoformat() if expires_at else None,
        "created_at": now.isoformat(),
        "activated": False
    }
    
    save_data()
    return jsonify({
        "status": "created",
        "expires_at": expires_at.isoformat() if expires_at else "UNLIMITED"
    }), 200

@app.route('/api/admin/create-permanent-license', methods=['POST'])
def create_permanent_license():
    data = request.get_json()
    if data.get("admin_key") != ADMIN_KEY:
        return jsonify({"status": "denied"}), 403
    
    license_key = data.get("license_key", "").strip().upper()
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    expires_at_str = data.get("expires_at", "")
    
    if not license_key:
        return jsonify({"error": "License key required"}), 400
    
    expires_at = None
    if expires_at_str:
        try:
            expires_at = datetime.fromisoformat(expires_at_str)
        except:
            pass
    
    PERMANENT_LICENSES[license_key] = {
        "type": "permanent",
        "username": username if username else None,
        "password": password if password else None,
        "hwid": "",
        "expires_at": expires_at.isoformat() if expires_at else None,
        "created_at": datetime.utcnow().isoformat()
    }
    
    save_data()
    return jsonify({"status": "created"}), 200

@app.route('/api/admin/get-all-trials', methods=['POST'])
def get_all():
    if request.get_json().get("admin_key") != ADMIN_KEY:
        return jsonify({"status": "denied"}), 403
    now = datetime.utcnow()
    list_trials = []
    for k, v in TRIAL_LICENSES.items():
        status = "NOT ACTIVATED"
        rem = "-"
        if v.get("expires_at"):
            exp = datetime.fromisoformat(v["expires_at"])
            if exp > now:
                status = "✅ ACTIVE"
                diff = exp - now
                rem = f"{diff.days}d {diff.seconds//3600}h {(diff.seconds//60)%60}m"
            else:
                status = "❌ EXPIRED"
                rem = "EXPIRED"
        
        usage_count = len(USAGE_LOGS.get(k, []))
        
        list_trials.append({
            "license_key": k,
            "duration_hours": f"{v['duration_hours']}h",
            "hwid": v.get("hwid") or "-",
            "activated_at": v.get("activated_at") or "-",
            "expires_at": v.get("expires_at") or "-",
            "status": status,
            "remaining": rem,
            "usage_count": usage_count
        })
    return jsonify({"trials": list_trials}), 200

@app.route('/api/admin/get-permanent-licenses', methods=['POST'])
def get_permanent_licenses():
    if request.get_json().get("admin_key") != ADMIN_KEY:
        return jsonify({"status": "denied"}), 403
    
    now = datetime.utcnow()
    licenses_list = []
    for k, v in PERMANENT_LICENSES.items():
        status = "ACTIVE"
        if v.get("expires_at"):
            exp = datetime.fromisoformat(v["expires_at"])
            if now > exp:
                status = "EXPIRED"
        
        usage_count = len(USAGE_LOGS.get(k, []))
        
        licenses_list.append({
            "license_key": k,
            "username": v.get("username"),
            "hwid": v.get("hwid") or "-",
            "expires_at": v.get("expires_at") or "UNLIMITED",
            "status": status,
            "usage_count": usage_count
        })
    
    return jsonify({"licenses": licenses_list}), 200

@app.route('/api/admin/get-custom-activations', methods=['POST'])
def get_custom_activations():
    if request.get_json().get("admin_key") != ADMIN_KEY:
        return jsonify({"status": "denied"}), 403
    
    now = datetime.utcnow()
    activations_list = []
    for k, v in CUSTOM_ACTIVATIONS.items():
        status = "ACTIVE"
        if v.get("expires_at"):
            exp = datetime.fromisoformat(v["expires_at"])
            if now > exp:
                status = "EXPIRED"
        
        usage_count = len(USAGE_LOGS.get(k, []))
        
        activations_list.append({
            "license_key": k,
            "username": v.get("username"),
            "password": v.get("password"),
            "hwid": v.get("hwid") or "-",
            "expires_at": v.get("expires_at") or "UNLIMITED",
            "status": status,
            "usage_count": usage_count
        })
    
    return jsonify({"activations": activations_list}), 200

@app.route('/api/admin/get-monitor-data', methods=['POST'])
def get_monitor_data():
    if request.get_json().get("admin_key") != ADMIN_KEY:
        return jsonify({"status": "denied"}), 403
    
    now = datetime.utcnow()
    expiring_soon = []
    active_users = set()
    
    # Check trials
    for k, v in TRIAL_LICENSES.items():
        if v.get("expires_at"):
            exp = datetime.fromisoformat(v["expires_at"])
            if now < exp < (now + timedelta(hours=24)):
                expiring_soon.append({"license_key": k, "expires_at": v["expires_at"]})
            if v.get("hwid"):
                active_users.add(v["hwid"])
    
    # Check permanents
    for k, v in PERMANENT_LICENSES.items():
        if v.get("expires_at"):
            exp = datetime.fromisoformat(v["expires_at"])
            if now < exp < (now + timedelta(hours=24)):
                expiring_soon.append({"license_key": k, "expires_at": v["expires_at"]})
            if v.get("hwid"):
                active_users.add(v["hwid"])
    
    # Check custom activations
    expired_count = 0
    for k, v in CUSTOM_ACTIVATIONS.items():
        if v.get("expires_at"):
            exp = datetime.fromisoformat(v["expires_at"])
            if now < exp < (now + timedelta(hours=24)):
                expiring_soon.append({"license_key": k, "expires_at": v["expires_at"]})
            elif now > exp:
                expired_count += 1
            if v.get("hwid"):
                active_users.add(v["hwid"])
    
    total_api_calls = sum(len(logs) for logs in USAGE_LOGS.values())
    
    return jsonify({
        "stats": {
            "trials": len(TRIAL_LICENSES),
            "permanent": len(PERMANENT_LICENSES),
            "custom": len(CUSTOM_ACTIVATIONS),
            "active_users": len(active_users),
            "expired": expired_count,
            "total_api_calls": total_api_calls
        },
        "server_time": now.isoformat(),
        "last_check": now.isoformat(),
        "expiring_soon": expiring_soon
    }), 200

@app.route('/api/admin/delete-trial', methods=['POST'])
def delete_trial():
    data = request.get_json()
    if data.get("admin_key") != ADMIN_KEY:
        return jsonify({"status": "denied"}), 403
    key = data.get("license_key", "")
    if key in TRIAL_LICENSES:
        for user, user_data in list(TRIAL_USERS.items()):
            if user_data.get("linked_license") == key:
                del TRIAL_USERS[user]
        del TRIAL_LICENSES[key]
        # Keep usage logs for history
        save_data()
        return jsonify({"status": "deleted"}), 200
    return jsonify({"status": "not_found"}), 404

@app.route('/api/admin/delete-permanent-license', methods=['POST'])
def delete_permanent_license():
    data = request.get_json()
    if data.get("admin_key") != ADMIN_KEY:
        return jsonify({"status": "denied"}), 403
    key = data.get("license_key", "")
    if key in PERMANENT_LICENSES:
        del PERMANENT_LICENSES[key]
        save_data()
        return jsonify({"status": "deleted"}), 200
    return jsonify({"status": "not_found"}), 404

@app.route('/api/admin/delete-custom-activation', methods=['POST'])
def delete_custom_activation():
    data = request.get_json()
    if data.get("admin_key") != ADMIN_KEY:
        return jsonify({"status": "denied"}), 403
    key = data.get("license_key", "")
    if key in CUSTOM_ACTIVATIONS:
        del CUSTOM_ACTIVATIONS[key]
        save_data()
        return jsonify({"status": "deleted"}), 200
    return jsonify({"status": "not_found"}), 404

# ==================================================
# 🔑 ACTIVATE & VERIFY — Updated with usage tracking
# ==================================================
@app.route('/api/activate', methods=['POST'])
def activate():
    data = request.get_json()
    key = data.get("license_key", "").strip().upper()
    hwid = data.get("hardware_id", "").strip()
    now = datetime.utcnow()

    # Check Custom Activations first
    if key in CUSTOM_ACTIVATIONS:
        activation = CUSTOM_ACTIVATIONS[key]
        
        # Check expiry
        if activation.get("expires_at"):
            exp_time = datetime.fromisoformat(activation["expires_at"])
            if now > exp_time:
                log_usage(key, "activation", {"status": "expired", "hwid": hwid})
                return jsonify({"status": "expired", "msg": "License has expired"}), 403
        
        # Check if already activated on different HWID
        if activation["hwid"] and activation["hwid"] != hwid:
            log_usage(key, "activation", {"status": "blocked", "hwid": hwid})
            return jsonify({"status": "blocked", "msg": "License used on another PC"}), 403
        
        # Activate if not activated
        if not activation["hwid"]:
            activation["hwid"] = hwid
            activation["activated"] = True
            activation["activated_at"] = now.isoformat()
            save_data()
        
        # Add to valid users
        if activation["username"] not in VALID_USERS:
            VALID_USERS[activation["username"]] = activation["password"]
        
        log_usage(key, "activation", {"status": "success", "hwid": hwid, "username": activation["username"]})
        
        return jsonify({
            "status": "activated",
            "msg": f"Activated successfully! Expires: {activation['expires_at'] or 'NEVER'}"
        }), 200

    # Check Permanent Licenses
    if key in PERMANENT_LICENSES:
        lic = PERMANENT_LICENSES[key]
        
        if lic.get("expires_at"):
            exp_time = datetime.fromisoformat(lic["expires_at"])
            if now > exp_time:
                log_usage(key, "activation", {"status": "expired", "hwid": hwid})
                return jsonify({"status": "expired", "msg": "License has expired"}), 403
        
        if lic["hwid"] and lic["hwid"] != hwid:
            log_usage(key, "activation", {"status": "blocked", "hwid": hwid})
            return jsonify({"status": "blocked", "msg": "License used on another PC"}), 403
        
        if not lic["hwid"]:
            lic["hwid"] = hwid
            save_data()
        
        log_usage(key, "activation", {"status": "success", "hwid": hwid})
        return jsonify({"status": "activated"}), 200

    # Check Original Licenses
    if key in LICENSES:
        lic = LICENSES[key]
        if lic["type"] == "unlimited":
            if hwid not in lic["hwid"]:
                lic["hwid"].append(hwid)
            log_usage(key, "activation", {"status": "success", "hwid": hwid})
            return jsonify({"status": "activated"}), 200
        if lic["type"] == "single":
            if lic["hwid"] == "":
                lic["hwid"] = hwid
                log_usage(key, "activation", {"status": "success", "hwid": hwid})
                return jsonify({"status": "activated"}), 200
            elif lic["hwid"] == hwid:
                log_usage(key, "activation", {"status": "success", "hwid": hwid})
                return jsonify({"status": "activated"}), 200
            else:
                log_usage(key, "activation", {"status": "blocked", "hwid": hwid})
                return jsonify({"status": "blocked", "msg": "Used on another PC"}), 403

    # Check Trial Licenses
    if key in TRIAL_LICENSES:
        lic = TRIAL_LICENSES[key]
        if lic["start_time"] is None:
            lic["start_time"] = now.isoformat()
            lic["activated_at"] = now.isoformat()
            lic["expires_at"] = (now + timedelta(hours=lic["duration_hours"])).isoformat()
            lic["hwid"] = hwid
            save_data()
            log_usage(key, "activation", {"status": "success", "hwid": hwid, "duration": lic["duration_hours"]})
            return jsonify({
                "status": "activated",
                "msg": f"Trial activated! Expires in {lic['duration_hours']} hours"
            }), 200
        else:
            exp_time = datetime.fromisoformat(str(lic["expires_at"]))
            if now > exp_time:
                log_usage(key, "activation", {"status": "expired", "hwid": hwid})
                return jsonify({"status": "expired", "msg": "Trial already expired"}), 403
            if lic["hwid"] == hwid:
                log_usage(key, "activation", {"status": "success", "hwid": hwid})
                return jsonify({"status": "activated"}), 200
            else:
                log_usage(key, "activation", {"status": "blocked", "hwid": hwid})
                return jsonify({"status": "blocked", "msg": "Trial used on another PC"}), 403

    return jsonify({"status": "invalid", "msg": "License key does not exist"}), 403

@app.route('/api/verify-license', methods=['POST'])
def verify():
    data = request.get_json()
    hwid = data.get("hwid", "")
    key_hash = data.get("hash", "")
    now = datetime.utcnow()

    # Verify Custom Activations
    for key, activation in CUSTOM_ACTIVATIONS.items():
        if hashlib.sha256(key.encode()).hexdigest() == key_hash:
            if activation.get("expires_at"):
                exp_time = datetime.fromisoformat(activation["expires_at"])
                if now > exp_time:
                    log_usage(key, "verification", {"status": "expired", "hwid": hwid})
                    return jsonify({"expired": True}), 403
            if activation["hwid"] == hwid:
                log_usage(key, "verification", {"status": "success", "hwid": hwid})
                return jsonify({"ok": True}), 200
            log_usage(key, "verification", {"status": "invalid", "hwid": hwid})
            return jsonify({"invalid": True}), 403

    # Verify Permanent Licenses
    for key, lic in PERMANENT_LICENSES.items():
        if hashlib.sha256(key.encode()).hexdigest() == key_hash:
            if lic.get("expires_at"):
                exp_time = datetime.fromisoformat(lic["expires_at"])
                if now > exp_time:
                    log_usage(key, "verification", {"status": "expired", "hwid": hwid})
                    return jsonify({"expired": True}), 403
            if lic["hwid"] == hwid:
                log_usage(key, "verification", {"status": "success", "hwid": hwid})
                return jsonify({"ok": True}), 200
            log_usage(key, "verification", {"status": "invalid", "hwid": hwid})
            return jsonify({"invalid": True}), 403

    # Verify original licenses
    for key, lic in LICENSES.items():
        if hashlib.sha256(key.encode()).hexdigest() == key_hash:
            if lic["type"] == "unlimited" and hwid in lic["hwid"]:
                log_usage(key, "verification", {"status": "success", "hwid": hwid})
                return jsonify({"ok": True}), 200
            if lic["type"] == "single" and lic["hwid"] == hwid:
                log_usage(key, "verification", {"status": "success", "hwid": hwid})
                return jsonify({"ok": True}), 200
            log_usage(key, "verification", {"status": "invalid", "hwid": hwid})
            return jsonify({"invalid": True}), 403

    # Verify trial licenses
    for key, lic in TRIAL_LICENSES.items():
        if hashlib.sha256(key.encode()).hexdigest() == key_hash:
            if not lic.get("expires_at"):
                log_usage(key, "verification", {"status": "invalid", "hwid": hwid})
                return jsonify({"invalid": True}), 403
                
            exp_time = datetime.fromisoformat(str(lic["expires_at"]))
            if lic["hwid"] == hwid and now < exp_time:
                log_usage(key, "verification", {"status": "success", "hwid": hwid})
                return jsonify({"ok": True}), 200
            if now > exp_time:
                log_usage(key, "verification", {"status": "expired", "hwid": hwid})
                return jsonify({"expired": True}), 403
            log_usage(key, "verification", {"status": "invalid", "hwid": hwid})
            return jsonify({"invalid": True}), 403

    return jsonify({"invalid": True}), 403

@app.route('/api/validate-user', methods=['POST'])
def validate_user():
    username = request.get_json().get("username", "")
    
    # Find which license this username belongs to
    for key, activation in CUSTOM_ACTIVATIONS.items():
        if activation["username"] == username:
            log_usage(key, "validation", {"status": "success", "username": username})
            return jsonify({"ok": True}), 200
    
    for key, user_data in TRIAL_USERS.items():
        if key == username:
            license_key = user_data.get("linked_license")
            if license_key:
                log_usage(license_key, "validation", {"status": "success", "username": username})
            return jsonify({"ok": True}), 200
    
    if username in VALID_USERS:
        # Find original license key
        for key in LICENSES:
            log_usage(key, "validation", {"status": "success", "username": username})
            break
        return jsonify({"ok": True}), 200
    
    return "", 403

@app.route('/api/check-password', methods=['POST'])
def check_pass():
    data = request.get_json()
    username = data.get("username", "")
    password = data.get("password", "")
    
    # Check custom activations
    for key, activation in CUSTOM_ACTIVATIONS.items():
        if activation["username"] == username and activation["password"] == password:
            log_usage(key, "login", {"status": "success", "username": username})
            return jsonify({"ok": True}), 200
    
    # Check trial users
    for user, user_data in TRIAL_USERS.items():
        if user == username and user_data["password"] == password:
            license_key = user_data.get("linked_license")
            if license_key:
                log_usage(license_key, "login", {"status": "success", "username": username})
            return jsonify({"ok": True}), 200
    
    # Check permanent users
    for key, lic in PERMANENT_LICENSES.items():
        if lic.get("username") == username and lic.get("password") == password:
            log_usage(key, "login", {"status": "success", "username": username})
            return jsonify({"ok": True}), 200
    
    if username in VALID_USERS and VALID_USERS[username] == password:
        # Find original license key
        for key in LICENSES:
            log_usage(key, "login", {"status": "success", "username": username})
            break
        return jsonify({"ok": True}), 200
    
    return "", 403

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)