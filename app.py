from flask import Flask, request, jsonify, render_template_string, Response, redirect, url_for
import hashlib
from datetime import datetime, timedelta
import uuid
import json
import os
import threading
import time
import secrets
import string

app = Flask(__name__)

# ==================================================
# 📂 PERMANENT DATA SAVE
# ==================================================
DATA_FILE = "server_data.json"

# ==================================================
# 🔗 REGISTRATION LINKS
# ==================================================
REGISTRATION_LINKS = {}  # {link_token: {type, duration_value, duration_type, max_devices, created_by, created_at, used, used_by, expires_at}}

# ==================================================
# 🎨 THEME SETTINGS
# ==================================================
THEMES = {
    "dark": {
        "bg_gradient": "linear-gradient(135deg, #0f0c29, #302b63, #24243e)",
        "primary": "#7C3AED",
        "secondary": "#10B981",
        "danger": "#EF4444",
        "warning": "#F59E0B",
        "text": "#FFFFFF",
        "text_secondary": "#AAAAAA",
        "card_bg": "rgba(255,255,255,0.1)",
        "input_bg": "rgba(0,0,0,0.3)",
        "border": "rgba(255,255,255,0.2)"
    },
    "light": {
        "bg_gradient": "linear-gradient(135deg, #f5f7fa, #c3cfe2)",
        "primary": "#6D28D9",
        "secondary": "#059669",
        "danger": "#DC2626",
        "warning": "#D97706",
        "text": "#1F2937",
        "text_secondary": "#6B7280",
        "card_bg": "rgba(255,255,255,0.9)",
        "input_bg": "rgba(255,255,255,0.8)",
        "border": "rgba(0,0,0,0.1)"
    },
    "blue": {
        "bg_gradient": "linear-gradient(135deg, #1e3c72, #2a5298)",
        "primary": "#3B82F6",
        "secondary": "#22C55E",
        "danger": "#EF4444",
        "warning": "#F59E0B",
        "text": "#FFFFFF",
        "text_secondary": "#CBD5E1",
        "card_bg": "rgba(59,130,246,0.2)",
        "input_bg": "rgba(0,0,0,0.3)",
        "border": "rgba(59,130,246,0.3)"
    },
    "green": {
        "bg_gradient": "linear-gradient(135deg, #0f2027, #203a43, #2c5364)",
        "primary": "#10B981",
        "secondary": "#34D399",
        "danger": "#EF4444",
        "warning": "#F59E0B",
        "text": "#FFFFFF",
        "text_secondary": "#A7F3D0",
        "card_bg": "rgba(16,185,129,0.15)",
        "input_bg": "rgba(0,0,0,0.3)",
        "border": "rgba(16,185,129,0.3)"
    },
    "midnight": {
        "bg_gradient": "linear-gradient(135deg, #000428, #004e92)",
        "primary": "#8B5CF6",
        "secondary": "#A78BFA",
        "danger": "#F87171",
        "warning": "#FBBF24",
        "text": "#FFFFFF",
        "text_secondary": "#C4B5FD",
        "card_bg": "rgba(139,92,246,0.15)",
        "input_bg": "rgba(0,0,0,0.4)",
        "border": "rgba(139,92,246,0.3)"
    }
}

CURRENT_THEME = "dark"

def get_theme_css():
    theme = THEMES.get(CURRENT_THEME, THEMES["dark"])
    return f"""
    :root {{
        --bg-gradient: {theme["bg_gradient"]};
        --primary: {theme["primary"]};
        --secondary: {theme["secondary"]};
        --danger: {theme["danger"]};
        --warning: {theme["warning"]};
        --text: {theme["text"]};
        --text-secondary: {theme["text_secondary"]};
        --card-bg: {theme["card_bg"]};
        --input-bg: {theme["input_bg"]};
        --border: {theme["border"]};
    }}
    body {{ background: var(--bg-gradient); color: var(--text); }}
    .card, .stat-card, .result-box, .modal-content, .login-box {{ background: var(--card_bg); backdrop-filter: blur(10px); }}
    input, select, textarea {{ background: var(--input-bg) !important; color: var(--text) !important; border-color: var(--border); }}
    select option {{ background: #1a1a2e; color: #ffffff; }}
    button {{ background: var(--primary); }}
    button:hover {{ filter: brightness(1.1); }}
    .tab {{ background: rgba(255,255,255,0.1); color: var(--text); }}
    .tab.active {{ background: var(--primary); }}
    .stat-card:hover {{ transform: translateY(-5px); transition: 0.3s; }}
    th {{ background: {theme["primary"]}40; }}
    tr:hover {{ background: rgba(255,255,255,0.05); }}
    """
    
THEME_SELECTOR_HTML = """
<div style="position: fixed; bottom: 20px; right: 20px; z-index: 1000;">
    <select id="themeSelect" onchange="changeTheme(this.value)" style="padding: 8px 15px; border-radius: 20px; background: var(--card-bg); color: var(--text); border: 1px solid var(--border); cursor: pointer;">
        <option value="dark" style="background:#0f0c29">🌙 Dark</option>
        <option value="light" style="background:#f5f7fa; color:#000">☀️ Light</option>
        <option value="blue" style="background:#1e3c72">🔵 Blue</option>
        <option value="green" style="background:#0f2027">🌿 Green</option>
        <option value="midnight" style="background:#000428">🌌 Midnight</option>
    </select>
</div>
<script>
function changeTheme(theme) {
    fetch('/api/set-theme', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({theme: theme})
    }).then(() => location.reload());
}
document.getElementById('themeSelect').value = '""" + CURRENT_THEME + """';
</script>
"""

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

ADMINS = {}
MODERATORS = {}

# ==================================================
# 📝 LICENSES & USERS
# ==================================================
PERMANENT_LICENSES = {}
CUSTOM_ACTIVATIONS = {}
TRIAL_LICENSES = {}
TRIAL_USERS = {}
USAGE_LOGS = {}

# ==================================================
# 📜 LICENSE HISTORY
# ==================================================
LICENSE_HISTORY = []

# ==================================================
# 📨 USER REQUESTS
# ==================================================
USER_REQUESTS = []

VALID_USERS = {
    "JEPFX": "@JEPFX_1875",
}

# ==================================================
# 💰 CREDIT PRICING
# ==================================================
CREDIT_PRICING = {
    "trial_hour": 2,
    "custom_hour": 2,
    "custom_day": 5,
    "custom_week": 8,
    "custom_month": 50,
    "custom_year": 800,
    "custom_unlimited": 1500,
    "permanent": 500
}

TELEGRAM_CONTACT = "t.me/JEPFX_0"

# ==================================================
# 💾 SAVE / LOAD DATA
# ==================================================
def load_data():
    global TRIAL_LICENSES, TRIAL_USERS, PERMANENT_LICENSES, CUSTOM_ACTIVATIONS, USAGE_LOGS, ADMINS, MODERATORS, VALID_USERS, LICENSE_HISTORY, USER_REQUESTS, CURRENT_THEME, REGISTRATION_LINKS
    
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
                LICENSE_HISTORY = data.get("license_history", [])
                USER_REQUESTS = data.get("user_requests", [])
                CURRENT_THEME = data.get("theme", "dark")
                REGISTRATION_LINKS = data.get("registration_links", {})
            print(f"✅ DATA LOADED: {len(LICENSE_HISTORY)} licenses, {len(USER_REQUESTS)} requests, {len(REGISTRATION_LINKS)} links")
        except Exception as e:
            print(f"⚠️ LOAD ERROR: {e}")
            reset_data()
    else:
        reset_data()

def reset_data():
    global TRIAL_LICENSES, TRIAL_USERS, PERMANENT_LICENSES, CUSTOM_ACTIVATIONS, USAGE_LOGS, ADMINS, MODERATORS, LICENSE_HISTORY, USER_REQUESTS, REGISTRATION_LINKS
    TRIAL_LICENSES = {}
    TRIAL_USERS = {}
    PERMANENT_LICENSES = {}
    CUSTOM_ACTIVATIONS = {}
    USAGE_LOGS = {}
    ADMINS = {}
    MODERATORS = {}
    LICENSE_HISTORY = []
    USER_REQUESTS = []
    REGISTRATION_LINKS = {}
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
        "valid_users": VALID_USERS,
        "license_history": LICENSE_HISTORY,
        "user_requests": USER_REQUESTS,
        "theme": CURRENT_THEME,
        "registration_links": REGISTRATION_LINKS
    }
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=2, default=str)
        print("💾 DATA SAVED SUCCESSFULLY")
    except Exception as e:
        print(f"❌ SAVE ERROR: {e}")

load_data()

# ==================================================
# 🔗 REGISTRATION LINK FUNCTIONS
# ==================================================
def generate_registration_link(license_type, duration_value, duration_type, max_devices, created_by, credits_cost=0):
    """Generate a unique one-time registration link"""
    token = secrets.token_urlsafe(16)
    expires_at = datetime.utcnow() + timedelta(hours=24)  # Links expire in 24 hours
    
    REGISTRATION_LINKS[token] = {
        "license_type": license_type,  # "trial" or "custom"
        "duration_value": duration_value,
        "duration_type": duration_type,  # "hours", "days", "weeks", "months", "years", "unlimited"
        "max_devices": max_devices,
        "created_by": created_by,
        "created_at": datetime.utcnow().isoformat(),
        "expires_at": expires_at.isoformat(),
        "used": False,
        "used_by": None,
        "used_at": None,
        "credits_cost": credits_cost  # Store cost for refund on cancel
    }
    save_data()
    return token

def calculate_credits_cost(license_type, duration_value, duration_type):
    """Calculate how many credits a registration will cost"""
    if license_type == "trial":
        # Fixed pricing by duration hours
        TRIAL_FIXED_CREDITS = {3: 2, 6: 3, 12: 4, 24: 5, 72: 10, 168: 20, 720: 50}
        return TRIAL_FIXED_CREDITS.get(int(duration_value), round(duration_value * 0.1, 2))
    else:  # custom
        if duration_type == "hours":
            return round(duration_value * CREDIT_PRICING["custom_hour"], 2)
        elif duration_type == "days":
            return round(duration_value * CREDIT_PRICING["custom_day"], 2)
        elif duration_type == "weeks":
            return round(duration_value * CREDIT_PRICING["custom_week"], 2)
        elif duration_type == "months":
            return round(duration_value * CREDIT_PRICING["custom_month"], 2)
        elif duration_type == "years":
            return round(duration_value * CREDIT_PRICING["custom_year"], 2)
        elif duration_type == "unlimited":
            return CREDIT_PRICING["custom_unlimited"]
    return 0

# ==================================================
# 📜 LICENSE HISTORY FUNCTION
# ==================================================
def add_to_history(license_key, username, password, license_type, owner, expires_at, details=None):
    history_entry = {
        "license_key": license_key,
        "username": username,
        "password": password,
        "type": license_type,
        "owner": owner,
        "created_at": datetime.utcnow().isoformat(),
        "expires_at": expires_at,
        "details": details or {}
    }
    LICENSE_HISTORY.append(history_entry)
    save_data()

def get_history_by_owner(owner, role):
    if role == "master":
        return LICENSE_HISTORY
    return [h for h in LICENSE_HISTORY if h.get("owner") == owner]

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
    username = data.get("admin_username", "")
    password = data.get("admin_password", "")
    
    if username == MASTER_ADMIN["username"] and password == MASTER_ADMIN["password"]:
        return {"authorized": True, "role": "master", "username": username}
    
    if username in ADMINS and ADMINS[username]["password"] == password:
        return {"authorized": True, "role": "admin", "username": username, "credits": ADMINS[username]["credits"]}
    
    if username in MODERATORS and MODERATORS[username]["password"] == password:
        return {"authorized": True, "role": "moderator", "username": username, "credits": MODERATORS[username]["credits"]}
    
    return {"authorized": False}

def deduct_credits(username, amount):
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
    if role == "master":
        return {
            "trials": TRIAL_LICENSES,
            "custom": CUSTOM_ACTIVATIONS,
            "permanent": PERMANENT_LICENSES
        }
    elif role == "admin":
        filtered_trials = {k: v for k, v in TRIAL_LICENSES.items() if v.get("owner") == owner}
        filtered_custom = {k: v for k, v in CUSTOM_ACTIVATIONS.items() if v.get("owner") == owner}
        return {
            "trials": filtered_trials,
            "custom": filtered_custom,
            "permanent": {}
        }
    else:
        filtered_trials = {k: v for k, v in TRIAL_LICENSES.items() if v.get("owner") == owner}
        return {
            "trials": filtered_trials,
            "custom": {},
            "permanent": {}
        }

def find_license_by_credentials(username, password):
    for key, activation in CUSTOM_ACTIVATIONS.items():
        if activation.get("username") == username and activation.get("password") == password:
            return key, "custom", activation
    
    for user, user_data in TRIAL_USERS.items():
        if user == username and user_data.get("password") == password:
            return user_data.get("linked_license"), "trial", TRIAL_LICENSES.get(user_data.get("linked_license"), {})
    
    for key, lic in PERMANENT_LICENSES.items():
        if lic.get("username") == username and lic.get("password") == password:
            return key, "permanent", lic
    
    return None, None, None

# ==================================================
# 🔍 MONITORING THREAD
# ==================================================
def monitor_expired_licenses():
    while True:
        try:
            now = datetime.utcnow()
            changes_made = False
            
            # Clean up expired registration links — refund if unused
            for token, link in list(REGISTRATION_LINKS.items()):
                if link.get("expires_at"):
                    exp_time = datetime.fromisoformat(link["expires_at"])
                    if now > exp_time:
                        if not link.get("used") and link.get("credits_cost", 0) > 0:
                            add_credits(link["created_by"], link["credits_cost"])
                        del REGISTRATION_LINKS[token]
                        changes_made = True
            
            for key, activation in list(CUSTOM_ACTIVATIONS.items()):
                if activation.get("expires_at") and activation.get("activated", False):
                    exp_time = datetime.fromisoformat(activation["expires_at"])
                    if now > exp_time:
                        del CUSTOM_ACTIVATIONS[key]
                        changes_made = True
            
            for key, lic in list(TRIAL_LICENSES.items()):
                if lic.get("expires_at") and lic.get("activated", False):
                    exp_time = datetime.fromisoformat(lic["expires_at"])
                    if now > exp_time:
                        for user, user_data in list(TRIAL_USERS.items()):
                            if user_data.get("linked_license") == key:
                                del TRIAL_USERS[user]
                        del TRIAL_LICENSES[key]
                        changes_made = True
            
            if changes_made:
                save_data()
        except Exception as e:
            print(f"⚠️ Monitor error: {e}")
        time.sleep(60)

monitor_thread = threading.Thread(target=monitor_expired_licenses, daemon=True)
monitor_thread.start()

# ==================================================
# 🎨 REGISTRATION PAGE HTML
# ==================================================
def get_registration_html(token, link_data):
    license_type = link_data["license_type"]
    duration_type = link_data["duration_type"]
    duration_value = link_data["duration_value"]
    max_devices = link_data["max_devices"]
    
    # Format duration display
    if duration_type == "unlimited":
        duration_display = "UNLIMITED"
    else:
        duration_display = f"{duration_value} {duration_type.upper()}"
    
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>JEPFX • License Registration</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Inter', 'Segoe UI', sans-serif;
        }}
        
        {get_theme_css()}
        
        body {{
            min-height: 100vh;
            transition: all 0.3s ease;
        }}
        
        .container {{
            max-width: 600px;
            margin: 0 auto;
            padding: 40px 20px;
        }}
        
        .header {{
            text-align: center;
            margin-bottom: 40px;
        }}
        
        .header h1 {{
            font-size: 36px;
            font-weight: 800;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
            margin-bottom: 10px;
        }}
        
        .header p {{
            color: var(--text-secondary);
        }}
        
        .card {{
            background: var(--card-bg);
            backdrop-filter: blur(10px);
            border-radius: 24px;
            padding: 32px;
            border: 1px solid var(--border);
            box-shadow: 0 20px 40px rgba(0,0,0,0.2);
        }}
        
        .license-info {{
            background: rgba(124,58,237,0.15);
            border-radius: 16px;
            padding: 20px;
            margin-bottom: 25px;
            border: 1px solid var(--border);
        }}
        
        .info-row {{
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid var(--border);
        }}
        
        .info-row:last-child {{
            border-bottom: none;
        }}
        
        .info-label {{
            color: var(--text-secondary);
            font-weight: 500;
        }}
        
        .info-value {{
            color: var(--primary);
            font-weight: 700;
            font-size: 18px;
        }}
        
        input {{
            width: 100%;
            padding: 14px 16px;
            margin: 12px 0;
            border: 1px solid var(--border);
            border-radius: 12px;
            outline: none;
            font-size: 15px;
            transition: all 0.3s;
        }}
        
        input:focus {{
            border-color: var(--primary);
            box-shadow: 0 0 0 3px rgba(124,58,237,0.2);
        }}
        
        button {{
            width: 100%;
            background: var(--primary);
            color: white;
            padding: 14px;
            border: none;
            border-radius: 12px;
            cursor: pointer;
            font-size: 16px;
            font-weight: 600;
            transition: all 0.3s;
            margin-top: 15px;
        }}
        
        button:hover {{
            transform: translateY(-2px);
            filter: brightness(1.05);
        }}
        
        button:disabled {{
            opacity: 0.6;
            cursor: not-allowed;
        }}
        
        .alert-error {{
            background: rgba(239,68,68,0.15);
            border: 1px solid var(--danger);
            color: var(--danger);
            padding: 12px;
            border-radius: 12px;
            margin: 15px 0;
        }}
        
        .alert-success {{
            background: rgba(16,185,129,0.15);
            border: 1px solid var(--secondary);
            color: var(--secondary);
            padding: 12px;
            border-radius: 12px;
            margin: 15px 0;
        }}
        
        .spinner {{
            border: 3px solid rgba(255,255,255,0.3);
            border-top: 3px solid var(--primary);
            border-radius: 50%;
            width: 20px;
            height: 20px;
            animation: spin 1s linear infinite;
            display: inline-block;
            margin-right: 8px;
        }}
        
        @keyframes spin {{
            0% {{ transform: rotate(0deg); }}
            100% {{ transform: rotate(360deg); }}
        }}
        
        .redirect-notice {{
            text-align: center;
            margin-top: 20px;
            color: var(--text-secondary);
            font-size: 13px;
        }}
        
        .redirect-notice a {{
            color: var(--primary);
            text-decoration: none;
        }}
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1><i class="fas fa-user-plus"></i> License Registration</h1>
        <p>Create your unique license credentials</p>
    </div>
    
    <div class="card">
        <div class="license-info">
            <div class="info-row">
                <span class="info-label"><i class="fas fa-tag"></i> License Type</span>
                <span class="info-value">{license_type.upper()}</span>
            </div>
            <div class="info-row">
                <span class="info-label"><i class="fas fa-clock"></i> Duration</span>
                <span class="info-value">{duration_display}</span>
            </div>
            <div class="info-row">
                <span class="info-label"><i class="fas fa-microchip"></i> Max Devices</span>
                <span class="info-value">{max_devices}</span>
            </div>
        </div>
        
        <form id="registrationForm">
            <input type="text" id="licenseKey" placeholder="License Key *" required>
            <input type="text" id="username" placeholder="Username *" required>
            <input type="password" id="password" placeholder="Password *" required>
            <input type="password" id="confirmPassword" placeholder="Confirm Password *" required>
            <button type="submit" id="registerBtn"><i class="fas fa-check-circle"></i> CREATE LICENSE</button>
        </form>
        
        <div id="result"></div>
        
        <div class="redirect-notice" id="redirectNotice" style="display: none;">
            <i class="fas fa-spinner fa-pulse"></i> Redirecting to license portal...
        </div>
    </div>
</div>

{THEME_SELECTOR_HTML}

<script>
    document.getElementById('registrationForm').addEventListener('submit', async (e) => {{
        e.preventDefault();
        
        const licenseKey = document.getElementById('licenseKey').value.trim().toUpperCase();
        const username = document.getElementById('username').value.trim();
        const password = document.getElementById('password').value;
        const confirmPassword = document.getElementById('confirmPassword').value;
        
        if(!licenseKey || !username || !password) {{
            showError('Please fill in all fields');
            return;
        }}
        
        if(password !== confirmPassword) {{
            showError('Passwords do not match');
            return;
        }}
        
        if(password.length < 4) {{
            showError('Password must be at least 4 characters');
            return;
        }}
        
        const btn = document.getElementById('registerBtn');
        btn.disabled = true;
        btn.innerHTML = '<div class="spinner"></div> Creating license...';
        
        try {{
            const res = await fetch('/api/register-from-link/{token}', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{
                    license_key: licenseKey,
                    username: username,
                    password: password
                }})
            }});
            
            const data = await res.json();
            
            if(data.success) {{
                document.getElementById('result').innerHTML = `
                    <div class="alert-success">
                        <i class="fas fa-check-circle"></i> ${{data.message}}
                    </div>
                `;
                document.getElementById('redirectNotice').style.display = 'block';
                
                setTimeout(() => {{
                    window.location.href = '/user';
                }}, 3000);
            }} else {{
                showError(data.error);
                btn.disabled = false;
                btn.innerHTML = '<i class="fas fa-check-circle"></i> CREATE LICENSE';
            }}
        }} catch(error) {{
            showError('Connection error. Please try again.');
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-check-circle"></i> CREATE LICENSE';
        }}
    }});
    
    function showError(msg) {{
        document.getElementById('result').innerHTML = `
            <div class="alert-error">
                <i class="fas fa-exclamation-triangle"></i> ${{msg}}
            </div>
        `;
        setTimeout(() => {{
            const errorDiv = document.querySelector('.alert-error');
            if(errorDiv) errorDiv.style.opacity = '0';
            setTimeout(() => {{
                document.getElementById('result').innerHTML = '';
            }}, 500);
        }}, 3000);
    }}
</script>
</body>
</html>
"""

# ==================================================
# 🎨 MODERN ADMIN PANEL HTML (with Registration Links)
# ==================================================
def get_admin_html():
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>JEPFX ADMIN PANEL • License Management System</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Inter', 'Segoe UI', sans-serif;
        }}
        
        {get_theme_css()}
        
        body {{
            min-height: 100vh;
            transition: all 0.3s ease;
            scroll-behavior: smooth;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }}
        
        .login-box {{
            max-width: 420px;
            margin: 80px auto;
            padding: 40px;
            border-radius: 24px;
            text-align: center;
            box-shadow: 0 20px 40px rgba(0,0,0,0.3);
            border: 1px solid var(--border);
        }}
        
        .login-box h2 {{
            font-size: 28px;
            margin-bottom: 10px;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
        }}
        
        .login-box input {{
            width: 100%;
            padding: 14px 16px;
            margin: 12px 0;
            border: 1px solid var(--border);
            border-radius: 12px;
            outline: none;
            font-size: 15px;
            transition: all 0.3s;
        }}
        
        .login-box input:focus {{
            border-color: var(--primary);
            box-shadow: 0 0 0 3px rgba(124,58,237,0.2);
        }}
        
        .login-box button {{
            width: 100%;
            padding: 14px;
            border: none;
            border-radius: 12px;
            font-weight: 600;
            font-size: 16px;
            margin-top: 10px;
            cursor: pointer;
            transition: all 0.3s;
        }}
        
        .login-box button:hover {{
            transform: translateY(-2px);
            filter: brightness(1.05);
        }}
        
        .panel {{
            display: none;
        }}
        
        .header {{
            border-radius: 24px;
            padding: 28px 32px;
            margin-bottom: 24px;
            background: var(--card-bg);
            backdrop-filter: blur(10px);
            border: 1px solid var(--border);
        }}
        
        .header h1 {{
            font-size: 28px;
            font-weight: 700;
            letter-spacing: -0.5px;
        }}
        
        .header h1 i {{
            color: var(--primary);
            margin-right: 12px;
        }}
        
        .user-info {{
            display: flex;
            gap: 20px;
            margin-top: 12px;
            flex-wrap: wrap;
        }}
        
        .user-badge {{
            background: rgba(124,58,237,0.2);
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: 500;
        }}
        
        .user-badge i {{
            margin-right: 6px;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .stat-card {{
            padding: 20px;
            border-radius: 20px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s;
            border: 1px solid var(--border);
            backdrop-filter: blur(10px);
            background: var(--card-bg);
        }}
        
        .stat-card i {{
            font-size: 32px;
            color: var(--primary);
            margin-bottom: 10px;
        }}
        
        .stat-number {{
            font-size: 32px;
            font-weight: 800;
            color: var(--primary);
        }}
        
        .stat-label {{
            font-size: 13px;
            color: var(--text-secondary);
            margin-top: 5px;
        }}
        
        .tabs {{
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            margin-bottom: 24px;
        }}
        
        .tab {{
            padding: 12px 24px;
            border-radius: 40px;
            cursor: pointer;
            border: none;
            font-weight: 500;
            font-size: 14px;
            transition: all 0.3s;
            background: var(--card-bg);
            color: var(--text);
            backdrop-filter: blur(5px);
        }}
        
        .tab i {{
            margin-right: 8px;
        }}
        
        .tab:hover {{
            transform: translateY(-2px);
            background: var(--primary);
        }}
        
        .tab.active {{
            background: var(--primary);
            box-shadow: 0 4px 15px rgba(124,58,237,0.3);
        }}
        
        .content {{
            display: none;
            border-radius: 24px;
            padding: 28px;
            background: var(--card-bg);
            backdrop-filter: blur(10px);
            border: 1px solid var(--border);
        }}
        
        .content.active {{
            display: block;
            animation: fadeIn 0.3s ease;
        }}
        
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(10px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        
        .content h2 {{
            font-size: 22px;
            margin-bottom: 20px;
            font-weight: 600;
        }}
        
        .content h2 i {{
            margin-right: 10px;
            color: var(--primary);
        }}
        
        .form-group {{
            margin-bottom: 15px;
        }}
        
        .form-row {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
        }}
        
        input, select, textarea {{
            width: 100%;
            padding: 14px 16px;
            margin: 10px 0;
            border: 1px solid var(--border);
            border-radius: 12px;
            outline: none;
            font-size: 14px;
            transition: all 0.3s;
        }}
        
        input:focus, select:focus, textarea:focus {{
            border-color: var(--primary);
            box-shadow: 0 0 0 3px rgba(124,58,237,0.2);
        }}
        
        button {{
            background: var(--primary);
            color: white;
            padding: 12px 28px;
            border: none;
            border-radius: 12px;
            cursor: pointer;
            font-weight: 600;
            font-size: 14px;
            transition: all 0.3s;
            margin: 5px;
        }}
        
        button:hover {{
            transform: translateY(-2px);
            filter: brightness(1.05);
        }}
        
        .btn-danger {{
            background: var(--danger);
        }}
        
        .btn-success {{
            background: var(--secondary);
        }}
        
        .btn-warning {{
            background: var(--warning);
        }}
        
        .btn-outline {{
            background: transparent;
            border: 1px solid var(--border);
        }}
        
        .btn-outline:hover {{
            background: var(--primary);
            border-color: var(--primary);
        }}
        
        .table-wrapper {{
            overflow-x: auto;
            border-radius: 16px;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
        }}
        
        th, td {{
            padding: 14px 12px;
            text-align: left;
            border-bottom: 1px solid var(--border);
        }}
        
        th {{
            font-weight: 600;
            color: var(--primary);
        }}
        
        .result-box {{
            padding: 20px;
            border-radius: 16px;
            margin-top: 20px;
            border-left: 4px solid var(--primary);
            background: rgba(0,0,0,0.2);
        }}
        
        .modal {{
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.8);
            backdrop-filter: blur(8px);
        }}
        
        .modal-content {{
            margin: 5% auto;
            padding: 28px;
            border-radius: 24px;
            width: 90%;
            max-width: 550px;
            position: relative;
            border: 1px solid var(--border);
        }}
        
        .close {{
            float: right;
            font-size: 28px;
            cursor: pointer;
            transition: 0.3s;
        }}
        
        .close:hover {{
            color: var(--danger);
        }}
        
        .copy-btn {{
            background: var(--primary);
            padding: 4px 10px;
            border-radius: 8px;
            font-size: 10px;
            margin-left: 8px;
            cursor: pointer;
            display: inline-block;
        }}
        
        .badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: 600;
        }}
        
        .badge-active {{ background: var(--secondary); }}
        .badge-expired {{ background: var(--danger); }}
        .badge-warning {{ background: var(--warning); color: #000; }}
        .badge-pending {{ background: var(--warning); color: #000; }}
        .badge-approved {{ background: var(--secondary); }}
        .badge-rejected {{ background: var(--danger); }}
        .badge-used {{ background: var(--secondary); }}
        .badge-unused {{ background: var(--warning); color: #000; }}
        
        .pre-style {{
            font-family: 'Courier New', monospace;
            white-space: pre;
            background: rgba(0,0,0,0.3);
            padding: 16px;
            border-radius: 12px;
            overflow-x: auto;
            font-size: 13px;
            line-height: 1.6;
        }}
        
        .master-only {{
            border-left: 4px solid var(--danger);
            padding: 16px;
            margin: 16px 0;
            border-radius: 12px;
            background: rgba(239,68,68,0.1);
        }}
        
        .link-card {{
            background: rgba(0,0,0,0.2);
            border-radius: 12px;
            padding: 15px;
            margin: 10px 0;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 10px;
        }}
        
        .link-url {{
            font-family: monospace;
            font-size: 12px;
            word-break: break-all;
            flex: 1;
        }}
        
        .spinner {{
            border: 3px solid rgba(255,255,255,0.3);
            border-top: 3px solid var(--primary);
            border-radius: 50%;
            width: 20px;
            height: 20px;
            animation: spin 1s linear infinite;
            display: inline-block;
        }}
        
        @keyframes spin {{
            0% {{ transform: rotate(0deg); }}
            100% {{ transform: rotate(360deg); }}
        }}
        
        @media (max-width: 768px) {{
            .container {{ padding: 12px; }}
            .header {{ padding: 20px; }}
            .tab {{ padding: 8px 16px; font-size: 12px; }}
            .content {{ padding: 20px; }}
            .stats-grid {{ grid-template-columns: repeat(2, 1fr); }}
            .form-row {{ grid-template-columns: 1fr; }}
        }}
        
        ::-webkit-scrollbar {{
            width: 8px;
            height: 8px;
        }}
        
        ::-webkit-scrollbar-track {{
            background: rgba(255,255,255,0.1);
            border-radius: 10px;
        }}
        
        ::-webkit-scrollbar-thumb {{
            background: var(--primary);
            border-radius: 10px;
        }}
    </style>
</head>
<body>
<div class="container">
    <div id="loginScreen" class="login-box">
        <i class="fas fa-shield-alt" style="font-size: 48px; color: var(--primary); margin-bottom: 20px;"></i>
        <h2>JEPFX ADMIN</h2>
        <p style="color: var(--text-secondary); margin-bottom: 20px;">License Management System</p>
        <input type="text" id="loginUsername" placeholder="Username">
        <input type="password" id="loginPassword" placeholder="Password">
        <button onclick="login()"><i class="fas fa-sign-in-alt"></i> LOGIN</button>
        <p id="loginError" style="color: var(--danger); display: none; margin-top: 15px;"><i class="fas fa-exclamation-circle"></i> Invalid credentials!</p>
    </div>
    
    <div id="mainPanel" class="panel">
        <div class="header">
            <h1><i class="fas fa-bolt"></i> JEPFX ADMIN PANEL</h1>
            <div class="user-info">
                <span class="user-badge"><i class="fas fa-user"></i> <span id="currentUser">-</span></span>
                <span class="user-badge"><i class="fas fa-tag"></i> <span id="currentRole">-</span></span>
                <span class="user-badge"><i class="fas fa-coins"></i> Credits: <span id="currentCredits">0</span></span>
            </div>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card" onclick="switchTabTo('myLicenses')">
                <i class="fas fa-flask"></i>
                <div class="stat-number" id="statTrials">0</div>
                <div class="stat-label">Trial Licenses</div>
            </div>
            <div class="stat-card" id="statCustomCard" onclick="switchTabTo('myLicenses')">
                <i class="fas fa-star"></i>
                <div class="stat-number" id="statCustom">0</div>
                <div class="stat-label">Custom Licenses</div>
            </div>
            <div class="stat-card" id="statPermanentCard" style="display: none;" onclick="switchTabTo('myLicenses')">
                <i class="fas fa-gem"></i>
                <div class="stat-number" id="statPermanent">0</div>
                <div class="stat-label">Permanent Licenses</div>
            </div>
            <div class="stat-card" onclick="switchTabTo('history')">
                <i class="fas fa-history"></i>
                <div class="stat-number" id="statHistory">0</div>
                <div class="stat-label">History Entries</div>
            </div>
            <div class="stat-card" onclick="switchTabTo('userRequests')">
                <i class="fas fa-envelope"></i>
                <div class="stat-number" id="statRequests">0</div>
                <div class="stat-label">Pending Requests</div>
            </div>
            <div class="stat-card" onclick="switchTabTo('registrationLinks')">
                <i class="fas fa-link"></i>
                <div class="stat-number" id="statLinks">0</div>
                <div class="stat-label">Active Links</div>
            </div>
        </div>
        
        <div class="tabs">
            <button class="tab active" onclick="switchTab('generateTrial')"><i class="fas fa-dice-d6"></i> TRIAL</button>
            <button class="tab" id="customTab" onclick="switchTab('customActivation')"><i class="fas fa-magic"></i> CUSTOM</button>
            <button class="tab" id="permanentTab" style="display: none;" onclick="switchTab('permanentLicense')"><i class="fas fa-infinity"></i> PERMANENT</button>
            <button class="tab" onclick="switchTab('registrationLinks')"><i class="fas fa-link"></i> REG LINKS</button>
            <button class="tab" onclick="switchTab('myLicenses')"><i class="fas fa-list"></i> MY LICENSES</button>
            <button class="tab" onclick="switchTab('userRequests')"><i class="fas fa-inbox"></i> REQUESTS</button>
            <button class="tab" onclick="switchTab('history')"><i class="fas fa-scroll"></i> HISTORY</button>
            <button class="tab" id="adminTab" style="display: none;" onclick="switchTab('admins')"><i class="fas fa-users-cog"></i> MANAGE</button>
            <button class="tab" onclick="switchTab('changePassword')"><i class="fas fa-key"></i> PASSWORD</button>
            <button class="tab" onclick="switchTab('monitor')"><i class="fas fa-chart-line"></i> MONITOR</button>
        </div>
        
        <div id="generateTrial" class="content active">
            <h2><i class="fas fa-dice-d6"></i> Generate Trial License</h2>
            <div class="form-row">
                <div class="form-group">
                    <select id="trialDuration">
                        <option value="3">3 Hours (2 credits)</option>
                        <option value="6">6 Hours (3 credits)</option>
                        <option value="12">12 Hours (4 credits)</option>
                        <option value="24">1 Day (5 credits)</option>
                        <option value="72">3 Days (10 credits)</option>
                        <option value="168">1 Week (20 credits)</option>
                        <option value="720">1 Month (50 credits)</option>
                    </select>
                </div>
                <div class="form-group">
                    <input type="number" id="maxDevices" placeholder="Max devices (default: 1)" value="1" min="1" max="50">
                </div>
            </div>
            <button onclick="generateTrial()"><i class="fas fa-plus-circle"></i> GENERATE LICENSE</button>
            <div id="trialResult" class="result-box" style="display: none;"></div>
        </div>
        
        <div id="customActivation" class="content">
            <h2><i class="fas fa-magic"></i> Custom Activation (Multi-PC)</h2>
            <div class="form-row">
                <div class="form-group"><input type="text" id="customUsername" placeholder="Username *"></div>
                <div class="form-group"><input type="text" id="customPassword" placeholder="Password *"></div>
            </div>
            <div class="form-row">
                <div class="form-group"><input type="text" id="customLicense" placeholder="License Key *"></div>
                <div class="form-group">
                    <select id="customDurationType">
                        <option value="hours">Hours (2 credits/hour)</option>
                        <option value="days">Days (5 credit/day)</option>
                        <option value="weeks">Weeks (8 credits/week)</option>
                        <option value="months">Months (50 credits/month)</option>
                        <option value="years">Years (800 credits/year)</option>
                        <option value="unlimited">Unlimited (1500 credits)</option>
                    </select>
                </div>
            </div>
            <div class="form-row">
                <div class="form-group"><input type="number" id="customDurationValue" placeholder="Duration value" step="0.5"></div>
                <div class="form-group"><input type="number" id="customMaxDevices" placeholder="Max devices" value="1" min="1" max="100"></div>
            </div>
            <button onclick="createCustomActivation()"><i class="fas fa-save"></i> CREATE ACTIVATION</button>
            <div id="customResult" class="result-box" style="display: none;"></div>
        </div>
        
        <div id="permanentLicense" class="content">
            <h2><i class="fas fa-infinity"></i> Permanent License (50 Credits)</h2>
            <div class="form-row">
                <div class="form-group"><input type="text" id="permLicenseKey" placeholder="License Key *"></div>
                <div class="form-group"><input type="text" id="permUsername" placeholder="Username (optional)"></div>
            </div>
            <div class="form-row">
                <div class="form-group"><input type="text" id="permPassword" placeholder="Password (optional)"></div>
                <div class="form-group"><input type="number" id="permMaxDevices" placeholder="Max devices" value="1" min="1" max="100"></div>
            </div>
            <button onclick="createPermanentLicense()"><i class="fas fa-crown"></i> CREATE PERMANENT</button>
            <div id="permResult" class="result-box" style="display: none;"></div>
        </div>
        
        <div id="registrationLinks" class="content">
            <h2><i class="fas fa-link"></i> Registration Links</h2>
            <div style="background: rgba(0,0,0,0.2); border-radius: 16px; padding: 20px; margin-bottom: 20px; border: 1px solid var(--border);">
                <h3 style="margin-bottom: 15px;"><i class="fas fa-plus-circle"></i> Generate New Registration Link</h3>
                <div style="background: rgba(245,158,11,0.1); border: 1px solid var(--warning); border-radius: 10px; padding: 10px 14px; margin-bottom: 15px; font-size: 13px;">
                    <i class="fas fa-info-circle" style="color: var(--warning);"></i> Links expire in <strong>24 hours</strong>. Unused links are <strong>fully refunded</strong> on cancel or expiry.
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label style="font-size:12px; color:var(--text-secondary); margin-bottom:4px; display:block;">License Type</label>
                        <select id="linkLicenseType" onchange="updateLinkTypeOptions(); updateLinkCostPreview()">
                            <option value="trial">Trial License</option>
                            <option value="custom" id="linkCustomOption">Custom License</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label style="font-size:12px; color:var(--text-secondary); margin-bottom:4px; display:block;">Duration</label>
                        <select id="linkDurationSelect" onchange="updateLinkCostPreview()" style="display:block;">
                            <option value="3">3 Hours (2 credits)</option>
                            <option value="6">6 Hours (3 credits)</option>
                            <option value="12">12 Hours (4 credits)</option>
                            <option value="24">1 Day (5 credits)</option>
                            <option value="72">3 Days (10 credits)</option>
                            <option value="168">1 Week (20 credits)</option>
                            <option value="720">1 Month (50 credits)</option>
                        </select>
                        <select id="linkDurationType" onchange="updateLinkCostPreview()" style="display:none;">
                            <option value="hours">Hours (2 credits/hour)</option>
                            <option value="days">Days (5 credits/day)</option>
                            <option value="weeks">Weeks (8 credits/week)</option>
                            <option value="months">Months (50 credits/month)</option>
                            <option value="years">Years (800 credits/year)</option>
                            <option value="unlimited">Unlimited (1500 credits)</option>
                        </select>
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-group" id="linkDurationValueGroup" style="display:none;">
                        <label style="font-size:12px; color:var(--text-secondary); margin-bottom:4px; display:block;">Duration Value</label>
                        <input type="number" id="linkDurationValue" placeholder="e.g. 1" step="0.5" value="1" oninput="updateLinkCostPreview()">
                    </div>
                    <div class="form-group">
                        <label style="font-size:12px; color:var(--text-secondary); margin-bottom:4px; display:block;">Max Devices</label>
                        <input type="number" id="linkMaxDevices" placeholder="Max devices" value="1" min="1" max="100">
                    </div>
                </div>
                <div id="linkCostPreview" style="background: rgba(124,58,237,0.15); border-radius: 10px; padding: 10px 14px; margin-bottom: 15px; font-size: 13px; display: none;">
                    <i class="fas fa-coins" style="color: var(--primary);"></i> Estimated cost: <strong id="linkCostValue">0</strong> credits
                </div>
                <div style="display: flex; gap: 10px; flex-wrap: wrap;">
                    <button onclick="generateRegistrationLink()" style="flex:1;"><i class="fas fa-link"></i> GENERATE LINK</button>
                </div>
            </div>
            
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                <h3><i class="fas fa-list"></i> Active Registration Links</h3>
                <button onclick="loadRegistrationLinks()" style="width:auto; padding: 8px 16px;"><i class="fas fa-sync-alt"></i> Refresh</button>
            </div>
            <div id="linksList"></div>
        </div>
        
        <div id="myLicenses" class="content">
            <h2><i class="fas fa-list"></i> My Active Licenses</h2>
            <div style="margin-bottom: 20px; display: flex; gap: 10px; flex-wrap: wrap;">
                <button class="btn-outline" onclick="showLicenseType('trials')"><i class="fas fa-flask"></i> Trial</button>
                <button class="btn-outline" id="showCustomBtn" onclick="showLicenseType('custom')"><i class="fas fa-star"></i> Custom</button>
                <button class="btn-outline" id="showPermanentBtn" style="display: none;" onclick="showLicenseType('permanent')"><i class="fas fa-gem"></i> Permanent</button>
            </div>
            <div id="myTrialsList"></div>
            <div id="myCustomList" style="display: none;"></div>
            <div id="myPermanentList" style="display: none;"></div>
        </div>
        
        <div id="userRequests" class="content">
            <h2><i class="fas fa-inbox"></i> User Requests</h2>
            <button onclick="loadUserRequests()"><i class="fas fa-sync-alt"></i> REFRESH</button>
            <div class="table-wrapper"><div id="requestsList"></div></div>
        </div>
        
        <div id="history" class="content">
            <h2><i class="fas fa-scroll"></i> License History</h2>
            <div style="display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 15px;">
                <input type="text" id="historySearch" placeholder="Search..." onkeyup="filterHistory()" style="width: 300px;">
                <button onclick="loadHistory()"><i class="fas fa-sync-alt"></i> REFRESH</button>
                <button onclick="exportHistory()"><i class="fas fa-download"></i> EXPORT CSV</button>
            </div>
            <div class="table-wrapper"><div id="historyList"></div></div>
        </div>
        
        <div id="admins" class="content">
            <div class="master-only">
                <h2><i class="fas fa-crown"></i> MASTER CONTROL — User Management</h2>
            </div>
            
            <!-- Action Cards -->
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; margin-bottom: 28px;">
                
                <!-- Add User Card -->
                <div style="background: rgba(0,0,0,0.25); border: 1px solid var(--border); border-radius: 16px; padding: 20px;">
                    <h3 style="margin-bottom: 14px; font-size: 15px;"><i class="fas fa-user-plus" style="color: var(--secondary);"></i> &nbsp;Add New User</h3>
                    <input type="text" id="newAdminUser" placeholder="Username">
                    <input type="password" id="newAdminPass" placeholder="Password">
                    <select id="newAdminRole" style="margin: 8px 0;">
                        <option value="admin">Admin (Trial + Custom)</option>
                        <option value="moderator">Moderator (Trial only)</option>
                    </select>
                    <input type="number" id="newAdminCredits" placeholder="Initial Credits" value="100" step="0.5">
                    <button class="btn-success" onclick="addAdmin()" style="margin-top: 10px;"><i class="fas fa-plus"></i> ADD USER</button>
                </div>
                
                <!-- Change Role Card -->
                <div style="background: rgba(0,0,0,0.25); border: 1px solid var(--border); border-radius: 16px; padding: 20px;">
                    <h3 style="margin-bottom: 14px; font-size: 15px;"><i class="fas fa-exchange-alt" style="color: var(--warning);"></i> &nbsp;Change Role</h3>
                    <input type="text" id="roleChangeUser" placeholder="Username">
                    <select id="newRoleSelect" style="margin: 8px 0;">
                        <option value="admin">Admin (Trial + Custom)</option>
                        <option value="moderator">Moderator (Trial only)</option>
                    </select>
                    <button class="btn-warning" onclick="changeUserRole()" style="margin-top: 10px;"><i class="fas fa-sync"></i> CHANGE ROLE</button>
                    
                    <hr style="border-color: var(--border); margin: 16px 0;">
                    
                    <h3 style="margin-bottom: 14px; font-size: 15px;"><i class="fas fa-key" style="color: var(--primary);"></i> &nbsp;Change User Password</h3>
                    <input type="text" id="targetUsername" placeholder="Username">
                    <input type="password" id="newPasswordForTarget" placeholder="New Password">
                    <button onclick="changeOtherPassword()" style="margin-top: 10px;"><i class="fas fa-lock"></i> CHANGE PASSWORD</button>
                </div>
                
                <!-- Credits Card -->
                <div style="background: rgba(0,0,0,0.25); border: 1px solid var(--border); border-radius: 16px; padding: 20px;">
                    <h3 style="margin-bottom: 14px; font-size: 15px;"><i class="fas fa-coins" style="color: #F59E0B;"></i> &nbsp;Manage Credits</h3>
                    <input type="text" id="creditUsername" placeholder="Username">
                    <input type="number" id="creditAmount" placeholder="Amount (use - to deduct)" step="0.5">
                    <button onclick="manageCredits()" style="margin-top: 10px;"><i class="fas fa-wallet"></i> UPDATE CREDITS</button>
                    <div style="margin-top: 12px; font-size: 12px; color: var(--text-secondary);">
                        <i class="fas fa-info-circle"></i> Use negative numbers to deduct credits (e.g. -50)
                    </div>
                </div>
            </div>
            
            <!-- Users Tables -->
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                <div>
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                        <h3 style="font-size: 15px;"><i class="fas fa-users" style="color: var(--primary);"></i> &nbsp;Admins</h3>
                        <button onclick="loadAdmins()" style="width:auto; padding:6px 14px; font-size:12px;"><i class="fas fa-sync-alt"></i></button>
                    </div>
                    <div style="overflow-x:auto; border-radius: 12px; border: 1px solid var(--border);">
                        <div id="adminsList"></div>
                    </div>
                </div>
                <div>
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                        <h3 style="font-size: 15px;"><i class="fas fa-user-shield" style="color: var(--secondary);"></i> &nbsp;Moderators</h3>
                        <button onclick="loadAdmins()" style="width:auto; padding:6px 14px; font-size:12px;"><i class="fas fa-sync-alt"></i></button>
                    </div>
                    <div style="overflow-x:auto; border-radius: 12px; border: 1px solid var(--border);">
                        <div id="moderatorsList"></div>
                    </div>
                </div>
            </div>
        </div>
        
        <div id="changePassword" class="content">
            <h2><i class="fas fa-key"></i> Change Your Password</h2>
            <div class="form-row">
                <div class="form-group"><input type="password" id="oldPassword" placeholder="Current Password"></div>
                <div class="form-group"><input type="password" id="newPassword" placeholder="New Password"></div>
            </div>
            <div class="form-group"><input type="password" id="confirmPassword" placeholder="Confirm Password"></div>
            <button onclick="changePassword()"><i class="fas fa-save"></i> UPDATE PASSWORD</button>
            <div id="passwordResult" class="result-box" style="display: none;"></div>
        </div>
        
        <div id="monitor" class="content">
            <h2><i class="fas fa-chart-line"></i> System Monitor</h2>
            <button onclick="loadMonitor()"><i class="fas fa-sync-alt"></i> REFRESH</button>
            <div id="monitorData" class="result-box"></div>
        </div>
    </div>
</div>

<div id="credsModal" class="modal">
    <div class="modal-content">
        <span class="close" onclick="closeModal()">&times;</span>
        <h2 id="modalTitle"><i class="fas fa-key"></i> License Credentials</h2>
        <div id="modalBody"></div>
        <div style="margin-top: 20px; display: flex; gap: 10px; justify-content: flex-end;">
            <button class="btn-success" onclick="copyStyledCredentials()"><i class="fas fa-copy"></i> COPY STYLIZED</button>
            <button onclick="closeModal()"><i class="fas fa-times"></i> Close</button>
        </div>
    </div>
</div>

{THEME_SELECTOR_HTML}

<script>
    const API_URL = window.location.origin;
    let currentUser = null, currentRole = null;
    let lastGeneratedData = null;
    
    function switchTabTo(tabId) {{
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.content').forEach(c => c.classList.remove('active'));
        document.getElementById(tabId).classList.add('active');
        if(tabId === 'myLicenses') loadMyLicenses();
        if(tabId === 'userRequests') loadUserRequests();
        if(tabId === 'history') loadHistory();
        if(tabId === 'admins' && currentRole === 'master') loadAdmins();
        if(tabId === 'monitor') loadMonitor();
        if(tabId === 'registrationLinks') loadRegistrationLinks();
    }}
    
    async function login() {{
        const username = document.getElementById('loginUsername').value;
        const password = document.getElementById('loginPassword').value;
        const res = await fetch(API_URL + '/api/admin/login', {{
            method: 'POST', headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify({{username: username, password: password}})
        }});
        const data = await res.json();
        if(data.success) {{
            currentUser = username; currentRole = data.role;
            document.getElementById('currentUser').textContent = username;
            document.getElementById('currentRole').textContent = data.role.toUpperCase();
            document.getElementById('currentCredits').textContent = data.credits || 'Unlimited';
            
            if(data.role === 'master') {{
                document.getElementById('adminTab').style.display = 'inline-block';
                document.getElementById('permanentTab').style.display = 'inline-block';
                document.getElementById('showPermanentBtn').style.display = 'inline-block';
                document.getElementById('statPermanentCard').style.display = 'block';
            }} else if(data.role === 'admin') {{
                document.getElementById('customTab').style.display = 'inline-block';
                document.getElementById('showCustomBtn').style.display = 'inline-block';
                document.getElementById('statCustomCard').style.display = 'block';
            }} else {{
                document.getElementById('customTab').style.display = 'none';
                document.getElementById('showCustomBtn').style.display = 'none';
                document.getElementById('statCustomCard').style.display = 'none';
                // Moderators can only generate trial links
                const customOpt = document.getElementById('linkCustomOption');
                if(customOpt) customOpt.style.display = 'none';
            }}
            document.getElementById('loginScreen').style.display = 'none';
            document.getElementById('mainPanel').style.display = 'block';
            loadStats(); loadMyLicenses(); loadHistory(); loadUserRequests(); loadRegistrationLinks();
            updateLinkTypeOptions(); updateLinkCostPreview();
        }} else {{
            document.getElementById('loginError').style.display = 'block';
        }}
    }}
    
    function switchTab(tabId) {{
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.content').forEach(c => c.classList.remove('active'));
        event.target.classList.add('active');
        document.getElementById(tabId).classList.add('active');
        if(tabId === 'myLicenses') loadMyLicenses();
        if(tabId === 'userRequests') loadUserRequests();
        if(tabId === 'history') loadHistory();
        if(tabId === 'admins' && currentRole === 'master') loadAdmins();
        if(tabId === 'monitor') loadMonitor();
        if(tabId === 'registrationLinks') loadRegistrationLinks();
    }}
    
    function showLicenseType(type) {{
        document.getElementById('myTrialsList').style.display = 'none';
        document.getElementById('myCustomList').style.display = 'none';
        document.getElementById('myPermanentList').style.display = 'none';
        if(type === 'trials') document.getElementById('myTrialsList').style.display = 'block';
        if(type === 'custom') document.getElementById('myCustomList').style.display = 'block';
        if(type === 'permanent') document.getElementById('myPermanentList').style.display = 'block';
    }}
    
    async function loadStats() {{
        const res = await fetch(API_URL + '/api/admin/get-stats', {{
            method: 'POST', headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify({{admin_username: currentUser, admin_password: document.getElementById('loginPassword').value}})
        }});
        const data = await res.json();
        if(data.success) {{
            document.getElementById('statTrials').textContent = data.trials;
            document.getElementById('statCustom').textContent = data.custom || 0;
            document.getElementById('statPermanent').textContent = data.permanent || 0;
            document.getElementById('statHistory').textContent = data.history_count || 0;
            document.getElementById('statRequests').textContent = data.pending_requests || 0;
            document.getElementById('statLinks').textContent = data.active_links || 0;
            document.getElementById('currentCredits').textContent = data.user_credits || 'Unlimited';
        }}
    }}
    
    function formatDurationHours(hours) {{
        if(hours >= 720) return Math.floor(hours/720) + ' MONTHS';
        if(hours >= 168) return Math.floor(hours/168) + ' WEEKS';
        if(hours >= 24) return Math.floor(hours/24) + ' DAYS';
        return hours + ' HOURS';
    }}
    
    function getStyledCredentials(licenseKey, username, password, durationText, maxDevices, licenseType) {{
        return `✅ ${{licenseType}} CREATED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔑 LICENSE: ${{licenseKey}}
👤 USER: ${{username}}
🔒 PASS: ${{password}}
⏱️ TIME: ${{durationText}}
💻 MAX DEVICES: ${{maxDevices}}
🌐 CHECK STATUS: ${{API_URL}}/user
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ License activates ONLY on first use!`;
    }}
    
    function showCredentialsModal(licenseKey, username, password, durationText, maxDevices, licenseType) {{
        lastGeneratedData = {{licenseKey, username, password, durationText, maxDevices, licenseType}};
        const styledText = getStyledCredentials(licenseKey, username, password, durationText, maxDevices, licenseType);
        const modal = document.getElementById('credsModal');
        document.getElementById('modalTitle').innerHTML = '<i class="fas fa-key"></i> LICENSE GENERATED';
        document.getElementById('modalBody').innerHTML = `
            <div class="pre-style">${{styledText.replace(/\\n/g, '<br>')}}</div>
            <div style="margin-top: 15px; padding: 10px; background: rgba(16,185,129,0.1); border-radius: 12px;">
                <p style="font-size: 13px;"><i class="fas fa-check-circle"></i> License saved in history<br><i class="fas fa-folder-open"></i> You can find it in "MY LICENSES" tab</p>
            </div>
        `;
        modal.style.display = 'block';
    }}
    
    function copyStyledCredentials() {{
        if(!lastGeneratedData) return;
        const text = getStyledCredentials(
            lastGeneratedData.licenseKey, 
            lastGeneratedData.username, 
            lastGeneratedData.password, 
            lastGeneratedData.durationText, 
            lastGeneratedData.maxDevices, 
            lastGeneratedData.licenseType
        );
        navigator.clipboard.writeText(text);
        alert('✓ Credentials copied to clipboard!');
    }}
    
    function copyToClipboard(text) {{ navigator.clipboard.writeText(text); alert('✓ Copied!'); }}
    
    async function generateTrial() {{
        const duration = document.getElementById('trialDuration').value;
        const maxDevices = document.getElementById('maxDevices').value;
        const res = await fetch(API_URL + '/api/admin/generate-trial', {{
            method: 'POST', headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify({{
                admin_username: currentUser, 
                admin_password: document.getElementById('loginPassword').value, 
                duration_hours: parseInt(duration),
                max_devices: parseInt(maxDevices)
            }})
        }});
        const data = await res.json();
        const resultDiv = document.getElementById('trialResult');
        resultDiv.style.display = 'block';
        if(data.success) {{
            const durationText = formatDurationHours(parseInt(duration));
            showCredentialsModal(data.license_key, data.username, data.password, durationText, maxDevices, 'TRIAL');
            resultDiv.innerHTML = `<i class="fas fa-check-circle"></i> TRIAL LICENSE CREATED!<br>💰 Used: ${{data.credits_used}} credits<br>💳 Remaining: ${{data.remaining_credits}}`;
            loadStats(); loadMyLicenses(); loadHistory();
        }} else {{ resultDiv.innerHTML = `<i class="fas fa-exclamation-triangle"></i> ${{data.error}}`; }}
    }}
    
    async function createCustomActivation() {{
        if(currentRole === 'moderator') {{ alert('Moderators cannot create Custom licenses!'); return; }}
        const username = document.getElementById('customUsername').value;
        const password = document.getElementById('customPassword').value;
        const license = document.getElementById('customLicense').value;
        const durationType = document.getElementById('customDurationType').value;
        const durationValue = parseFloat(document.getElementById('customDurationValue').value);
        const maxDevices = document.getElementById('customMaxDevices').value;
        if(!username || !password || !license) {{ alert('Fill all fields!'); return; }}
        const res = await fetch(API_URL + '/api/admin/create-custom-activation', {{
            method: 'POST', headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify({{
                admin_username: currentUser, 
                admin_password: document.getElementById('loginPassword').value, 
                username, password, 
                license_key: license, 
                duration_type: durationType, 
                duration_value: durationValue,
                max_devices: parseInt(maxDevices)
            }})
        }});
        const data = await res.json();
        const resultDiv = document.getElementById('customResult');
        resultDiv.style.display = 'block';
        if(data.success) {{
            let durationText = '';
            if(durationType === 'unlimited') durationText = 'UNLIMITED';
            else durationText = durationValue + ' ' + durationType.toUpperCase();
            showCredentialsModal(license, username, password, durationText, maxDevices, 'CUSTOM');
            resultDiv.innerHTML = `<i class="fas fa-check-circle"></i> CUSTOM LICENSE CREATED!<br>💰 Used: ${{data.credits_used}} credits<br>💳 Remaining: ${{data.remaining_credits}}`;
            document.getElementById('customUsername').value = '';
            document.getElementById('customPassword').value = '';
            document.getElementById('customLicense').value = '';
            document.getElementById('customDurationValue').value = '';
            loadStats(); loadMyLicenses(); loadHistory();
        }} else {{ resultDiv.innerHTML = `<i class="fas fa-exclamation-triangle"></i> ${{data.error}}`; }}
    }}
    
    async function createPermanentLicense() {{
        if(currentRole !== 'master') {{ alert('Only Master can create Permanent licenses!'); return; }}
        const license = document.getElementById('permLicenseKey').value;
        const username = document.getElementById('permUsername').value;
        const password = document.getElementById('permPassword').value;
        const maxDevices = document.getElementById('permMaxDevices').value;
        if(!license) {{ alert('License key required!'); return; }}
        const res = await fetch(API_URL + '/api/admin/create-permanent-license', {{
            method: 'POST', headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify({{
                admin_username: currentUser, 
                admin_password: document.getElementById('loginPassword').value, 
                license_key: license, 
                username, password,
                max_devices: parseInt(maxDevices)
            }})
        }});
        const data = await res.json();
        const resultDiv = document.getElementById('permResult');
        resultDiv.style.display = 'block';
        if(data.success) {{
            showCredentialsModal(license, username || 'N/A', password || 'N/A', 'PERMANENT (NEVER EXPIRES)', maxDevices, 'PERMANENT');
            resultDiv.innerHTML = `<i class="fas fa-check-circle"></i> PERMANENT LICENSE CREATED!<br>💰 Remaining: ${{data.remaining_credits}}`;
            document.getElementById('permLicenseKey').value = '';
            document.getElementById('permUsername').value = '';
            document.getElementById('permPassword').value = '';
            loadStats(); loadMyLicenses(); loadHistory();
        }} else {{ resultDiv.innerHTML = `<i class="fas fa-exclamation-triangle"></i> ${{data.error}}`; }}
    }}
    
    function updateLinkTypeOptions() {{
        const licenseType = document.getElementById('linkLicenseType').value;
        const trialSelect = document.getElementById('linkDurationSelect');
        const customSelect = document.getElementById('linkDurationType');
        const valueGroup = document.getElementById('linkDurationValueGroup');
        if(licenseType === 'trial') {{
            trialSelect.style.display = 'block';
            customSelect.style.display = 'none';
            valueGroup.style.display = 'none';
        }} else {{
            trialSelect.style.display = 'none';
            customSelect.style.display = 'block';
            valueGroup.style.display = 'block';
        }}
        updateLinkCostPreview();
    }}
    
    function updateLinkCostPreview() {{
        const licenseType = document.getElementById('linkLicenseType').value;
        let cost = 0;
        const pricing = {{ custom_hour: 2, custom_day: 5, custom_week: 8, custom_month: 50, custom_year: 800, custom_unlimited: 1500 }};
        const TRIAL_FIXED = {{3:2, 6:3, 12:4, 24:5, 72:10, 168:20, 720:50}};
        if(licenseType === 'trial') {{
            const hours = parseInt(document.getElementById('linkDurationSelect').value) || 3;
            cost = TRIAL_FIXED[hours] || 0;
        }} else {{
            const durationType = document.getElementById('linkDurationType').value;
            const durationValue = parseFloat(document.getElementById('linkDurationValue').value) || 0;
            if(durationType === 'hours') cost = durationValue * pricing.custom_hour;
            else if(durationType === 'days') cost = durationValue * pricing.custom_day;
            else if(durationType === 'weeks') cost = durationValue * pricing.custom_week;
            else if(durationType === 'months') cost = durationValue * pricing.custom_month;
            else if(durationType === 'years') cost = durationValue * pricing.custom_year;
            else if(durationType === 'unlimited') cost = pricing.custom_unlimited;
            cost = Math.round(cost * 100) / 100;
        }}
        const preview = document.getElementById('linkCostPreview');
        document.getElementById('linkCostValue').textContent = cost;
        preview.style.display = cost > 0 ? 'block' : 'none';
    }}
    
    async function generateRegistrationLink() {{
        const licenseType = document.getElementById('linkLicenseType').value;
        const maxDevices = parseInt(document.getElementById('linkMaxDevices').value);
        
        let durationType, durationValue;
        if(licenseType === 'trial') {{
            const hours = parseInt(document.getElementById('linkDurationSelect').value);
            durationType = 'hours';
            durationValue = hours;
        }} else {{
            durationType = document.getElementById('linkDurationType').value;
            durationValue = parseFloat(document.getElementById('linkDurationValue').value);
        }}
        
        if(durationType !== 'unlimited' && (!durationValue || durationValue <= 0)) {{
            alert('Please enter a valid duration value');
            return;
        }}
        
        if(currentRole === 'moderator' && licenseType === 'custom') {{
            alert('Moderators can only generate Trial registration links.');
            return;
        }}
        
        const res = await fetch(API_URL + '/api/admin/generate-registration-link', {{
            method: 'POST', headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify({{
                admin_username: currentUser,
                admin_password: document.getElementById('loginPassword').value,
                license_type: licenseType,
                duration_value: durationValue,
                duration_type: durationType,
                max_devices: maxDevices
            }})
        }});
        
        const data = await res.json();
        if(data.success) {{
            const fullLink = `${{API_URL}}/register/${{data.token}}`;
            const msg = `✅ Registration link created!\n\n🔗 LINK:\n${{fullLink}}\n\n💰 Credits used: ${{data.credits_used}}\n💳 Remaining: ${{data.remaining_credits}}\n\n⏰ Expires in 24 hours. Link auto-refunds if unused.`;
            if(navigator.clipboard) navigator.clipboard.writeText(fullLink).catch(()=>{{}});
            alert(msg);
            loadRegistrationLinks();
            loadStats();
        }} else {{
            alert('Error: ' + data.error);
        }}
    }}
    
    async function loadRegistrationLinks() {{
        const res = await fetch(API_URL + '/api/admin/get-registration-links', {{
            method: 'POST', headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify({{
                admin_username: currentUser,
                admin_password: document.getElementById('loginPassword').value
            }})
        }});
        const data = await res.json();
        if(!data.links || data.links.length === 0) {{
            document.getElementById('linksList').innerHTML = '<div style="text-align:center; padding:30px; color: var(--text-secondary);"><i class="fas fa-link" style="font-size:32px; opacity:0.3;"></i><br><br>No registration links yet.</div>';
            return;
        }}
        let html = '<div style="display:grid; gap:12px;">';
        data.links.forEach(link => {{
            const fullLink = `${{API_URL}}/register/${{link.token}}`;
            const isUsed = link.used;
            const expires = new Date(link.expires_at);
            const now = new Date();
            const isExpired = now > expires;
            const minsLeft = Math.max(0, Math.round((expires - now) / 60000));
            const hoursLeft = Math.floor(minsLeft / 60);
            const minsRem = minsLeft % 60;
            const timeLeft = isExpired ? '<span style="color:var(--danger);">Expired</span>' : `<span style="color:var(--warning);">${{hoursLeft}}h ${{minsRem}}m left</span>`;
            let durationDisplay = link.duration_type === 'unlimited' ? 'UNLIMITED' : `${{link.duration_value}} ${{link.duration_type}}`;
            const statusColor = isUsed ? 'var(--secondary)' : (isExpired ? 'var(--danger)' : 'var(--warning)');
            const statusText = isUsed ? '✓ Used' : (isExpired ? '✗ Expired' : '◉ Active');
            html += `
            <div style="background:rgba(0,0,0,0.25); border:1px solid var(--border); border-radius:14px; padding:16px;">
                <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:10px;">
                    <div style="flex:1; min-width:0;">
                        <div style="display:flex; gap:8px; align-items:center; flex-wrap:wrap; margin-bottom:10px;">
                            <span style="background:rgba(124,58,237,0.2); padding:3px 10px; border-radius:20px; font-size:11px; font-weight:700; color:var(--primary);">${{link.license_type.toUpperCase()}}</span>
                            <span style="font-size:12px; font-weight:700; color:${{statusColor}};">${{statusText}}</span>
                            <span style="font-size:11px; color:var(--text-secondary);">${{timeLeft}}</span>
                            ${{(link.credits_cost && link.credits_cost > 0) ? `<span style="font-size:11px; color:var(--text-secondary);"><i class="fas fa-coins"></i> ${{link.credits_cost}} cr</span>` : ''}}
                        </div>
                        <div style="font-family:monospace; font-size:11px; color:var(--text-secondary); word-break:break-all; background:rgba(0,0,0,0.2); padding:8px; border-radius:8px; margin-bottom:8px;">
                            ${{fullLink}}
                        </div>
                        <div style="display:flex; gap:16px; font-size:12px; color:var(--text-secondary); flex-wrap:wrap;">
                            <span><i class="fas fa-clock"></i> ${{durationDisplay}}</span>
                            <span><i class="fas fa-microchip"></i> ${{link.max_devices}} device(s)</span>
                            <span><i class="fas fa-user"></i> By: ${{link.created_by}}</span>
                            ${{isUsed ? `<span><i class="fas fa-check-circle" style="color:var(--secondary);"></i> Used by: ${{link.used_by || '-'}}</span>` : ''}}
                        </div>
                    </div>
                    <div style="display:flex; flex-direction:column; gap:8px; min-width:100px;">
                        ${{!isUsed && !isExpired ? `<button onclick="copyLinkToClipboard('${{fullLink}}')" style="padding:8px 14px; font-size:12px; background:rgba(59,130,246,0.3); border:1px solid rgba(59,130,246,0.5);"><i class="fas fa-copy"></i> Copy</button>` : ''}}
                        ${{!isUsed && !isExpired ? `<button class="btn-danger" onclick="cancelRegistrationLink('${{link.token}}')" style="padding:8px 14px; font-size:12px;"><i class="fas fa-times"></i> Cancel</button>` : ''}}
                    </div>
                </div>
            </div>`;
        }});
        html += '</div>';
        document.getElementById('linksList').innerHTML = html;
    }}

    function copyLinkToClipboard(text) {{
        navigator.clipboard.writeText(text).then(() => alert('✓ Link copied to clipboard!')).catch(() => {{
            prompt('Copy this link:', text);
        }});
    }}

    async function cancelRegistrationLink(token) {{
        if(!confirm('Cancel this link? If unused, your credits will be refunded.')) return;
        const res = await fetch(API_URL + '/api/admin/delete-registration-link', {{
            method: 'POST', headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify({{
                admin_username: currentUser,
                admin_password: document.getElementById('loginPassword').value,
                token: token
            }})
        }});
        const data = await res.json();
        if(data.success) {{
            if(data.refunded_credits > 0) {{
                alert(`✅ Link cancelled! ${{data.refunded_credits}} credits refunded.`);
            }} else {{
                alert('Link cancelled.');
            }}
            loadRegistrationLinks();
            loadStats();
        }} else {{
            alert('Error: ' + data.error);
        }}
    }}
    
    async function loadMyLicenses() {{
        await loadMyTrials();
        if(currentRole !== 'moderator') await loadMyCustom();
        if(currentRole === 'master') await loadMyPermanent();
    }}
    
    async function loadMyTrials() {{
        const res = await fetch(API_URL + '/api/admin/get-my-trials', {{
            method: 'POST', headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify({{admin_username: currentUser, admin_password: document.getElementById('loginPassword').value}})
        }});
        const data = await res.json();
        let html = '<div class="table-wrapper"><table><thead><tr><th>License</th><th>Max Devices</th><th>Used</th><th>Activated</th><th>Expires</th><th>Status</th><th>Action</th></tr></thead><tbody>';
        data.trials.forEach(t => {{
            html += `<tr>
                <td>${{t.license_key}} <button class="copy-btn" onclick="copyToClipboard('${{t.license_key}}')"><i class="fas fa-copy"></i></button></td>
                <td>${{t.max_devices || 1}}</td>
                <td>${{t.hwid_count || 0}}</td>
                <td>${{t.activated ? '<i class="fas fa-check-circle" style="color:var(--secondary)"></i>' : '<i class="fas fa-clock" style="color:var(--warning)"></i>'}} ${{t.activated ? 'Yes' : 'No'}}</td>
                <td>${{t.expires_at || '-'}}</td>
                <td><span class="badge badge-${{t.status === 'ACTIVE' ? 'active' : (t.status === 'EXPIRED' ? 'expired' : 'warning')}}">${{t.status}}</span></td>
                <td><button class="btn-danger" onclick="deleteTrial('${{t.license_key}}')"><i class="fas fa-trash"></i></button></td>
            </tr>`;
        }});
        html += '</tbody></table></div>';
        document.getElementById('myTrialsList').innerHTML = html;
    }}
    
    async function loadMyCustom() {{
        const res = await fetch(API_URL + '/api/admin/get-my-custom', {{
            method: 'POST', headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify({{admin_username: currentUser, admin_password: document.getElementById('loginPassword').value}})
        }});
        const data = await res.json();
        let html = '<div class="table-wrapper"><table><thead><tr><th>License</th><th>Username</th><th>Password</th><th>Max Devices</th><th>Used</th><th>Expires</th><th>Status</th><th>Action</th></tr></thead><tbody>';
        data.activations.forEach(a => {{
            html += `<tr>
                <td>${{a.license_key}} <button class="copy-btn" onclick="copyToClipboard('${{a.license_key}}')"><i class="fas fa-copy"></i></button></td>
                <td>${{a.username}} <button class="copy-btn" onclick="copyToClipboard('${{a.username}}')"><i class="fas fa-copy"></i></button></td>
                <td>${{a.password}} <button class="copy-btn" onclick="copyToClipboard('${{a.password}}')"><i class="fas fa-copy"></i></button></td>
                <td>${{a.max_devices || 1}}</td>
                <td>${{a.hwids ? a.hwids.length : 0}}</td>
                <td>${{a.expires_at || 'NEVER'}}</td>
                <td><span class="badge badge-${{a.status === 'ACTIVE' ? 'active' : 'expired'}}">${{a.status}}</span></td>
                <td><button class="btn-danger" onclick="deleteCustomActivation('${{a.license_key}}')"><i class="fas fa-trash"></i></button></td>
            </tr>`;
        }});
        html += '</tbody></table></div>';
        document.getElementById('myCustomList').innerHTML = html;
    }}
    
    async function loadMyPermanent() {{
        const res = await fetch(API_URL + '/api/admin/get-my-permanent', {{
            method: 'POST', headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify({{admin_username: currentUser, admin_password: document.getElementById('loginPassword').value}})
        }});
        const data = await res.json();
        let html = '<div class="table-wrapper"><table><thead><tr><th>License</th><th>Username</th><th>Max Devices</th><th>Used</th><th>Status</th><th>Action</th></tr></thead><tbody>';
        data.licenses.forEach(l => {{
            html += `<tr>
                <td>${{l.license_key}} <button class="copy-btn" onclick="copyToClipboard('${{l.license_key}}')"><i class="fas fa-copy"></i></button></td>
                <td>${{l.username || '-'}}</td>
                <td>${{l.max_devices || 1}}</td>
                <td>${{l.hwids ? l.hwids.length : 0}}</td>
                <td><span class="badge badge-active">ACTIVE</span></td>
                <td><button class="btn-danger" onclick="deletePermanentLicense('${{l.license_key}}')"><i class="fas fa-trash"></i></button></td>
            </tr>`;
        }});
        html += '</tbody></table></div>';
        document.getElementById('myPermanentList').innerHTML = html;
    }}
    
    async function loadUserRequests() {{
        const res = await fetch(API_URL + '/api/admin/get-requests', {{
            method: 'POST', headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify({{admin_username: currentUser, admin_password: document.getElementById('loginPassword').value}})
        }});
        const data = await res.json();
        let html = '<table><thead><tr><th>Date</th><th>License</th><th>User</th><th>Type</th><th>Message</th><th>Contact</th><th>Status</th><th>Action</th></tr></thead><tbody>';
        data.requests.forEach((req, idx) => {{
            html += `<tr>
                <td>${{new Date(req.created_at).toLocaleString()}}</td>
                <td>${{req.license_key}}</td>
                <td>${{req.username}}</td>
                <td>${{req.request_type}}</td>
                <td>${{req.message.substring(0, 50)}}...</td>
                <td>${{req.contact || '-'}}</td>
                <td><span class="badge badge-${{req.status}}">${{req.status}}</span></td>
                <td>${{req.status === 'pending' ? `<button class="btn-success" onclick="approveRequest(${{idx}}, '${{req.license_key}}', '${{req.request_type}}', ${{req.days_requested || 7}})"><i class="fas fa-check"></i></button>
                    <button class="btn-danger" onclick="rejectRequest(${{idx}})"><i class="fas fa-times"></i></button>` : '-'}}</td>
            </tr>`;
        }});
        html += '</tbody></table>';
        document.getElementById('requestsList').innerHTML = html;
    }}
    
    async function approveRequest(idx, licenseKey, reqType, days) {{
        if(!confirm(`Approve request for ${{licenseKey}}?`)) return;
        const res = await fetch(API_URL + '/api/admin/approve-request', {{
            method: 'POST', headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify({{admin_username: currentUser, admin_password: document.getElementById('loginPassword').value, request_index: idx, license_key: licenseKey, request_type: reqType, days_to_add: days}})
        }});
        const data = await res.json();
        if(data.success) {{ alert('Approved!'); loadUserRequests(); loadStats(); }}
        else {{ alert('Error: ' + data.error); }}
    }}
    
    async function rejectRequest(idx) {{
        if(!confirm('Reject this request?')) return;
        const res = await fetch(API_URL + '/api/admin/reject-request', {{
            method: 'POST', headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify({{admin_username: currentUser, admin_password: document.getElementById('loginPassword').value, request_index: idx}})
        }});
        const data = await res.json();
        if(data.success) {{ alert('Rejected!'); loadUserRequests(); }}
        else {{ alert('Error: ' + data.error); }}
    }}
    
    async function loadHistory() {{
        const res = await fetch(API_URL + '/api/admin/get-history', {{
            method: 'POST', headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify({{admin_username: currentUser, admin_password: document.getElementById('loginPassword').value}})
        }});
        const data = await res.json();
        let html = '<table><thead><tr><th>Created</th><th>License</th><th>Username</th><th>Password</th><th>Type</th><th>Owner</th><th>Expires</th><th>Action</th></tr></thead><tbody>';
        data.history.forEach(h => {{
            html += `<tr>
                <td>${{new Date(h.created_at).toLocaleString()}}</td>
                <td><strong>${{h.license_key}}</strong> <button class="copy-btn" onclick="copyToClipboard('${{h.license_key}}')"><i class="fas fa-copy"></i></button></td>
                <td>${{h.username}} <button class="copy-btn" onclick="copyToClipboard('${{h.username}}')"><i class="fas fa-copy"></i></button></td>
                <td>${{h.password}} <button class="copy-btn" onclick="copyToClipboard('${{h.password}}')"><i class="fas fa-copy"></i></button></td>
                <td>${{h.type}}</td>
                <td>${{h.owner}}</td>
                <td>${{h.expires_at || 'NEVER'}}</td>
                <td><button onclick="showHistoryCredentials('${{h.license_key}}', '${{h.username}}', '${{h.password}}', '${{h.type}}', '${{h.expires_at}}')"><i class="fas fa-eye"></i></button></td>
            </tr>`;
        }});
        html += '</tbody></table>';
        document.getElementById('historyList').innerHTML = html;
    }}
    
    function showHistoryCredentials(licenseKey, username, password, type, expires) {{
        const styledText = `📜 LICENSE FROM HISTORY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔑 LICENSE: ${{licenseKey}}
👤 USER: ${{username}}
🔒 PASS: ${{password}}
📋 TYPE: ${{type}}
⏰ EXPIRES: ${{expires || 'NEVER'}}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`;
        const modal = document.getElementById('credsModal');
        document.getElementById('modalTitle').innerHTML = '<i class="fas fa-scroll"></i> History Credentials';
        document.getElementById('modalBody').innerHTML = `<div class="pre-style">${{styledText.replace(/\\n/g, '<br>')}}</div>`;
        modal.style.display = 'block';
    }}
    
    function filterHistory() {{
        const search = document.getElementById('historySearch').value.toLowerCase();
        const rows = document.querySelectorAll('#historyList tr');
        rows.forEach((row, i) => {{ if(i > 0) row.style.display = row.textContent.toLowerCase().includes(search) ? '' : 'none'; }});
    }}
    
    async function exportHistory() {{
        window.open(API_URL + '/api/admin/export-history?admin_username=' + currentUser + '&admin_password=' + document.getElementById('loginPassword').value);
    }}
    
    async function loadAdmins() {{
        const res = await fetch(API_URL + '/api/admin/get-admins', {{
            method: 'POST', headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify({{admin_username: currentUser, admin_password: document.getElementById('loginPassword').value}})
        }});
        const data = await res.json();

        function makeUserTable(users, deleteFunc) {{
            if(!users || users.length === 0) {{
                return '<div style="text-align:center; padding:20px; color:var(--text-secondary); font-size:13px;"><i class="fas fa-users" style="opacity:0.3;"></i><br>None yet</div>';
            }}
            let h = '<table style="width:100%; border-collapse:collapse; font-size:13px;"><thead><tr style="background:rgba(124,58,237,0.15);"><th style="padding:10px 12px; text-align:left; font-weight:600; color:var(--primary); border-bottom:1px solid var(--border);">User</th><th style="padding:10px 12px; text-align:left; font-weight:600; color:var(--primary); border-bottom:1px solid var(--border);">Credits</th><th style="padding:10px 12px; text-align:left; font-weight:600; color:var(--primary); border-bottom:1px solid var(--border);">Created</th><th style="padding:10px 12px; text-align:left; font-weight:600; color:var(--primary); border-bottom:1px solid var(--border);"></th></tr></thead><tbody>';
            users.forEach(u => {{
                const created = u.created_at ? new Date(u.created_at).toLocaleDateString() : '-';
                h += `<tr style="border-bottom:1px solid var(--border);">
                    <td style="padding:10px 12px; font-weight:600;"><i class="fas fa-user" style="color:var(--primary); margin-right:6px; font-size:11px;"></i>${{u.username}}</td>
                    <td style="padding:10px 12px;"><span style="background:rgba(124,58,237,0.2); padding:3px 10px; border-radius:20px; font-size:12px; font-weight:700;">${{u.credits}}</span></td>
                    <td style="padding:10px 12px; color:var(--text-secondary); font-size:12px;">${{created}}</td>
                    <td style="padding:10px 12px;"><button onclick="${{deleteFunc}}('${{u.username}}')" style="background:var(--danger); padding:5px 10px; font-size:11px; border-radius:8px; width:auto;"><i class="fas fa-trash"></i></button></td>
                </tr>`;
            }});
            h += '</tbody></table>';
            return h;
        }}

        document.getElementById('adminsList').innerHTML = makeUserTable(data.admins, 'deleteAdmin');
        document.getElementById('moderatorsList').innerHTML = makeUserTable(data.moderators, 'deleteModerator');
    }}
    
    async function addAdmin() {{
        const username = document.getElementById('newAdminUser').value;
        const password = document.getElementById('newAdminPass').value;
        const role = document.getElementById('newAdminRole').value;
        const credits = parseFloat(document.getElementById('newAdminCredits').value);
        const res = await fetch(API_URL + '/api/admin/add-admin', {{
            method: 'POST', headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify({{admin_username: currentUser, admin_password: document.getElementById('loginPassword').value, new_username: username, new_password: password, role: role, credits: credits}})
        }});
        const data = await res.json();
        if(data.success) {{ alert('User added!'); loadAdmins(); }}
        else {{ alert('Error: ' + data.error); }}
    }}
    
    async function changeUserRole() {{
        const username = document.getElementById('roleChangeUser').value;
        const newRole = document.getElementById('newRoleSelect').value;
        const res = await fetch(API_URL + '/api/admin/change-role', {{
            method: 'POST', headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify({{admin_username: currentUser, admin_password: document.getElementById('loginPassword').value, target_username: username, new_role: newRole}})
        }});
        const data = await res.json();
        if(data.success) {{ alert(`Role changed to ${{newRole}}!`); loadAdmins(); }}
        else {{ alert('Error: ' + data.error); }}
    }}
    
    async function changeOtherPassword() {{
        const targetUser = document.getElementById('targetUsername').value;
        const newPass = document.getElementById('newPasswordForTarget').value;
        const res = await fetch(API_URL + '/api/admin/change-other-password', {{
            method: 'POST', headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify({{admin_username: currentUser, admin_password: document.getElementById('loginPassword').value, target_username: targetUser, new_password: newPass}})
        }});
        const data = await res.json();
        if(data.success) {{ alert('Password changed!'); }}
        else {{ alert('Error: ' + data.error); }}
    }}
    
    async function manageCredits() {{
        const username = document.getElementById('creditUsername').value;
        const amount = parseFloat(document.getElementById('creditAmount').value);
        const res = await fetch(API_URL + '/api/admin/manage-credits', {{
            method: 'POST', headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify({{admin_username: currentUser, admin_password: document.getElementById('loginPassword').value, target_username: username, amount: amount}})
        }});
        const data = await res.json();
        if(data.success) {{ alert(`New balance: ${{data.new_balance}}`); loadAdmins(); if(username === currentUser) loadStats(); }}
        else {{ alert('Error: ' + data.error); }}
    }}
    
    async function changePassword() {{
        const oldPass = document.getElementById('oldPassword').value;
        const newPass = document.getElementById('newPassword').value;
        const confirmPass = document.getElementById('confirmPassword').value;
        if(newPass !== confirmPass) {{ alert('Passwords do not match!'); return; }}
        const res = await fetch(API_URL + '/api/admin/change-password', {{
            method: 'POST', headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify({{username: currentUser, old_password: oldPass, new_password: newPass}})
        }});
        const data = await res.json();
        const resultDiv = document.getElementById('passwordResult');
        resultDiv.style.display = 'block';
        if(data.success) {{ resultDiv.innerHTML = '<i class="fas fa-check-circle"></i> Password changed! Please login again.'; setTimeout(() => location.reload(), 2000); }}
        else {{ resultDiv.innerHTML = '<i class="fas fa-exclamation-triangle"></i> ' + data.error; }}
    }}
    
    async function loadMonitor() {{
        const res = await fetch(API_URL + '/api/admin/get-monitor-data', {{
            method: 'POST', headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify({{admin_username: currentUser, admin_password: document.getElementById('loginPassword').value}})
        }});
        const data = await res.json();
        document.getElementById('monitorData').innerHTML = `
            <i class="fas fa-chart-pie"></i> <strong>SYSTEM STATUS</strong><br><br>
            <i class="fas fa-flask"></i> Trials: ${{data.my_trials}}<br>
            <i class="fas fa-star"></i> Custom: ${{data.my_custom}}<br>
            <i class="fas fa-gem"></i> Permanent: ${{data.my_permanent}}<br>
            <i class="fas fa-history"></i> History: ${{data.history_count}}<br>
            <i class="fas fa-envelope"></i> Pending: ${{data.pending_requests}}<br>
            <i class="fas fa-link"></i> Active Links: ${{data.active_links}}<br>
            <i class="fas fa-users"></i> Active Users: ${{data.active_users}}<br>
            <hr style="margin: 10px 0; border-color: var(--border);">
            <i class="fas fa-clock"></i> Server Time: ${{data.server_time}}
        `;
    }}
    
    async function deleteTrial(key) {{ if(confirm('Delete?')) {{ await fetch(API_URL + '/api/admin/delete-trial', {{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{admin_username:currentUser,admin_password:document.getElementById('loginPassword').value,license_key:key}})}}); loadMyTrials(); loadStats(); }} }}
    async function deleteCustomActivation(key) {{ if(confirm('Delete?')) {{ await fetch(API_URL + '/api/admin/delete-custom-activation', {{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{admin_username:currentUser,admin_password:document.getElementById('loginPassword').value,license_key:key}})}}); loadMyCustom(); loadStats(); }} }}
    async function deletePermanentLicense(key) {{ if(confirm('Delete?')) {{ await fetch(API_URL + '/api/admin/delete-permanent-license', {{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{admin_username:currentUser,admin_password:document.getElementById('loginPassword').value,license_key:key}})}}); loadMyPermanent(); loadStats(); }} }}
    async function deleteAdmin(username) {{ if(confirm(`Delete ${{username}}?`)) {{ await fetch(API_URL + '/api/admin/delete-admin', {{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{admin_username:currentUser,admin_password:document.getElementById('loginPassword').value,target_username:username,role:'admin'}})}}); loadAdmins(); }} }}
    async function deleteModerator(username) {{ if(confirm(`Delete ${{username}}?`)) {{ await fetch(API_URL + '/api/admin/delete-admin', {{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{admin_username:currentUser,admin_password:document.getElementById('loginPassword').value,target_username:username,role:'moderator'}})}}); loadAdmins(); }} }}
    
    function closeModal() {{ document.getElementById('credsModal').style.display = 'none'; }}
    setInterval(() => {{ if(document.getElementById('mainPanel').style.display === 'block') loadStats(); }}, 30000);
</script>
</body>
</html>
"""
    return ADMIN_HTML

# ==================================================
# 🎨 MODERN USER PORTAL HTML
# ==================================================
def get_user_portal_html():
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>JEPFX • License Portal</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Inter', 'Segoe UI', sans-serif;
        }}
        
        {get_theme_css()}
        
        body {{
            min-height: 100vh;
            transition: all 0.3s ease;
        }}
        
        .container {{
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
        }}
        
        .header {{
            text-align: center;
            margin-bottom: 40px;
            padding: 30px 0;
        }}
        
        .header h1 {{
            font-size: 42px;
            font-weight: 800;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
            margin-bottom: 10px;
        }}
        
        .header p {{
            color: var(--text-secondary);
            font-size: 16px;
        }}
        
        .card {{
            background: var(--card-bg);
            backdrop-filter: blur(10px);
            border-radius: 24px;
            padding: 32px;
            margin-bottom: 24px;
            border: 1px solid var(--border);
            transition: transform 0.3s, box-shadow 0.3s;
        }}
        
        .card:hover {{
            transform: translateY(-4px);
            box-shadow: 0 20px 40px rgba(0,0,0,0.2);
        }}
        
        .card h2 {{
            font-size: 24px;
            margin-bottom: 20px;
            font-weight: 600;
        }}
        
        .card h2 i {{
            color: var(--primary);
            margin-right: 12px;
        }}
        
        input, select, textarea {{
            width: 100%;
            padding: 14px 16px;
            margin: 10px 0;
            border: 1px solid var(--border);
            border-radius: 12px;
            outline: none;
            font-size: 15px;
            transition: all 0.3s;
        }}
        
        input:focus, select:focus, textarea:focus {{
            border-color: var(--primary);
            box-shadow: 0 0 0 3px rgba(124,58,237,0.2);
        }}
        
        button {{
            background: var(--primary);
            color: white;
            padding: 14px 28px;
            border: none;
            border-radius: 12px;
            cursor: pointer;
            font-size: 16px;
            font-weight: 600;
            transition: all 0.3s;
            width: 100%;
        }}
        
        button:hover {{
            transform: translateY(-2px);
            filter: brightness(1.05);
        }}
        
        button:disabled {{
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }}
        
        .status-box {{
            border-radius: 16px;
            padding: 20px;
            margin: 20px 0;
            border-left: 4px solid var(--primary);
            background: rgba(0,0,0,0.2);
        }}
        
        .status-active {{ border-left-color: var(--secondary); }}
        .status-expired {{ border-left-color: var(--danger); }}
        .status-warning {{ border-left-color: var(--warning); }}
        
        .info-row {{
            display: flex;
            justify-content: space-between;
            padding: 12px 0;
            border-bottom: 1px solid var(--border);
        }}
        
        .info-label {{
            color: var(--text-secondary);
            font-weight: 500;
        }}
        
        .info-value {{
            color: var(--text);
            font-weight: 600;
        }}
        
        .contact-buttons {{
            display: flex;
            gap: 12px;
            margin-top: 24px;
        }}
        
        .contact-btn {{
            flex: 1;
            text-align: center;
            text-decoration: none;
            padding: 14px;
            border-radius: 12px;
            color: white;
            font-weight: 600;
            transition: all 0.3s;
        }}
        
        .telegram-btn {{
            background: linear-gradient(135deg, #0088cc, #006699);
        }}
        
        .telegram-btn:hover {{
            transform: translateY(-2px);
            filter: brightness(1.05);
        }}
        
        .request-form {{
            display: none;
            margin-top: 24px;
            padding-top: 24px;
            border-top: 1px solid var(--border);
        }}
        
        .request-form.show {{
            display: block;
            animation: fadeIn 0.3s ease;
        }}
        
        .alert-success {{
            background: rgba(16,185,129,0.15);
            border: 1px solid var(--secondary);
            color: var(--secondary);
            padding: 14px;
            border-radius: 12px;
            margin: 15px 0;
        }}
        
        .alert-error {{
            background: rgba(239,68,68,0.15);
            border: 1px solid var(--danger);
            color: var(--danger);
            padding: 14px;
            border-radius: 12px;
            margin: 15px 0;
        }}
        
        .alert-info {{
            background: rgba(59,130,246,0.15);
            border: 1px solid var(--primary);
            color: var(--primary);
            padding: 14px;
            border-radius: 12px;
            margin: 15px 0;
        }}
        
        .badge {{
            display: inline-block;
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
        }}
        
        .badge-active {{ background: var(--secondary); color: white; }}
        .badge-expired {{ background: var(--danger); color: white; }}
        .badge-warning {{ background: var(--warning); color: #000; }}
        
        .hidden {{ display: none; }}
        
        .loading {{
            text-align: center;
            padding: 40px;
        }}
        
        .spinner {{
            border: 3px solid rgba(255,255,255,0.3);
            border-top: 3px solid var(--primary);
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto;
        }}
        
        @keyframes spin {{
            0% {{ transform: rotate(0deg); }}
            100% {{ transform: rotate(360deg); }}
        }}
        
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(10px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        
        code {{
            background: rgba(0,0,0,0.3);
            padding: 4px 8px;
            border-radius: 6px;
            font-family: monospace;
        }}
        
        .footer {{
            text-align: center;
            margin-top: 40px;
            padding: 20px;
            color: var(--text-secondary);
            font-size: 13px;
        }}
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1><i class="fas fa-key"></i> JEPFX Portal</h1>
        <p>License Management & Support System</p>
    </div>
    
    <div id="loginSection" class="card">
        <h2><i class="fas fa-lock"></i> License Login</h2>
        <p style="margin-bottom: 20px; color: var(--text-secondary);">Enter your credentials to check license status</p>
        <input type="text" id="loginUsername" placeholder="Username">
        <input type="password" id="loginPassword" placeholder="Password">
        <button onclick="checkLicense()"><i class="fas fa-sign-in-alt"></i> CHECK LICENSE STATUS</button>
        <div id="loginError" class="alert-error" style="display: none;"></div>
    </div>
    
    <div id="statusSection" class="hidden">
        <div class="card" id="statusCard">
            <div id="statusContent"></div>
            <div id="requestForm" class="request-form">
                <h3><i class="fas fa-paper-plane"></i> Request Support</h3>
                <select id="requestType">
                    <option value="extension">📅 Extension (Add more days)</option>
                    <option value="reactivation">🔄 Reactivation (Reset HWID)</option>
                    <option value="other">💬 Other Request</option>
                </select>
                <input type="number" id="requestDays" placeholder="Days to add (if extension)" value="7">
                <textarea id="requestMessage" rows="4" placeholder="Describe your request in detail..."></textarea>
                <input type="text" id="contactInfo" placeholder="Your contact (Telegram/Discord/Email)" value="t.me/">
                <button onclick="submitRequest()"><i class="fas fa-send"></i> SUBMIT REQUEST</button>
                <div id="requestResult" class="alert-info" style="display: none;"></div>
            </div>
            <div class="contact-buttons">
                <a href="https://t.me/JEPFX_0" target="_blank" class="contact-btn telegram-btn"><i class="fab fa-telegram-plane"></i> Telegram Support</a>
            </div>
        </div>
    </div>
    
    <div class="footer">
        <p>© 2024 JEPFX License System | All rights reserved</p>
    </div>
</div>

{THEME_SELECTOR_HTML}

<script>
    let currentLicenseKey = null;
    let currentUsername = null;
    
    async function checkLicense() {{
        const username = document.getElementById('loginUsername').value;
        const password = document.getElementById('loginPassword').value;
        
        if(!username || !password) {{
            showError('Please enter username and password');
            return;
        }}
        
        const btn = event.target;
        btn.disabled = true;
        btn.innerHTML = '<div class="spinner" style="width:20px;height:20px;"></div> Checking...';
        
        try {{
            const res = await fetch('/api/user/check-license', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{username: username, password: password}})
            }});
            const data = await res.json();
            
            if(data.success) {{
                currentLicenseKey = data.license_key;
                currentUsername = username;
                displayLicenseStatus(data);
                document.getElementById('loginSection').classList.add('hidden');
                document.getElementById('statusSection').classList.remove('hidden');
            }} else {{
                showError(data.error || 'Invalid credentials or license not found');
            }}
        }} catch (error) {{
            showError('Connection error. Please try again.');
        }}
        
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-sign-in-alt"></i> CHECK LICENSE STATUS';
    }}
    
    function displayLicenseStatus(data) {{
        const statusClass = data.is_expired ? 'status-expired' : (data.days_left < 3 ? 'status-warning' : 'status-active');
        const badgeClass = data.is_expired ? 'badge-expired' : (data.days_left < 3 ? 'badge-warning' : 'badge-active');
        const statusText = data.is_expired ? 'EXPIRED' : (data.days_left < 3 ? 'EXPIRING SOON' : 'ACTIVE');
        
        let hwidHtml = '';
        if(data.hwids && data.hwids.length > 0) {{
            hwidHtml = '<div class="info-row"><span class="info-label"><i class="fas fa-desktop"></i> Activated Devices:</span><span class="info-value">' + data.hwids.length + ' device(s)</span></div>';
        }}
        
        let activationStatus = '';
        if(!data.activated && data.license_type === 'trial') {{
            activationStatus = '<div class="alert-info" style="margin:15px 0;"><i class="fas fa-info-circle"></i> License not activated yet. It will start counting down after first activation!</div>';
        }}
        
        const html = `
            <div class="status-box ${{statusClass}}">
                <div class="info-row"><span class="info-label"><i class="fas fa-key"></i> License Key:</span><span class="info-value"><code>${{data.license_key}}</code></span></div>
                <div class="info-row"><span class="info-label"><i class="fas fa-user"></i> Username:</span><span class="info-value">${{data.username}}</span></div>
                <div class="info-row"><span class="info-label"><i class="fas fa-tag"></i> License Type:</span><span class="info-value"><span class="badge badge-active">${{data.license_type}}</span></span></div>
                <div class="info-row"><span class="info-label"><i class="fas fa-calendar"></i> Expires:</span><span class="info-value">${{data.expires_at || 'NEVER'}}</span></div>
                <div class="info-row"><span class="info-label"><i class="fas fa-chart-line"></i> Status:</span><span class="info-value"><span class="badge ${{badgeClass}}">${{statusText}}</span></span></div>
                ${{data.days_left !== null ? `<div class="info-row"><span class="info-label"><i class="fas fa-hourglass-half"></i> Days Left:</span><span class="info-value">${{data.days_left}} days</span></div>` : ''}}
                ${{data.max_devices ? `<div class="info-row"><span class="info-label"><i class="fas fa-microchip"></i> Max Devices:</span><span class="info-value">${{data.max_devices}}</span></div>` : ''}}
                ${{hwidHtml}}
                ${{data.created_at ? `<div class="info-row"><span class="info-label"><i class="fas fa-plus-circle"></i> Created:</span><span class="info-value">${{new Date(data.created_at).toLocaleString()}}</span></div>` : ''}}
                ${{data.last_used ? `<div class="info-row"><span class="info-label"><i class="fas fa-clock"></i> Last Used:</span><span class="info-value">${{new Date(data.last_used).toLocaleString()}}</span></div>` : ''}}
            </div>
            ${{activationStatus}}
            ${{data.is_expired ? '<div class="alert-error"><i class="fas fa-exclamation-triangle"></i> Your license has expired. Submit a request for reactivation.</div>' : ''}}
            ${{!data.is_expired && data.days_left < 7 && data.days_left !== null ? '<div class="alert-warning" style="background:rgba(245,158,11,0.15);border:1px solid var(--warning);padding:14px;border-radius:12px;margin:15px 0;"><i class="fas fa-hourglass-end"></i> Your license is expiring soon! Submit a request to extend.</div>' : ''}}
        `;
        
        document.getElementById('statusContent').innerHTML = html;
        document.getElementById('requestForm').classList.add('show');
    }}
    
    async function submitRequest() {{
        const requestType = document.getElementById('requestType').value;
        const requestDays = document.getElementById('requestDays').value;
        const requestMessage = document.getElementById('requestMessage').value;
        const contactInfo = document.getElementById('contactInfo').value;
        
        if(!requestMessage) {{
            alert('Please describe your request');
            return;
        }}
        
        const res = await fetch('/api/user/submit-request', {{
            method: 'POST',
            headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify({{
                license_key: currentLicenseKey,
                username: currentUsername,
                request_type: requestType,
                days_requested: parseInt(requestDays) || 0,
                message: requestMessage,
                contact: contactInfo
            }})
        }});
        
        const data = await res.json();
        const resultDiv = document.getElementById('requestResult');
        
        if(data.success) {{
            resultDiv.className = 'alert-success';
            resultDiv.innerHTML = '<i class="fas fa-check-circle"></i> Request submitted successfully! Admin will review and contact you soon.';
            resultDiv.style.display = 'block';
            document.getElementById('requestMessage').value = '';
            setTimeout(() => {{ resultDiv.style.display = 'none'; }}, 5000);
        }} else {{
            resultDiv.className = 'alert-error';
            resultDiv.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Error: ' + data.error;
            resultDiv.style.display = 'block';
        }}
    }}
    
    function showError(msg) {{
        const errorDiv = document.getElementById('loginError');
        errorDiv.innerHTML = '<i class="fas fa-exclamation-circle"></i> ' + msg;
        errorDiv.style.display = 'block';
        setTimeout(() => {{ errorDiv.style.display = 'none'; }}, 5000);
    }}
</script>
</body>
</html>
"""
    return USER_PORTAL_HTML

# ==================================================
# 🔐 API ENDPOINTS
# ==================================================

@app.route('/api/set-theme', methods=['POST'])
def set_theme():
    global CURRENT_THEME
    data = request.get_json()
    theme = data.get("theme", "dark")
    if theme in THEMES:
        CURRENT_THEME = theme
        save_data()
    return jsonify({"success": True})

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

@app.route('/api/admin/generate-registration-link', methods=['POST'])
def admin_generate_registration_link():
    data = request.get_json()
    auth = check_admin_auth(data)
    if not auth["authorized"]:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    # Moderators can only generate trial links
    license_type = data.get("license_type", "trial")
    if auth["role"] == "moderator" and license_type == "custom":
        return jsonify({"success": False, "error": "Moderators can only generate trial registration links"}), 403

    duration_value = float(data.get("duration_value", 1))
    duration_type = data.get("duration_type", "days")
    max_devices = int(data.get("max_devices", 1))

    # Calculate credit cost (same pricing as direct creation)
    credits_cost = calculate_credits_cost(license_type, duration_value, duration_type)
    if auth["role"] != "master":
        if not deduct_credits(auth["username"], credits_cost):
            return jsonify({"success": False, "error": f"Insufficient credits. Need {credits_cost} credits"}), 400

    token = generate_registration_link(license_type, duration_value, duration_type, max_devices, auth["username"], credits_cost)

    save_data()
    remaining = get_credits(auth["username"])

    return jsonify({
        "success": True,
        "token": token,
        "credits_used": credits_cost,
        "remaining_credits": remaining
    }), 200

@app.route('/api/admin/get-registration-links', methods=['POST'])
def admin_get_registration_links():
    data = request.get_json()
    auth = check_admin_auth(data)
    if not auth["authorized"]:
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    links = []
    for token, link in REGISTRATION_LINKS.items():
        if auth["role"] == "master" or link.get("created_by") == auth["username"]:
            links.append({
                "token": token,
                "license_type": link["license_type"],
                "duration_value": link["duration_value"],
                "duration_type": link["duration_type"],
                "max_devices": link["max_devices"],
                "created_by": link["created_by"],
                "created_at": link["created_at"],
                "expires_at": link["expires_at"],
                "used": link["used"],
                "used_by": link["used_by"],
                "used_at": link["used_at"]
            })
    
    return jsonify({"links": links}), 200

@app.route('/api/admin/delete-registration-link', methods=['POST'])
def admin_delete_registration_link():
    data = request.get_json()
    auth = check_admin_auth(data)
    if not auth["authorized"]:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    token = data.get("token", "")

    if token in REGISTRATION_LINKS:
        link = REGISTRATION_LINKS[token]
        if auth["role"] != "master" and link.get("created_by") != auth["username"]:
            return jsonify({"success": False, "error": "Not your link"}), 403

        # Refund credits if link was not used
        refunded = 0
        if not link.get("used") and link.get("credits_cost", 0) > 0:
            refunded = link["credits_cost"]
            add_credits(link["created_by"], refunded)

        del REGISTRATION_LINKS[token]
        save_data()
        return jsonify({"success": True, "refunded_credits": refunded}), 200

    return jsonify({"success": False, "error": "Link not found"}), 404

@app.route('/register/<token>')
def register_page(token):
    link_data = REGISTRATION_LINKS.get(token)
    
    if not link_data:
        return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head><title>Invalid Link</title></head>
        <body style="background: #0f0c29; color: white; font-family: Arial; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0;">
            <div style="text-align: center;">
                <h1>❌ Invalid or Expired Link</h1>
                <p>This registration link is invalid, expired, or has already been used.</p>
                <a href="/user" style="color: #7C3AED;">Go to Portal</a>
            </div>
        </body>
        </html>
        """)
    
    if link_data.get("used"):
        return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head><title>Link Used</title></head>
        <body style="background: #0f0c29; color: white; font-family: Arial; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0;">
            <div style="text-align: center;">
                <h1>⚠️ Link Already Used</h1>
                <p>This registration link has already been used.</p>
                <a href="/user" style="color: #7C3AED;">Go to Portal</a>
            </div>
        </body>
        </html>
        """)
    
    now = datetime.utcnow()
    if link_data.get("expires_at"):
        exp_time = datetime.fromisoformat(link_data["expires_at"])
        if now > exp_time:
            return render_template_string("""
            <!DOCTYPE html>
            <html>
            <head><title>Link Expired</title></head>
            <body style="background: #0f0c29; color: white; font-family: Arial; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0;">
                <div style="text-align: center;">
                    <h1>⏰ Link Expired</h1>
                    <p>This registration link has expired.</p>
                    <a href="/user" style="color: #7C3AED;">Go to Portal</a>
                </div>
            </body>
            </html>
            """)
    
    return render_template_string(get_registration_html(token, link_data))

@app.route('/api/register-from-link/<token>', methods=['POST'])
def register_from_link(token):
    data = request.get_json()
    license_key = data.get("license_key", "").strip().upper()
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    
    link_data = REGISTRATION_LINKS.get(token)
    
    if not link_data:
        return jsonify({"success": False, "error": "Invalid link"}), 400
    
    if link_data.get("used"):
        return jsonify({"success": False, "error": "Link already used"}), 400
    
    now = datetime.utcnow()
    if link_data.get("expires_at"):
        exp_time = datetime.fromisoformat(link_data["expires_at"])
        if now > exp_time:
            return jsonify({"success": False, "error": "Link expired"}), 400
    
    if not license_key or not username or not password:
        return jsonify({"success": False, "error": "All fields are required"}), 400
    
    # Check if license key already exists
    if license_key in CUSTOM_ACTIVATIONS or license_key in TRIAL_LICENSES or license_key in PERMANENT_LICENSES:
        return jsonify({"success": False, "error": "License key already exists"}), 400
    
    if username in VALID_USERS or username in TRIAL_USERS:
        return jsonify({"success": False, "error": "Username already taken"}), 400
    
    license_type = link_data["license_type"]
    duration_value = link_data["duration_value"]
    duration_type = link_data["duration_type"]
    max_devices = link_data["max_devices"]
    
    expires_at = None
    if duration_type != "unlimited":
        if duration_type == "hours":
            expires_at = now + timedelta(hours=duration_value)
        elif duration_type == "days":
            expires_at = now + timedelta(days=duration_value)
        elif duration_type == "weeks":
            expires_at = now + timedelta(weeks=duration_value)
        elif duration_type == "months":
            expires_at = now + timedelta(days=duration_value * 30)
        elif duration_type == "years":
            expires_at = now + timedelta(days=duration_value * 365)
    
    if license_type == "trial":
        # Trial: registered but NOT activated. Timer starts on first tool login.
        TRIAL_LICENSES[license_key] = {
            "type": "trial",
            "owner": link_data["created_by"],
            "hwids": [],
            "max_devices": max_devices,
            "duration_hours": duration_value if duration_type == "hours" else (
                duration_value * 24 if duration_type == "days" else
                duration_value * 168 if duration_type == "weeks" else
                duration_value * 720 if duration_type == "months" else
                duration_value * 8760 if duration_type == "years" else duration_value
            ),
            "start_time": None,
            "expires_at": None,  # Will be set on first activation via /api/activate
            "activated": False,
            "created_at": now.isoformat()
        }
        TRIAL_USERS[username] = {"password": password, "linked_license": license_key}

    else:  # custom — activate immediately
        CUSTOM_ACTIVATIONS[license_key] = {
            "username": username,
            "password": password,
            "license_key": license_key,
            "owner": link_data["created_by"],
            "hwids": [],
            "max_devices": max_devices,
            "expires_at": expires_at.isoformat() if expires_at else None,
            "created_at": now.isoformat(),
            "activated": True,
            "activated_at": now.isoformat()
        }
        VALID_USERS[username] = password
    
    # Mark link as used
    REGISTRATION_LINKS[token]["used"] = True
    REGISTRATION_LINKS[token]["used_by"] = username
    REGISTRATION_LINKS[token]["used_at"] = now.isoformat()
    
    add_to_history(license_key, username, password, license_type.upper(), link_data["created_by"], 
                   expires_at.isoformat() if expires_at else "UNLIMITED", 
                   {"duration_type": duration_type, "duration_value": duration_value, "max_devices": max_devices})
    
    save_data()
    
    return jsonify({
        "success": True,
        "message": "License created successfully! Redirecting to portal..."
    }), 200

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

@app.route('/api/admin/change-other-password', methods=['POST'])
def change_other_password():
    data = request.get_json()
    auth = check_admin_auth(data)
    if not auth["authorized"] or auth["role"] != "master":
        return jsonify({"success": False, "error": "Only master admin can change other passwords"}), 401
    
    target_username = data.get("target_username", "")
    new_password = data.get("new_password", "")
    
    if not target_username or not new_password:
        return jsonify({"success": False, "error": "Username and new password required"}), 400
    
    if target_username in ADMINS:
        ADMINS[target_username]["password"] = new_password
        save_data()
        return jsonify({"success": True}), 200
    
    if target_username in MODERATORS:
        MODERATORS[target_username]["password"] = new_password
        save_data()
        return jsonify({"success": True}), 200
    
    return jsonify({"success": False, "error": "User not found"}), 404

@app.route('/api/admin/change-role', methods=['POST'])
def change_user_role():
    data = request.get_json()
    auth = check_admin_auth(data)
    if not auth["authorized"] or auth["role"] != "master":
        return jsonify({"success": False, "error": "Only master admin can change roles"}), 401
    
    target_username = data.get("target_username", "")
    new_role = data.get("new_role", "")
    
    if target_username == MASTER_ADMIN["username"]:
        return jsonify({"success": False, "error": "Cannot change master admin role"}), 400
    
    if target_username in ADMINS:
        user_data = ADMINS.pop(target_username)
    elif target_username in MODERATORS:
        user_data = MODERATORS.pop(target_username)
    else:
        return jsonify({"success": False, "error": "User not found"}), 404
    
    if new_role == "admin":
        ADMINS[target_username] = user_data
    else:
        MODERATORS[target_username] = user_data
    
    save_data()
    return jsonify({"success": True}), 200

@app.route('/api/admin/get-stats', methods=['POST'])
def get_stats():
    data = request.get_json()
    auth = check_admin_auth(data)
    if not auth["authorized"]:
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    licenses = get_licenses_by_owner(auth["username"], auth["role"])
    history = get_history_by_owner(auth["username"], auth["role"])
    pending_requests = sum(1 for r in USER_REQUESTS if r.get("status") == "pending" and (auth["role"] == "master" or r.get("license_key") in licenses["trials"] or r.get("license_key") in licenses["custom"]))
    
    # Count active registration links for this admin
    active_links = sum(1 for link in REGISTRATION_LINKS.values() 
                      if not link.get("used") and (auth["role"] == "master" or link.get("created_by") == auth["username"]))
    
    return jsonify({
        "success": True,
        "trials": len(licenses["trials"]),
        "custom": len(licenses["custom"]),
        "permanent": len(licenses["permanent"]),
        "history_count": len(history),
        "pending_requests": pending_requests,
        "active_links": active_links,
        "user_credits": auth.get("credits", "Unlimited")
    }), 200

@app.route('/api/admin/generate-trial', methods=['POST'])
def generate_trial():
    data = request.get_json()
    auth = check_admin_auth(data)
    if not auth["authorized"]:
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    dur = int(data.get("duration_hours", 3))
    max_devices = int(data.get("max_devices", 1))
    # Fixed trial pricing by duration
    TRIAL_FIXED_CREDITS = {3: 2, 6: 3, 12: 4, 24: 5, 72: 10, 168: 20, 720: 50}
    credits_cost = TRIAL_FIXED_CREDITS.get(dur, round(dur * 0.1, 2))
    
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
        "max_devices": max_devices,
        "duration_hours": dur,
        "start_time": None,
        "expires_at": None,
        "activated": False,
        "created_at": datetime.utcnow().isoformat()
    }
    TRIAL_USERS[user] = {"password": pwd, "linked_license": lic}
    
    add_to_history(lic, user, pwd, "Trial", auth["username"], "NOT ACTIVATED YET", {"duration_hours": dur, "max_devices": max_devices})
    
    save_data()
    remaining = get_credits(auth["username"])
    
    return jsonify({
        "success": True,
        "license_key": lic,
        "username": user,
        "password": pwd,
        "credits_used": credits_cost,
        "remaining_credits": remaining,
        "max_devices": max_devices
    }), 200

@app.route('/api/admin/create-custom-activation', methods=['POST'])
def create_custom_activation():
    data = request.get_json()
    auth = check_admin_auth(data)
    if not auth["authorized"] or auth["role"] == "moderator":
        return jsonify({"success": False, "error": "Moderators cannot create custom licenses"}), 403
    
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    license_key = data.get("license_key", "").strip().upper()
    duration_type = data.get("duration_type", "hours")
    duration_value = float(data.get("duration_value", 0))
    max_devices = int(data.get("max_devices", 1))
    
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
        "max_devices": max_devices,
        "expires_at": expires_at.isoformat() if expires_at else None,
        "created_at": now.isoformat(),
        "activated": False
    }
    
    VALID_USERS[username] = password
    
    add_to_history(license_key, username, password, "Custom", auth["username"], 
                   expires_at.isoformat() if expires_at else "UNLIMITED", 
                   {"duration_type": duration_type, "duration_value": duration_value, "max_devices": max_devices})
    
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
    if not auth["authorized"] or auth["role"] != "master":
        return jsonify({"success": False, "error": "Only master admin can create permanent licenses"}), 403
    
    license_key = data.get("license_key", "").strip().upper()
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    max_devices = int(data.get("max_devices", 1))
    
    if not license_key:
        return jsonify({"success": False, "error": "License key required"}), 400
    
    PERMANENT_LICENSES[license_key] = {
        "type": "permanent",
        "owner": auth["username"],
        "username": username if username else None,
        "password": password if password else None,
        "hwids": [],
        "max_devices": max_devices,
        "expires_at": None,
        "created_at": datetime.utcnow().isoformat()
    }
    
    if username and password:
        VALID_USERS[username] = password
    
    add_to_history(license_key, username if username else "N/A", password if password else "N/A", 
                   "Permanent", auth["username"], "NEVER", {"max_devices": max_devices})
    
    save_data()
    remaining = get_credits(auth["username"])
    
    return jsonify({
        "success": True,
        "remaining_credits": remaining
    }), 200

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
            activated = False
            if v.get("activated"):
                activated = True
                if v.get("expires_at"):
                    exp = datetime.fromisoformat(v["expires_at"])
                    if exp > now:
                        status = "ACTIVE"
                    else:
                        status = "EXPIRED"
            elif v.get("start_time") is None:
                status = "AWAITING ACTIVATION"
            
            hwid_count = len(v.get("hwids", []))
            
            list_trials.append({
                "license_key": k,
                "duration_hours": f"{v['duration_hours']}h",
                "max_devices": v.get("max_devices", 1),
                "hwid_count": hwid_count,
                "activated": activated,
                "expires_at": v.get("expires_at") or "Not activated",
                "status": status
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
            
            list_custom.append({
                "license_key": k,
                "username": v.get("username"),
                "password": v.get("password"),
                "max_devices": v.get("max_devices", 1),
                "hwids": v.get("hwids", []),
                "expires_at": v.get("expires_at") or "UNLIMITED",
                "status": status
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
            list_permanent.append({
                "license_key": k,
                "username": v.get("username"),
                "max_devices": v.get("max_devices", 1),
                "hwids": v.get("hwids", []),
                "expires_at": v.get("expires_at") or "UNLIMITED",
                "status": "ACTIVE"
            })
    
    return jsonify({"licenses": list_permanent}), 200

@app.route('/api/admin/get-history', methods=['POST'])
def get_history():
    data = request.get_json()
    auth = check_admin_auth(data)
    if not auth["authorized"]:
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    history = get_history_by_owner(auth["username"], auth["role"])
    history.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    return jsonify({"history": history}), 200

@app.route('/api/admin/export-history', methods=['GET'])
def export_history():
    admin_username = request.args.get("admin_username")
    admin_password = request.args.get("admin_password")
    
    auth = check_admin_auth({"admin_username": admin_username, "admin_password": admin_password})
    if not auth["authorized"]:
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    history = get_history_by_owner(auth["username"], auth["role"])
    
    import csv
    from io import StringIO
    
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Created At', 'License Key', 'Username', 'Password', 'Type', 'Owner', 'Expires At'])
    
    for item in history:
        writer.writerow([
            item.get('created_at', ''),
            item.get('license_key', ''),
            item.get('username', ''),
            item.get('password', ''),
            item.get('type', ''),
            item.get('owner', ''),
            item.get('expires_at', '')
        ])
    
    output.seek(0)
    return Response(output.getvalue(), mimetype='text/csv', 
                   headers={"Content-Disposition": "attachment;filename=license_history.csv"})

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
    history = get_history_by_owner(auth["username"], auth["role"])
    pending_requests = sum(1 for r in USER_REQUESTS if r.get("status") == "pending")
    
    active_links = sum(1 for link in REGISTRATION_LINKS.values() 
                      if not link.get("used") and (auth["role"] == "master" or link.get("created_by") == auth["username"]))
    
    active_users = set()
    for logs in USAGE_LOGS.values():
        for log in logs[-10:]:
            if "hwid" in log.get("details", {}):
                active_users.add(log["details"]["hwid"])
    
    return jsonify({
        "my_trials": len(licenses["trials"]),
        "my_custom": len(licenses["custom"]),
        "my_permanent": len(licenses["permanent"]),
        "history_count": len(history),
        "pending_requests": pending_requests,
        "active_links": active_links,
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

@app.route('/api/admin/get-requests', methods=['POST'])
def admin_get_requests():
    data = request.get_json()
    auth = check_admin_auth(data)
    if not auth["authorized"]:
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    if auth["role"] == "master":
        requests = USER_REQUESTS
    else:
        owned_licenses = set()
        for k in TRIAL_LICENSES:
            if TRIAL_LICENSES[k].get("owner") == auth["username"]:
                owned_licenses.add(k)
        for k in CUSTOM_ACTIVATIONS:
            if CUSTOM_ACTIVATIONS[k].get("owner") == auth["username"]:
                owned_licenses.add(k)
        requests = [r for r in USER_REQUESTS if r.get("license_key") in owned_licenses]
    
    requests.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return jsonify({"requests": requests}), 200

@app.route('/api/admin/approve-request', methods=['POST'])
def admin_approve_request():
    data = request.get_json()
    auth = check_admin_auth(data)
    if not auth["authorized"]:
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    req_index = data.get("request_index")
    license_key = data.get("license_key")
    request_type = data.get("request_type")
    days_to_add = data.get("days_to_add", 7)
    
    if req_index is None or req_index >= len(USER_REQUESTS):
        return jsonify({"success": False, "error": "Request not found"}), 404
    
    req = USER_REQUESTS[req_index]
    
    if auth["role"] != "master":
        if license_key in TRIAL_LICENSES and TRIAL_LICENSES[license_key].get("owner") != auth["username"]:
            return jsonify({"success": False, "error": "Not your license"}), 403
        if license_key in CUSTOM_ACTIVATIONS and CUSTOM_ACTIVATIONS[license_key].get("owner") != auth["username"]:
            return jsonify({"success": False, "error": "Not your license"}), 403
    
    now = datetime.utcnow()
    
    if request_type == "extension":
        if license_key in CUSTOM_ACTIVATIONS:
            current_exp = CUSTOM_ACTIVATIONS[license_key].get("expires_at")
            if current_exp:
                new_exp = datetime.fromisoformat(current_exp) + timedelta(days=days_to_add)
            else:
                new_exp = now + timedelta(days=days_to_add)
            CUSTOM_ACTIVATIONS[license_key]["expires_at"] = new_exp.isoformat()
        elif license_key in TRIAL_LICENSES:
            current_exp = TRIAL_LICENSES[license_key].get("expires_at")
            if current_exp:
                new_exp = datetime.fromisoformat(current_exp) + timedelta(days=days_to_add)
            else:
                new_exp = now + timedelta(days=days_to_add)
            TRIAL_LICENSES[license_key]["expires_at"] = new_exp.isoformat()
            TRIAL_LICENSES[license_key]["activated"] = True
    
    elif request_type == "reactivation":
        if license_key in CUSTOM_ACTIVATIONS:
            CUSTOM_ACTIVATIONS[license_key]["hwids"] = []
        elif license_key in TRIAL_LICENSES:
            TRIAL_LICENSES[license_key]["hwids"] = []
    
    USER_REQUESTS[req_index]["status"] = "approved"
    USER_REQUESTS[req_index]["approved_at"] = now.isoformat()
    USER_REQUESTS[req_index]["approved_by"] = auth["username"]
    
    save_data()
    return jsonify({"success": True}), 200

@app.route('/api/admin/reject-request', methods=['POST'])
def admin_reject_request():
    data = request.get_json()
    auth = check_admin_auth(data)
    if not auth["authorized"]:
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    req_index = data.get("request_index")
    
    if req_index is None or req_index >= len(USER_REQUESTS):
        return jsonify({"success": False, "error": "Request not found"}), 404
    
    USER_REQUESTS[req_index]["status"] = "rejected"
    USER_REQUESTS[req_index]["rejected_at"] = datetime.utcnow().isoformat()
    USER_REQUESTS[req_index]["rejected_by"] = auth["username"]
    
    save_data()
    return jsonify({"success": True}), 200

# ==================================================
# 👥 USER PORTAL ENDPOINTS
# ==================================================

@app.route('/user')
def user_portal():
    return render_template_string(get_user_portal_html())

@app.route('/api/user/check-license', methods=['POST'])
def user_check_license():
    data = request.get_json()
    username = data.get("username", "")
    password = data.get("password", "")
    
    license_key, license_type, license_data = find_license_by_credentials(username, password)
    
    if not license_key:
        return jsonify({"success": False, "error": "Invalid username or password"}), 401
    
    now = datetime.utcnow()
    expires_at = license_data.get("expires_at")
    is_expired = False
    days_left = None
    activated = license_data.get("activated", False)
    
    if license_type == "trial" and not activated:
        days_left = None
        is_expired = False
    elif expires_at and expires_at not in ["NEVER", "UNLIMITED"]:
        try:
            exp_time = datetime.fromisoformat(expires_at)
            if now > exp_time:
                is_expired = True
            else:
                days_left = round((exp_time - now).days, 1)
        except:
            pass
    
    usage_stats = get_usage_stats(license_key)
    
    return jsonify({
        "success": True,
        "license_key": license_key,
        "username": username,
        "license_type": license_type,
        "expires_at": expires_at if expires_at else ("Not activated yet" if not activated else "NEVER"),
        "is_expired": is_expired,
        "days_left": days_left,
        "activated": activated,
        "max_devices": license_data.get("max_devices", 1),
        "hwids": license_data.get("hwids", []),
        "usage_count": usage_stats["total_usage"],
        "created_at": license_data.get("created_at"),
        "last_used": usage_stats["last_used"]
    }), 200

@app.route('/api/user/submit-request', methods=['POST'])
def user_submit_request():
    data = request.get_json()
    license_key = data.get("license_key", "")
    username = data.get("username", "")
    request_type = data.get("request_type", "extension")
    days_requested = data.get("days_requested", 7)
    message = data.get("message", "")
    contact = data.get("contact", "")
    
    if not license_key or not username or not message:
        return jsonify({"success": False, "error": "Missing required fields"}), 400
    
    USER_REQUESTS.append({
        "license_key": license_key,
        "username": username,
        "request_type": request_type,
        "days_requested": days_requested,
        "message": message,
        "contact": contact,
        "status": "pending",
        "created_at": datetime.utcnow().isoformat()
    })
    save_data()
    
    return jsonify({"success": True, "message": "Request submitted successfully"}), 200

# ==================================================
# 🔑 ACTIVATION ENDPOINTS
# ==================================================

@app.route('/api/activate', methods=['POST'])
def activate():
    data = request.get_json()
    key = data.get("license_key", "").strip().upper()
    hwid = data.get("hardware_id", "").strip()
    now = datetime.utcnow()
    
    if key in CUSTOM_ACTIVATIONS:
        activation = CUSTOM_ACTIVATIONS[key]
        
        if activation.get("expires_at") and activation.get("activated", False):
            exp_time = datetime.fromisoformat(activation["expires_at"])
            if now > exp_time:
                return jsonify({"status": "expired"}), 403
        
        if "hwids" not in activation:
            activation["hwids"] = []
        
        max_devices = activation.get("max_devices", 1)
        if hwid not in activation["hwids"] and len(activation["hwids"]) >= max_devices:
            return jsonify({"status": "blocked", "msg": f"Max devices reached ({max_devices})"}), 403
        
        if hwid not in activation["hwids"]:
            activation["hwids"].append(hwid)
        
        if not activation.get("activated"):
            activation["activated"] = True
            activation["activated_at"] = now.isoformat()
        
        save_data()
        log_usage(key, "activation", {"hwid": hwid})
        return jsonify({"status": "activated", "msg": f"Activated on {len(activation['hwids'])}/{max_devices} device(s)"}), 200
    
    if key in PERMANENT_LICENSES:
        lic = PERMANENT_LICENSES[key]
        if "hwids" not in lic:
            lic["hwids"] = []
        max_devices = lic.get("max_devices", 1)
        if hwid not in lic["hwids"] and len(lic["hwids"]) >= max_devices:
            return jsonify({"status": "blocked", "msg": f"Max devices reached ({max_devices})"}), 403
        if hwid not in lic["hwids"]:
            lic["hwids"].append(hwid)
            save_data()
        log_usage(key, "activation", {"hwid": hwid})
        return jsonify({"status": "activated"}), 200
    
    if key in TRIAL_LICENSES:
        lic = TRIAL_LICENSES[key]
        if "hwids" not in lic:
            lic["hwids"] = []
        
        max_devices = lic.get("max_devices", 1)
        if hwid not in lic["hwids"] and len(lic["hwids"]) >= max_devices:
            return jsonify({"status": "blocked", "msg": f"Max devices reached ({max_devices})"}), 403
        
        if not lic.get("activated"):
            lic["activated"] = True
            lic["activated_at"] = now.isoformat()
            duration_hours = lic.get("duration_hours", 3)
            expires_at = now + timedelta(hours=duration_hours)
            lic["expires_at"] = expires_at.isoformat()
        
        if hwid not in lic["hwids"]:
            lic["hwids"].append(hwid)
        save_data()
        
        if lic.get("expires_at"):
            exp_time = datetime.fromisoformat(lic["expires_at"])
            if now > exp_time:
                return jsonify({"status": "expired"}), 403
        
        log_usage(key, "activation", {"hwid": hwid})
        return jsonify({"status": "activated", "msg": f"Activated on {len(lic['hwids'])}/{max_devices} device(s)"}), 200
    
    return jsonify({"status": "invalid"}), 403

@app.route('/api/verify-license', methods=['POST'])
def verify():
    data = request.get_json()
    hwid = data.get("hwid", "")
    key_hash = data.get("hash", "")
    now = datetime.utcnow()
    
    for key, activation in CUSTOM_ACTIVATIONS.items():
        if hashlib.sha256(key.encode()).hexdigest() == key_hash:
            if activation.get("expires_at") and activation.get("activated", False):
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
            if lic.get("expires_at") and lic.get("activated", False):
                exp_time = datetime.fromisoformat(lic["expires_at"])
                if now > exp_time:
                    return jsonify({"expired": True}), 403
            if hwid in lic.get("hwids", []):
                log_usage(key, "verification", {"hwid": hwid})
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

# ==================================================
# 🚀 ROUTES
# ==================================================

@app.route('/admin')
def admin_page():
    return render_template_string(get_admin_html())

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
            "admin_panel": "/admin",
            "user_portal": "/user",
            "register": "/register/<token>"
        }
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)