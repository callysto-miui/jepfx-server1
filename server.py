from flask import Flask, request, jsonify, render_template_string, Response
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_cors import CORS
import hashlib
from datetime import datetime, timedelta
import uuid
import json
import os
import threading
import time
import secrets

app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(16)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
CORS(app)

# ==================================================
# 📂 PERMANENT DATA SAVE
# ==================================================
DATA_FILE = "server_data.json"
CHAT_FILE = "chat_data.json"

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

ADMINS = {}  # Can access: Trial + Custom (no permanent)
MODERATORS = {}  # Can access: Trial only

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
# 📨 USER REQUESTS & REGISTRATIONS
# ==================================================
USER_REQUESTS = []  # Extension/reactivation requests
USER_REGISTRATIONS = []  # New user registration requests

VALID_USERS = {
    "JEPFX": "@JEPFX_1875",
}

# ==================================================
# 💬 CHAT DATA
# ==================================================
CHAT_MESSAGES = {}  # room_id -> list of messages
CHAT_ROOMS = {}  # room_id -> {participants, created_at, status}
ONLINE_USERS = {}  # username -> sid

# ==================================================
# 💰 CREDIT PRICING
# ==================================================
CREDIT_PRICING = {
    "trial_hour": 0.1,
    "custom_hour": 0.1,
    "custom_day": 1,
    "custom_week": 5,
    "custom_month": 10,
    "custom_year": 30,
    "custom_unlimited": 50,
    "permanent": 50
}

TELEGRAM_CONTACT = "t.me/JEPFX_0"

# ==================================================
# 💾 SAVE / LOAD DATA
# ==================================================
def load_data():
    global TRIAL_LICENSES, TRIAL_USERS, PERMANENT_LICENSES, CUSTOM_ACTIVATIONS, USAGE_LOGS, ADMINS, MODERATORS, VALID_USERS, LICENSE_HISTORY, USER_REQUESTS, USER_REGISTRATIONS
    
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
                USER_REGISTRATIONS = data.get("user_registrations", [])
            print(f"✅ DATA LOADED: {len(LICENSE_HISTORY)} licenses, {len(USER_REQUESTS)} requests, {len(USER_REGISTRATIONS)} registrations")
        except Exception as e:
            print(f"⚠️ LOAD ERROR: {e}")
            reset_data()
    else:
        reset_data()

def reset_data():
    global TRIAL_LICENSES, TRIAL_USERS, PERMANENT_LICENSES, CUSTOM_ACTIVATIONS, USAGE_LOGS, ADMINS, MODERATORS, LICENSE_HISTORY, USER_REQUESTS, USER_REGISTRATIONS
    TRIAL_LICENSES = {}
    TRIAL_USERS = {}
    PERMANENT_LICENSES = {}
    CUSTOM_ACTIVATIONS = {}
    USAGE_LOGS = {}
    ADMINS = {}
    MODERATORS = {}
    LICENSE_HISTORY = []
    USER_REQUESTS = []
    USER_REGISTRATIONS = []
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
        "user_registrations": USER_REGISTRATIONS
    }
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=2, default=str)
        print("💾 DATA SAVED SUCCESSFULLY")
    except Exception as e:
        print(f"❌ SAVE ERROR: {e}")

def load_chat_data():
    global CHAT_MESSAGES, CHAT_ROOMS
    if os.path.exists(CHAT_FILE):
        try:
            with open(CHAT_FILE, "r") as f:
                data = json.load(f)
                CHAT_MESSAGES = data.get("messages", {})
                CHAT_ROOMS = data.get("rooms", {})
            print(f"✅ CHAT DATA LOADED: {len(CHAT_MESSAGES)} rooms")
        except Exception as e:
            print(f"⚠️ CHAT LOAD ERROR: {e}")
            CHAT_MESSAGES = {}
            CHAT_ROOMS = {}
    else:
        CHAT_MESSAGES = {}
        CHAT_ROOMS = {}

def save_chat_data():
    try:
        with open(CHAT_FILE, "w") as f:
            json.dump({
                "messages": CHAT_MESSAGES,
                "rooms": CHAT_ROOMS
            }, f, indent=2, default=str)
    except Exception as e:
        print(f"⚠️ CHAT SAVE ERROR: {e}")

load_data()
load_chat_data()

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

def get_user_role(username):
    """Get role of a user for chat"""
    if username == MASTER_ADMIN["username"]:
        return "master"
    if username in ADMINS:
        return "admin"
    if username in MODERATORS:
        return "moderator"
    for key, activation in CUSTOM_ACTIVATIONS.items():
        if activation.get("username") == username:
            return "user"
    for user, user_data in TRIAL_USERS.items():
        if user == username:
            return "user"
    return None

def get_available_staff():
    """Get list of staff members (admin + moderators + master)"""
    staff = []
    
    staff.append({
        "username": MASTER_ADMIN["username"],
        "role": "master",
        "online": ONLINE_USERS.get(MASTER_ADMIN["username"]) is not None,
        "avatar": "👑"
    })
    
    for username, data in ADMINS.items():
        staff.append({
            "username": username,
            "role": "admin",
            "online": ONLINE_USERS.get(username) is not None,
            "avatar": "⚙️"
        })
    
    for username, data in MODERATORS.items():
        staff.append({
            "username": username,
            "role": "moderator",
            "online": ONLINE_USERS.get(username) is not None,
            "avatar": "🔧"
        })
    
    return staff

def get_chat_room(user1, user2):
    room_id = f"chat_{min(user1, user2)}_{max(user1, user2)}"
    if room_id not in CHAT_ROOMS:
        CHAT_ROOMS[room_id] = {
            "participants": [user1, user2],
            "created_at": datetime.utcnow().isoformat()
        }
        save_chat_data()
    return room_id

def save_chat_message(room_id, sender, receiver, message, message_type='text'):
    if room_id not in CHAT_MESSAGES:
        CHAT_MESSAGES[room_id] = []
    
    msg_data = {
        "id": uuid.uuid4().hex[:8],
        "sender": sender,
        "receiver": receiver,
        "message": message,
        "type": message_type,
        "timestamp": datetime.utcnow().isoformat(),
        "read": False
    }
    
    CHAT_MESSAGES[room_id].append(msg_data)
    
    if len(CHAT_MESSAGES[room_id]) > 1000:
        CHAT_MESSAGES[room_id] = CHAT_MESSAGES[room_id][-1000:]
    
    save_chat_data()
    return msg_data

def get_user_chats(username):
    """Get all chat conversations for a user"""
    conversations = []
    for room_id, room in CHAT_ROOMS.items():
        if username in room["participants"]:
            other = [p for p in room["participants"] if p != username][0]
            messages = CHAT_MESSAGES.get(room_id, [])
            unread = sum(1 for m in messages if m["receiver"] == username and not m.get("read", False))
            last_msg = messages[-1] if messages else None
            
            conversations.append({
                "room_id": room_id,
                "other_user": other,
                "other_role": get_user_role(other),
                "last_message": last_msg["message"][:50] if last_msg else "No messages",
                "last_time": last_msg["timestamp"] if last_msg else room["created_at"],
                "unread": unread
            })
    
    conversations.sort(key=lambda x: x["last_time"], reverse=True)
    return conversations

def get_chat_messages(room_id, username):
    """Get messages for a room and mark as read"""
    messages = CHAT_MESSAGES.get(room_id, [])
    for msg in messages:
        if msg["receiver"] == username and not msg.get("read", False):
            msg["read"] = True
    save_chat_data()
    return messages

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
# 🔌 SOCKETIO CHAT EVENTS
# ==================================================

@socketio.on('connect')
def handle_connect():
    print(f"🔌 Client connected: {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    # Remove user from online list
    username_to_remove = None
    for user, sid in ONLINE_USERS.items():
        if sid == request.sid:
            username_to_remove = user
            break
    if username_to_remove:
        del ONLINE_USERS[username_to_remove]
        # Broadcast online status
        emit('online_users', get_available_staff(), broadcast=True)
        emit('user_offline', {'username': username_to_remove}, broadcast=True)
        print(f"🔌 User offline: {username_to_remove}")

@socketio.on('register_user')
def handle_register_user(data):
    username = data.get('username')
    password = data.get('password')
    
    # Verify credentials
    license_key, license_type, license_data = find_license_by_credentials(username, password)
    
    if license_key:
        ONLINE_USERS[username] = request.sid
        user_role = get_user_role(username)
        emit('registration_success', {
            'username': username,
            'role': user_role,
            'staff_list': get_available_staff(),
            'conversations': get_user_chats(username)
        })
        # Broadcast online status to staff
        emit('online_users', get_available_staff(), broadcast=True)
        emit('user_online', {'username': username, 'role': user_role}, broadcast=True)
        print(f"✅ User registered for chat: {username}")
    else:
        emit('registration_error', {'error': 'Invalid credentials'})

@socketio.on('join_chat')
def handle_join_chat(data):
    username = data.get('username')
    other_user = data.get('other_user')
    
    if username and other_user:
        room_id = get_chat_room(username, other_user)
        join_room(room_id)
        messages = get_chat_messages(room_id, username)
        emit('chat_history', {'messages': messages, 'room_id': room_id})
        print(f"📱 {username} joined chat with {other_user}")

@socketio.on('send_message')
def handle_send_message(data):
    sender = data.get('sender')
    receiver = data.get('receiver')
    message = data.get('message', '').strip()
    
    if not message:
        return
    
    room_id = get_chat_room(sender, receiver)
    msg_data = save_chat_message(room_id, sender, receiver, message)
    
    # Emit to room
    emit('new_message', msg_data, room=room_id)
    
    # Check if receiver is online and send notification
    receiver_sid = ONLINE_USERS.get(receiver)
    if receiver_sid:
        emit('chat_notification', {
            'from': sender,
            'message': message[:50],
            'room_id': room_id
        }, room=receiver_sid)
    
    # Update conversation list for both users
    for user in [sender, receiver]:
        user_sid = ONLINE_USERS.get(user)
        if user_sid:
            emit('update_conversations', {
                'conversations': get_user_chats(user)
            }, room=user_sid)

@socketio.on('typing')
def handle_typing(data):
    sender = data.get('sender')
    receiver = data.get('receiver')
    is_typing = data.get('is_typing', False)
    
    receiver_sid = ONLINE_USERS.get(receiver)
    if receiver_sid:
        emit('user_typing', {
            'from': sender,
            'is_typing': is_typing
        }, room=receiver_sid)

@socketio.on('mark_read')
def handle_mark_read(data):
    username = data.get('username')
    other_user = data.get('other_user')
    
    if username and other_user:
        room_id = get_chat_room(username, other_user)
        messages = CHAT_MESSAGES.get(room_id, [])
        for msg in messages:
            if msg["receiver"] == username and not msg.get("read", False):
                msg["read"] = True
        save_chat_data()
        
        # Update unread count for user
        user_sid = ONLINE_USERS.get(username)
        if user_sid:
            emit('update_conversations', {
                'conversations': get_user_chats(username)
            }, room=user_sid)

# ==================================================
# 🎨 CHAT WIDGET HTML (to be embedded)
# ==================================================
CHAT_WIDGET_HTML = """
<div id="chatWidget" style="position: fixed; bottom: 20px; right: 20px; z-index: 10000; font-family: 'Segoe UI', Arial, sans-serif;">
    <!-- Chat Button -->
    <div id="chatButton" onclick="toggleChat()" style="background: linear-gradient(135deg, #7C3AED, #6D28D9); width: 60px; height: 60px; border-radius: 50%; display: flex; align-items: center; justify-content: center; cursor: pointer; box-shadow: 0 4px 15px rgba(0,0,0,0.3); transition: transform 0.3s;">
        <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
        </svg>
        <span id="chatBadge" style="position: absolute; top: -5px; right: -5px; background: #EF4444; color: white; border-radius: 50%; padding: 2px 6px; font-size: 10px; font-weight: bold; display: none;">0</span>
    </div>
    
    <!-- Chat Window -->
    <div id="chatWindow" style="display: none; position: fixed; bottom: 90px; right: 20px; width: 380px; height: 550px; background: #1a1a2e; border-radius: 15px; box-shadow: 0 10px 40px rgba(0,0,0,0.4); overflow: hidden; flex-direction: column;">
        <!-- Header -->
        <div style="background: linear-gradient(135deg, #7C3AED, #6D28D9); padding: 15px; display: flex; justify-content: space-between; align-items: center;">
            <div>
                <h3 style="color: white; margin: 0;">💬 Live Support</h3>
                <p style="color: rgba(255,255,255,0.8); margin: 0; font-size: 12px;">Chat with our team</p>
            </div>
            <div>
                <button onclick="minimizeChat()" style="background: none; border: none; color: white; cursor: pointer; margin-right: 10px;">─</button>
                <button onclick="closeChat()" style="background: none; border: none; color: white; cursor: pointer;">✕</button>
            </div>
        </div>
        
        <!-- Login Section -->
        <div id="chatLoginSection" style="padding: 20px;">
            <p style="color: #aaa; margin-bottom: 15px;">Login with your license credentials to start chatting:</p>
            <input type="text" id="chatUsername" placeholder="Username" style="width: 100%; padding: 12px; margin: 8px 0; border: 1px solid rgba(255,255,255,0.2); border-radius: 8px; background: rgba(0,0,0,0.3); color: white;">
            <input type="password" id="chatPassword" placeholder="Password" style="width: 100%; padding: 12px; margin: 8px 0; border: 1px solid rgba(255,255,255,0.2); border-radius: 8px; background: rgba(0,0,0,0.3); color: white;">
            <button onclick="chatLogin()" style="width: 100%; padding: 12px; background: #7C3AED; border: none; border-radius: 8px; color: white; font-weight: bold; cursor: pointer; margin-top: 10px;">Start Chat</button>
            <div id="chatLoginError" style="color: #EF4444; font-size: 12px; margin-top: 10px; display: none;"></div>
        </div>
        
        <!-- Chat Interface -->
        <div id="chatInterface" style="display: none; flex: 1; flex-direction: column; height: 100%;">
            <!-- Staff List -->
            <div id="staffListSection" style="padding: 15px; border-bottom: 1px solid rgba(255,255,255,0.1);">
                <h4 style="color: white; margin: 0 0 10px 0;">👥 Choose who to contact:</h4>
                <div id="staffList" style="display: flex; gap: 10px; overflow-x: auto;"></div>
                <div id="currentChatInfo" style="margin-top: 10px; padding: 8px; background: rgba(124,58,237,0.2); border-radius: 8px; display: none;">
                    <span style="color: #aaa;">Chatting with:</span>
                    <strong id="chattingWith" style="color: #7C3AED;"></strong>
                    <span id="typingIndicator" style="color: #aaa; font-size: 11px; margin-left: 10px;"></span>
                </div>
            </div>
            
            <!-- Messages Area -->
            <div id="messagesArea" style="flex: 1; overflow-y: auto; padding: 15px; min-height: 250px;">
                <div style="text-align: center; color: #aaa; padding: 20px;">Select a staff member to start chatting</div>
            </div>
            
            <!-- Message Input -->
            <div id="messageInputSection" style="padding: 15px; border-top: 1px solid rgba(255,255,255,0.1); display: none;">
                <div style="display: flex; gap: 10px;">
                    <input type="text" id="messageInput" placeholder="Type your message..." style="flex: 1; padding: 10px; border: 1px solid rgba(255,255,255,0.2); border-radius: 8px; background: rgba(0,0,0,0.3); color: white;">
                    <button onclick="sendMessage()" style="padding: 10px 20px; background: #7C3AED; border: none; border-radius: 8px; color: white; cursor: pointer;">Send</button>
                </div>
            </div>
        </div>
    </div>
</div>

<script>
    let socket = null;
    let currentUser = null;
    let currentChatWith = null;
    let currentRoomId = null;
    let typingTimeout = null;
    
    function toggleChat() {
        const window = document.getElementById('chatWindow');
        if (window.style.display === 'none' || window.style.display === '') {
            window.style.display = 'flex';
            if (socket && currentUser) {
                loadConversations();
            }
        } else {
            window.style.display = 'none';
        }
    }
    
    function minimizeChat() {
        document.getElementById('chatWindow').style.display = 'none';
    }
    
    function closeChat() {
        document.getElementById('chatWindow').style.display = 'none';
        if (socket) {
            socket.disconnect();
            socket = null;
        }
        currentUser = null;
    }
    
    function chatLogin() {
        const username = document.getElementById('chatUsername').value;
        const password = document.getElementById('chatPassword').value;
        
        if (!username || !password) {
            showChatError('Please enter username and password');
            return;
        }
        
        // Connect WebSocket
        socket = io();
        
        socket.on('connect', function() {
            socket.emit('register_user', {username: username, password: password});
        });
        
        socket.on('registration_success', function(data) {
            currentUser = data.username;
            document.getElementById('chatLoginSection').style.display = 'none';
            document.getElementById('chatInterface').style.display = 'flex';
            document.getElementById('staffListSection').style.display = 'block';
            
            // Display staff list
            displayStaffList(data.staff_list);
            
            // Load conversations
            if (data.conversations && data.conversations.length > 0) {
                loadConversations();
            }
        });
        
        socket.on('registration_error', function(data) {
            showChatError(data.error);
        });
        
        socket.on('new_message', function(data) {
            if (currentChatWith === data.sender) {
                appendMessage(data.sender, data.message, data.timestamp, false);
                markMessagesAsRead();
            } else {
                updateChatBadge();
                // Show notification
                if (document.getElementById('chatWindow').style.display !== 'flex') {
                    document.getElementById('chatButton').style.animation = 'pulse 1s infinite';
                }
            }
            loadConversations();
        });
        
        socket.on('chat_history', function(data) {
            document.getElementById('messagesArea').innerHTML = '';
            data.messages.forEach(function(msg) {
                appendMessage(msg.sender, msg.message, msg.timestamp, msg.sender !== currentUser);
            });
            scrollToBottom();
        });
        
        socket.on('update_conversations', function(data) {
            // Update conversations in background
        });
        
        socket.on('user_typing', function(data) {
            if (data.from === currentChatWith) {
                const indicator = document.getElementById('typingIndicator');
                if (data.is_typing) {
                    indicator.innerHTML = 'typing...';
                } else {
                    indicator.innerHTML = '';
                }
            }
        });
        
        socket.on('online_users', function(staffList) {
            displayStaffList(staffList);
        });
        
        socket.on('user_online', function(data) {
            if (data.username === currentChatWith) {
                appendSystemMessage(`${data.username} is now online`);
            }
            loadConversations();
        });
        
        socket.on('user_offline', function(data) {
            if (data.username === currentChatWith) {
                appendSystemMessage(`${data.username} went offline`);
            }
            loadConversations();
        });
    }
    
    function displayStaffList(staffList) {
        const container = document.getElementById('staffList');
        container.innerHTML = '';
        
        staffList.forEach(function(staff) {
            const btn = document.createElement('button');
            btn.className = 'staff-btn';
            btn.style.cssText = 'padding: 10px; background: rgba(124,58,237,0.2); border: 1px solid #7C3AED; border-radius: 8px; color: white; cursor: pointer; transition: all 0.3s; min-width: 80px;';
            btn.innerHTML = `${staff.avatar} ${staff.username}${staff.online ? ' 🟢' : ' ⚫'}`;
            btn.onclick = function() { startChat(staff.username); };
            container.appendChild(btn);
        });
    }
    
    function startChat(otherUser) {
        currentChatWith = otherUser;
        document.getElementById('chattingWith').innerHTML = otherUser;
        document.getElementById('currentChatInfo').style.display = 'block';
        document.getElementById('messageInputSection').style.display = 'flex';
        
        socket.emit('join_chat', {username: currentUser, other_user: otherUser});
    }
    
    function sendMessage() {
        const input = document.getElementById('messageInput');
        const message = input.value.trim();
        
        if (!message || !currentChatWith) return;
        
        socket.emit('send_message', {
            sender: currentUser,
            receiver: currentChatWith,
            message: message
        });
        
        input.value = '';
        scrollToBottom();
        
        // Stop typing indicator
        if (typingTimeout) clearTimeout(typingTimeout);
        socket.emit('typing', {sender: currentUser, receiver: currentChatWith, is_typing: false});
    }
    
    function appendMessage(sender, message, timestamp, isOwn) {
        const area = document.getElementById('messagesArea');
        const msgDiv = document.createElement('div');
        msgDiv.style.cssText = `margin-bottom: 12px; display: flex; justify-content: ${isOwn ? 'flex-end' : 'flex-start'};`;
        
        const bubble = document.createElement('div');
        bubble.style.cssText = `max-width: 70%; padding: 10px 15px; border-radius: 15px; background: ${isOwn ? '#7C3AED' : 'rgba(255,255,255,0.1)'}; color: white;`;
        
        const nameSpan = document.createElement('div');
        nameSpan.style.cssText = 'font-size: 10px; opacity: 0.7; margin-bottom: 4px;';
        nameSpan.innerHTML = isOwn ? 'You' : sender;
        
        const msgSpan = document.createElement('div');
        msgSpan.innerHTML = message;
        
        const timeSpan = document.createElement('div');
        timeSpan.style.cssText = 'font-size: 9px; opacity: 0.5; margin-top: 4px; text-align: right;';
        timeSpan.innerHTML = new Date(timestamp).toLocaleTimeString();
        
        bubble.appendChild(nameSpan);
        bubble.appendChild(msgSpan);
        bubble.appendChild(timeSpan);
        msgDiv.appendChild(bubble);
        area.appendChild(msgDiv);
        scrollToBottom();
    }
    
    function appendSystemMessage(message) {
        const area = document.getElementById('messagesArea');
        const msgDiv = document.createElement('div');
        msgDiv.style.cssText = 'text-align: center; margin: 10px;';
        msgDiv.innerHTML = `<span style="background: rgba(255,255,255,0.1); padding: 5px 10px; border-radius: 10px; font-size: 11px; color: #aaa;">${message}</span>`;
        area.appendChild(msgDiv);
        scrollToBottom();
    }
    
    function scrollToBottom() {
        const area = document.getElementById('messagesArea');
        area.scrollTop = area.scrollHeight;
    }
    
    function showChatError(msg) {
        const errorDiv = document.getElementById('chatLoginError');
        errorDiv.innerHTML = msg;
        errorDiv.style.display = 'block';
        setTimeout(function() { errorDiv.style.display = 'none'; }, 3000);
    }
    
    function updateChatBadge() {
        // This would need an API call to get unread count
        const badge = document.getElementById('chatBadge');
        badge.style.display = 'inline-block';
    }
    
    function loadConversations() {
        // Load existing conversations from server
        socket.emit('get_conversations', {username: currentUser});
    }
    
    function markMessagesAsRead() {
        if (currentChatWith) {
            socket.emit('mark_read', {username: currentUser, other_user: currentChatWith});
        }
    }
    
    // Typing indicator
    document.addEventListener('DOMContentLoaded', function() {
        const input = document.getElementById('messageInput');
        if (input) {
            let typingTimer;
            input.addEventListener('input', function() {
                if (socket && currentChatWith) {
                    clearTimeout(typingTimer);
                    socket.emit('typing', {sender: currentUser, receiver: currentChatWith, is_typing: true});
                    typingTimer = setTimeout(function() {
                        socket.emit('typing', {sender: currentUser, receiver: currentChatWith, is_typing: false});
                    }, 1000);
                }
            });
        }
    });
    
    // CSS animation
    const style = document.createElement('style');
    style.innerHTML = `@keyframes pulse { 0% { transform: scale(1); } 50% { transform: scale(1.1); } 100% { transform: scale(1); } }`;
    document.head.appendChild(style);
</script>
"""

# ==================================================
# 🎨 USER PORTAL HTML (With Chat)
# ==================================================
USER_PORTAL_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>JEPFX License Portal</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://cdn.socket.io/4.5.0/socket.io.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Segoe UI', Arial, sans-serif; }
        body { background: linear-gradient(135deg, #0f0c29, #302b63, #24243e); min-height: 100vh; padding: 20px; }
        .container { max-width: 800px; margin: 0 auto; }
        .header { text-align: center; margin-bottom: 30px; }
        .header h1 { color: #7C3AED; font-size: 32px; }
        .header p { color: #aaa; }
        .card { background: rgba(255,255,255,0.1); backdrop-filter: blur(10px); border-radius: 15px; padding: 25px; margin-bottom: 20px; }
        .card h2 { color: #7C3AED; margin-bottom: 20px; border-bottom: 1px solid rgba(255,255,255,0.2); padding-bottom: 10px; }
        input, select, textarea { width: 100%; padding: 12px; margin: 10px 0; border: 1px solid rgba(255,255,255,0.2); border-radius: 8px; background: rgba(0,0,0,0.3); color: white; }
        button { background: #7C3AED; color: white; padding: 12px 25px; border: none; border-radius: 8px; cursor: pointer; font-size: 16px; font-weight: bold; }
        button:hover { background: #6D28D9; transform: translateY(-2px); }
        .status-box { background: rgba(0,0,0,0.5); border-radius: 10px; padding: 15px; margin: 15px 0; border-left: 3px solid #7C3AED; }
        .status-active { border-left-color: #10B981; }
        .status-expired { border-left-color: #EF4444; }
        .status-warning { border-left-color: #F59E0B; }
        .info-row { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.1); }
        .info-label { color: #aaa; }
        .info-value { color: white; font-weight: bold; }
        .contact-buttons { display: flex; gap: 10px; margin-top: 20px; }
        .contact-btn { flex: 1; text-align: center; text-decoration: none; padding: 12px; border-radius: 8px; color: white; font-weight: bold; }
        .telegram-btn { background: #0088cc; }
        .chat-btn { background: #7C3AED; }
        .request-form { display: none; margin-top: 20px; padding-top: 20px; border-top: 1px solid rgba(255,255,255,0.2); }
        .request-form.show { display: block; }
        .alert-success { background: rgba(16,185,129,0.2); border: 1px solid #10B981; color: #10B981; padding: 12px; border-radius: 8px; margin: 10px 0; }
        .alert-error { background: rgba(239,68,68,0.2); border: 1px solid #EF4444; color: #EF4444; padding: 12px; border-radius: 8px; margin: 10px 0; }
        .alert-info { background: rgba(59,130,246,0.2); border: 1px solid #3B82F6; color: #3B82F6; padding: 12px; border-radius: 8px; margin: 10px 0; }
        .badge { display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: bold; }
        .badge-active { background: #10B981; color: white; }
        .badge-expired { background: #EF4444; color: white; }
        .badge-warning { background: #F59E0B; color: white; }
        .hidden { display: none; }
        .tab-btn { background: rgba(255,255,255,0.1); padding: 10px 20px; border: none; border-radius: 8px; color: white; cursor: pointer; margin: 5px; }
        .tab-btn.active { background: #7C3AED; }
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>🔑 JEPFX License Portal</h1>
        <p>Register for a license, check status, or request support</p>
    </div>
    
    <div style="display: flex; gap: 10px; margin-bottom: 20px;">
        <button class="tab-btn active" onclick="showTab('login')">🔐 Login</button>
        <button class="tab-btn" onclick="showTab('register')">📝 Register</button>
    </div>
    
    <div id="loginSection" class="card">
        <h2>🔐 License Login</h2>
        <p>Already have a license? Login to check status.</p>
        <input type="text" id="loginUsername" placeholder="Username">
        <input type="password" id="loginPassword" placeholder="Password">
        <button onclick="checkLicense()">CHECK LICENSE STATUS</button>
        <div id="loginError" class="alert-error" style="display: none;"></div>
    </div>
    
    <div id="registerSection" class="card hidden">
        <h2>📝 Register for License</h2>
        <p>Create an account and request a license. Admin will approve and send your credentials.</p>
        <input type="text" id="regUsername" placeholder="Desired Username *">
        <input type="password" id="regPassword" placeholder="Desired Password *">
        <input type="text" id="regTelegram" placeholder="Telegram Username (e.g., @username) *">
        <input type="text" id="regFacebook" placeholder="Facebook Profile (optional)">
        <textarea id="regReason" rows="3" placeholder="Why do you need a license? (optional)"></textarea>
        <button onclick="registerUser()">SUBMIT REGISTRATION</button>
        <div id="registerResult" class="alert-info" style="display: none;"></div>
    </div>
    
    <div id="statusSection" class="card hidden">
        <div id="statusContent"></div>
        <div id="requestForm" class="request-form">
            <h3>📨 Request Extension / Reactivation</h3>
            <select id="requestType">
                <option value="extension">Extension (Add more days)</option>
                <option value="reactivation">Reactivation (Reset HWID)</option>
                <option value="other">Other Request</option>
            </select>
            <input type="number" id="requestDays" placeholder="Days to add (if extension)" value="7">
            <textarea id="requestMessage" rows="3" placeholder="Describe your request..."></textarea>
            <button onclick="submitRequest()">SUBMIT REQUEST</button>
            <div id="requestResult" class="alert-info" style="display: none;"></div>
        </div>
        <div class="contact-buttons">
            <a href="https://t.me/JEPFX_0" target="_blank" class="contact-btn telegram-btn">📱 Contact Admin on Telegram</a>
            <button class="contact-btn chat-btn" onclick="openChatWidget()">💬 Live Chat Support</button>
        </div>
    </div>
</div>

<!-- Include Chat Widget -->
""" + CHAT_WIDGET_HTML + """

<script>
    let currentLicenseKey = null;
    let currentUsername = null;
    
    function showTab(tab) {
        document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
        event.target.classList.add('active');
        
        if(tab === 'login') {
            document.getElementById('loginSection').classList.remove('hidden');
            document.getElementById('registerSection').classList.add('hidden');
            document.getElementById('statusSection').classList.add('hidden');
        } else {
            document.getElementById('loginSection').classList.add('hidden');
            document.getElementById('registerSection').classList.remove('hidden');
            document.getElementById('statusSection').classList.add('hidden');
        }
    }
    
    function openChatWidget() {
        if (currentUsername) {
            document.getElementById('chatUsername').value = currentUsername;
            document.getElementById('chatPassword').value = document.getElementById('loginPassword').value;
        }
        toggleChat();
    }
    
    async function registerUser() {
        const username = document.getElementById('regUsername').value;
        const password = document.getElementById('regPassword').value;
        const telegram = document.getElementById('regTelegram').value;
        const facebook = document.getElementById('regFacebook').value;
        const reason = document.getElementById('regReason').value;
        
        if(!username || !password || !telegram) {
            alert('Please fill in all required fields (*)');
            return;
        }
        
        const btn = event.target;
        btn.disabled = true;
        btn.innerHTML = 'Submitting...';
        
        try {
            const res = await fetch('/api/user/register', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({username, password, telegram, facebook, reason})
            });
            const data = await res.json();
            
            const resultDiv = document.getElementById('registerResult');
            if(data.success) {
                resultDiv.className = 'alert-success';
                resultDiv.innerHTML = '✅ Registration submitted! Admin will review and contact you on Telegram with your license.';
                resultDiv.style.display = 'block';
                document.getElementById('regUsername').value = '';
                document.getElementById('regPassword').value = '';
                document.getElementById('regTelegram').value = '';
                document.getElementById('regFacebook').value = '';
                document.getElementById('regReason').value = '';
                setTimeout(() => { showTab('login'); }, 3000);
            } else {
                resultDiv.className = 'alert-error';
                resultDiv.innerHTML = '❌ Error: ' + data.error;
                resultDiv.style.display = 'block';
            }
        } catch(error) {
            document.getElementById('registerResult').className = 'alert-error';
            document.getElementById('registerResult').innerHTML = '❌ Connection error. Please try again.';
            document.getElementById('registerResult').style.display = 'block';
        }
        
        btn.disabled = false;
        btn.innerHTML = 'SUBMIT REGISTRATION';
    }
    
    async function checkLicense() {
        const username = document.getElementById('loginUsername').value;
        const password = document.getElementById('loginPassword').value;
        
        if(!username || !password) {
            showError('Please enter username and password');
            return;
        }
        
        const btn = event.target;
        btn.disabled = true;
        btn.innerHTML = 'Checking...';
        
        try {
            const res = await fetch('/api/user/check-license', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({username: username, password: password})
            });
            const data = await res.json();
            
            if(data.success) {
                currentLicenseKey = data.license_key;
                currentUsername = username;
                displayLicenseStatus(data);
                document.getElementById('loginSection').classList.add('hidden');
                document.getElementById('registerSection').classList.add('hidden');
                document.getElementById('statusSection').classList.remove('hidden');
            } else {
                showError(data.error || 'Invalid credentials or license not found');
            }
        } catch (error) {
            showError('Connection error. Please try again.');
        }
        
        btn.disabled = false;
        btn.innerHTML = 'CHECK LICENSE STATUS';
    }
    
    function displayLicenseStatus(data) {
        const statusClass = data.is_expired ? 'status-expired' : (data.days_left < 3 ? 'status-warning' : 'status-active');
        const badgeClass = data.is_expired ? 'badge-expired' : (data.days_left < 3 ? 'badge-warning' : 'badge-active');
        const statusText = data.is_expired ? 'EXPIRED' : (data.days_left < 3 ? 'EXPIRING SOON' : 'ACTIVE');
        
        let hwidHtml = '';
        if(data.hwids && data.hwids.length > 0) {
            hwidHtml = '<div class="info-row"><span class="info-label">🖥️ Activated Devices:</span><span class="info-value">' + data.hwids.length + ' device(s)</span></div>';
        }
        
        const html = `
            <div class="status-box ${statusClass}">
                <div class="info-row"><span class="info-label">🔑 License Key:</span><span class="info-value"><code>${data.license_key}</code></span></div>
                <div class="info-row"><span class="info-label">👤 Username:</span><span class="info-value">${data.username}</span></div>
                <div class="info-row"><span class="info-label">📋 License Type:</span><span class="info-value">${data.license_type}</span></div>
                <div class="info-row"><span class="info-label">📅 Expires:</span><span class="info-value">${data.expires_at || 'NEVER'}</span></div>
                <div class="info-row"><span class="info-label">⏰ Status:</span><span class="info-value"><span class="badge ${badgeClass}">${statusText}</span></span></div>
                ${data.days_left !== null ? `<div class="info-row"><span class="info-label">📆 Days Left:</span><span class="info-value">${data.days_left} days</span></div>` : ''}
                ${data.usage_count !== undefined ? `<div class="info-row"><span class="info-label">📊 Total API Calls:</span><span class="info-value">${data.usage_count}</span></div>` : ''}
                ${hwidHtml}
                ${data.created_at ? `<div class="info-row"><span class="info-label">📅 Created:</span><span class="info-value">${new Date(data.created_at).toLocaleString()}</span></div>` : ''}
                ${data.last_used ? `<div class="info-row"><span class="info-label">🕐 Last Used:</span><span class="info-value">${new Date(data.last_used).toLocaleString()}</span></div>` : ''}
            </div>
            ${data.is_expired ? '<div class="alert-error" style="margin:10px 0;">⚠️ Your license has expired. Submit a request for reactivation.</div>' : ''}
            ${!data.is_expired && data.days_left < 7 ? '<div class="alert-info" style="margin:10px 0;">⚠️ Your license is expiring soon! Submit a request to extend.</div>' : ''}
        `;
        
        document.getElementById('statusContent').innerHTML = html;
        document.getElementById('requestForm').classList.add('show');
    }
    
    async function submitRequest() {
        const requestType = document.getElementById('requestType').value;
        const requestDays = document.getElementById('requestDays').value;
        const requestMessage = document.getElementById('requestMessage').value;
        
        if(!requestMessage) {
            alert('Please describe your request');
            return;
        }
        
        const res = await fetch('/api/user/submit-request', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                license_key: currentLicenseKey,
                username: currentUsername,
                request_type: requestType,
                days_requested: parseInt(requestDays) || 0,
                message: requestMessage,
                contact: ''
            })
        });
        
        const data = await res.json();
        const resultDiv = document.getElementById('requestResult');
        
        if(data.success) {
            resultDiv.className = 'alert-success';
            resultDiv.innerHTML = '✅ Request submitted successfully! Admin will review and contact you soon.';
            resultDiv.style.display = 'block';
            document.getElementById('requestMessage').value = '';
            setTimeout(() => { resultDiv.style.display = 'none'; }, 5000);
        } else {
            resultDiv.className = 'alert-error';
            resultDiv.innerHTML = '❌ Error: ' + data.error;
            resultDiv.style.display = 'block';
        }
    }
    
    function showError(msg) {
        const errorDiv = document.getElementById('loginError');
        errorDiv.innerHTML = msg;
        errorDiv.style.display = 'block';
        setTimeout(() => { errorDiv.style.display = 'none'; }, 5000);
    }
    
    function toggleChat() {
        const window = document.getElementById('chatWindow');
        if (window.style.display === 'none' || window.style.display === '') {
            window.style.display = 'flex';
            if (currentUsername) {
                document.getElementById('chatUsername').value = currentUsername;
                document.getElementById('chatPassword').value = document.getElementById('loginPassword').value;
            }
        } else {
            window.style.display = 'none';
        }
    }
    
    function closeChat() {
        document.getElementById('chatWindow').style.display = 'none';
    }
</script>
</body>
</html>
"""

# ==================================================
# 🎨 ADMIN PANEL HTML (With Chat)
# ==================================================
ADMIN_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>JEPFX ADMIN PANEL</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://cdn.socket.io/4.5.0/socket.io.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Segoe UI', Arial, sans-serif; }
        body { background: linear-gradient(135deg, #0f0c29, #302b63, #24243e); min-height: 100vh; padding: 20px; }
        .container { max-width: 1400px; margin: 0 auto; }
        .login-box { max-width: 400px; margin: 100px auto; background: rgba(255,255,255,0.1); backdrop-filter: blur(10px); padding: 30px; border-radius: 15px; text-align: center; }
        .login-box input { width: 100%; padding: 12px; margin: 10px 0; border: none; border-radius: 8px; background: rgba(255,255,255,0.2); color: white; }
        .login-box button { background: #7C3AED; color: white; padding: 12px 30px; border: none; border-radius: 8px; cursor: pointer; }
        .panel { display: none; }
        .header { background: rgba(255,255,255,0.1); border-radius: 15px; padding: 20px; margin-bottom: 20px; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin-bottom: 20px; }
        .stat-card { background: rgba(124,58,237,0.2); padding: 15px; border-radius: 10px; text-align: center; cursor: pointer; }
        .stat-number { font-size: 28px; font-weight: bold; color: #7C3AED; }
        .tabs { display: flex; gap: 5px; flex-wrap: wrap; margin-bottom: 20px; }
        .tab { background: rgba(255,255,255,0.1); padding: 10px 18px; border-radius: 8px; cursor: pointer; border: none; color: white; font-size: 14px; }
        .tab.active { background: #7C3AED; }
        .content { display: none; background: rgba(255,255,255,0.05); border-radius: 15px; padding: 25px; }
        .content.active { display: block; }
        input, select, textarea { width: 100%; padding: 12px; margin: 10px 0; border: 1px solid rgba(255,255,255,0.2); border-radius: 8px; background: rgba(0,0,0,0.3); color: white; }
        button { background: #7C3AED; color: white; padding: 10px 20px; border: none; border-radius: 8px; cursor: pointer; margin: 5px; }
        .btn-danger { background: #DC2626; }
        .btn-success { background: #10B981; }
        .btn-warning { background: #F59E0B; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; display: block; overflow-x: auto; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid rgba(255,255,255,0.1); }
        th { background: rgba(124,58,237,0.3); }
        tr:hover { background: rgba(255,255,255,0.05); }
        .result-box { background: rgba(0,0,0,0.5); padding: 20px; border-radius: 10px; margin-top: 20px; border-left: 3px solid #7C3AED; }
        .modal { display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); }
        .modal-content { background: #1a1a2e; margin: 5% auto; padding: 25px; border-radius: 15px; width: 90%; max-width: 600px; }
        .close { float: right; font-size: 28px; cursor: pointer; }
        .master-only { background: rgba(239,68,68,0.2); border-left: 3px solid #EF4444; padding: 10px; margin: 10px 0; border-radius: 5px; }
        .copy-btn { background: #3B82F6; padding: 2px 8px; border-radius: 5px; font-size: 11px; margin-left: 5px; cursor: pointer; display: inline-block; }
        .badge { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 11px; }
        .badge-pending { background: #F59E0B; }
        .badge-approved { background: #10B981; }
        .badge-rejected { background: #EF4444; }
        
        /* Chat Panel Styles */
        .chat-panel { position: fixed; bottom: 20px; right: 20px; width: 350px; height: 500px; background: #1a1a2e; border-radius: 15px; box-shadow: 0 10px 40px rgba(0,0,0,0.4); display: none; flex-direction: column; z-index: 1000; }
        .chat-panel.open { display: flex; }
        .chat-header { background: linear-gradient(135deg, #7C3AED, #6D28D9); padding: 15px; border-radius: 15px 15px 0 0; display: flex; justify-content: space-between; align-items: center; }
        .chat-messages { flex: 1; overflow-y: auto; padding: 15px; }
        .chat-input-area { padding: 15px; border-top: 1px solid rgba(255,255,255,0.1); display: flex; gap: 10px; }
        .chat-input { flex: 1; padding: 10px; border: 1px solid rgba(255,255,255,0.2); border-radius: 8px; background: rgba(0,0,0,0.3); color: white; }
        .chat-message { margin-bottom: 12px; display: flex; justify-content: flex-start; }
        .chat-message.own { justify-content: flex-end; }
        .chat-bubble { max-width: 70%; padding: 10px 15px; border-radius: 15px; background: rgba(255,255,255,0.1); color: white; }
        .chat-bubble.own { background: #7C3AED; }
        .chat-user-list { max-height: 200px; overflow-y: auto; border-bottom: 1px solid rgba(255,255,255,0.1); padding: 10px; }
        .chat-user { padding: 8px; margin: 4px 0; border-radius: 8px; cursor: pointer; display: flex; align-items: center; gap: 10px; }
        .chat-user:hover { background: rgba(124,58,237,0.3); }
        .chat-user.online { border-left: 3px solid #10B981; }
        .chat-user.offline { opacity: 0.6; }
        .chat-badge { position: absolute; top: -5px; right: -5px; background: #EF4444; color: white; border-radius: 50%; padding: 2px 6px; font-size: 10px; }
        .typing-indicator { font-size: 11px; color: #aaa; margin-top: 5px; }
    </style>
</head>
<body>
<div class="container">
    <div id="loginScreen" class="login-box">
        <h2>🔒 JEPFX ADMIN LOGIN</h2>
        <input type="text" id="loginUsername" placeholder="Username">
        <input type="password" id="loginPassword" placeholder="Password">
        <button onclick="login()">LOGIN</button>
        <p id="loginError" style="color: #EF4444; display: none; margin-top: 10px;">Invalid credentials!</p>
    </div>
    
    <div id="mainPanel" class="panel">
        <div class="header">
            <h1>⚡ JEPFX ADMIN PANEL</h1>
            <p>Welcome, <span id="currentUser">-</span> | Role: <span id="currentRole">-</span> | Credits: <span id="currentCredits">0</span></p>
            <div id="roleInfo" class="result-box" style="margin-top: 10px; font-size: 14px;"></div>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card"><div class="stat-number" id="statTrials">0</div><div>My Trials</div></div>
            <div class="stat-card" id="statCustomCard"><div class="stat-number" id="statCustom">0</div><div>My Custom</div></div>
            <div class="stat-card" id="statPermanentCard" style="display: none;"><div class="stat-number" id="statPermanent">0</div><div>My Permanent</div></div>
            <div class="stat-card"><div class="stat-number" id="statRegistrations">0</div><div>Registrations</div></div>
            <div class="stat-card"><div class="stat-number" id="statRequests">0</div><div>Requests</div></div>
            <div class="stat-card" onclick="openChatPanel()"><div class="stat-number" id="chatUnread">0</div><div>Chat Messages</div></div>
        </div>
        
        <div class="tabs" id="tabsContainer">
            <button class="tab active" onclick="switchTab('generateTrial')">🎲 TRIAL</button>
            <button class="tab" id="customTab" onclick="switchTab('customActivation')">✨ CUSTOM</button>
            <button class="tab" id="permanentTab" style="display: none;" onclick="switchTab('permanentLicense')">🔑 PERMANENT</button>
            <button class="tab" onclick="switchTab('myLicenses')">📋 MY LICENSES</button>
            <button class="tab" onclick="switchTab('registrations')">📝 REGISTRATIONS</button>
            <button class="tab" onclick="switchTab('userRequests')">📨 REQUESTS</button>
            <button class="tab" onclick="switchTab('history')">📜 HISTORY</button>
            <button class="tab" id="adminTab" style="display: none;" onclick="switchTab('admins')">👨‍💼 MANAGE</button>
            <button class="tab" onclick="switchTab('changePassword')">🔐 PASSWORD</button>
            <button class="tab" onclick="switchTab('monitor')">📈 MONITOR</button>
            <button class="tab" onclick="openChatPanel()">💬 CHAT</button>
        </div>
        
        <!-- Generate Trial -->
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
            <div id="trialResult" class="result-box" style="display: none;"></div>
        </div>
        
        <!-- Custom Activation -->
        <div id="customActivation" class="content">
            <h2>✨ Custom Activation (Multi-PC)</h2>
            <input type="text" id="customUsername" placeholder="Username *">
            <input type="text" id="customPassword" placeholder="Password *">
            <input type="text" id="customLicense" placeholder="License Key *">
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
            <div id="customResult" class="result-box" style="display: none;"></div>
        </div>
        
        <!-- Permanent License -->
        <div id="permanentLicense" class="content">
            <h2>🔑 Permanent License (50 Credits)</h2>
            <input type="text" id="permLicenseKey" placeholder="License Key *">
            <input type="text" id="permUsername" placeholder="Username (optional)">
            <input type="text" id="permPassword" placeholder="Password (optional)">
            <button onclick="createPermanentLicense()">CREATE PERMANENT</button>
            <div id="permResult" class="result-box" style="display: none;"></div>
        </div>
        
        <!-- My Licenses -->
        <div id="myLicenses" class="content">
            <h2>📋 My Active Licenses</h2>
            <div style="margin-bottom: 10px;">
                <button onclick="showLicenseType('trials')">Trial</button>
                <button id="showCustomBtn" onclick="showLicenseType('custom')">Custom</button>
                <button id="showPermanentBtn" style="display: none;" onclick="showLicenseType('permanent')">Permanent</button>
            </div>
            <div id="myTrialsList"></div>
            <div id="myCustomList" style="display: none;"></div>
            <div id="myPermanentList" style="display: none;"></div>
        </div>
        
        <!-- Registrations Tab -->
        <div id="registrations" class="content">
            <h2>📝 User Registration Requests</h2>
            <button onclick="loadRegistrations()">REFRESH</button>
            <div id="registrationsList"></div>
        </div>
        
        <!-- User Requests Tab -->
        <div id="userRequests" class="content">
            <h2>📨 User Extension/Reactivation Requests</h2>
            <button onclick="loadUserRequests()">REFRESH</button>
            <div id="requestsList"></div>
        </div>
        
        <!-- History -->
        <div id="history" class="content">
            <h2>📜 License History</h2>
            <input type="text" id="historySearch" placeholder="Search..." onkeyup="filterHistory()" style="width: 100%;">
            <button onclick="loadHistory()">REFRESH</button>
            <button onclick="exportHistory()">📥 EXPORT CSV</button>
            <div id="historyList"></div>
        </div>
        
        <!-- Admins Management -->
        <div id="admins" class="content">
            <div class="master-only"><h2>👑 MASTER CONTROL</h2></div>
            <h3>➕ Add User</h3>
            <input type="text" id="newAdminUser" placeholder="Username">
            <input type="password" id="newAdminPass" placeholder="Password">
            <select id="newAdminRole">
                <option value="admin">Admin (Trial + Custom)</option>
                <option value="moderator">Moderator (Trial only)</option>
            </select>
            <input type="number" id="newAdminCredits" placeholder="Initial Credits" value="100" step="0.5">
            <button onclick="addAdmin()">ADD USER</button>
            
            <h3>🔄 Change Role</h3>
            <input type="text" id="roleChangeUser" placeholder="Username">
            <select id="newRoleSelect">
                <option value="admin">Admin (Trial + Custom)</option>
                <option value="moderator">Moderator (Trial only)</option>
            </select>
            <button onclick="changeUserRole()">CHANGE ROLE</button>
            
            <h3>🔑 Change Password</h3>
            <input type="text" id="targetUsername" placeholder="Username">
            <input type="password" id="newPasswordForTarget" placeholder="New Password">
            <button class="btn-warning" onclick="changeOtherPassword()">CHANGE PASSWORD</button>
            
            <h3>💰 Credits</h3>
            <input type="text" id="creditUsername" placeholder="Username">
            <input type="number" id="creditAmount" placeholder="Amount" step="0.5">
            <button onclick="manageCredits()">UPDATE CREDITS</button>
            
            <h3>📋 Admins</h3>
            <div id="adminsList"></div>
            <h3>📋 Moderators</h3>
            <div id="moderatorsList"></div>
        </div>
        
        <!-- Change Password -->
        <div id="changePassword" class="content">
            <h2>🔐 Change Your Password</h2>
            <input type="password" id="oldPassword" placeholder="Current Password">
            <input type="password" id="newPassword" placeholder="New Password">
            <input type="password" id="confirmPassword" placeholder="Confirm Password">
            <button onclick="changePassword()">UPDATE</button>
            <div id="passwordResult" class="result-box" style="display: none;"></div>
        </div>
        
        <!-- Monitor -->
        <div id="monitor" class="content">
            <h2>📈 Monitor</h2>
            <button onclick="loadMonitor()">REFRESH</button>
            <div id="monitorData" class="result-box"></div>
        </div>
    </div>
</div>

<!-- Chat Panel -->
<div id="chatPanel" class="chat-panel">
    <div class="chat-header">
        <span>💬 Live Support Chat</span>
        <div>
            <button onclick="minimizeChatPanel()" style="background: none; border: none; color: white; cursor: pointer; margin-right: 10px;">─</button>
            <button onclick="closeChatPanel()" style="background: none; border: none; color: white; cursor: pointer;">✕</button>
        </div>
    </div>
    <div id="chatUserList" class="chat-user-list">
        <div style="text-align: center; padding: 20px;">Loading users...</div>
    </div>
    <div id="chatMessagesArea" class="chat-messages" style="display: none;">
        <div id="chatMessages"></div>
        <div id="typingIndicator" class="typing-indicator"></div>
    </div>
    <div id="chatInputArea" class="chat-input-area" style="display: none;">
        <input type="text" id="chatInput" class="chat-input" placeholder="Type a message...">
        <button onclick="sendChatMessage()">Send</button>
    </div>
</div>

<div id="credsModal" class="modal">
    <div class="modal-content">
        <span class="close" onclick="closeModal()">&times;</span>
        <h2 id="modalTitle">Credentials</h2>
        <div id="modalBody"></div>
        <button onclick="copyAllCredentials()">📋 Copy All</button>
    </div>
</div>

<script>
    const API_URL = window.location.origin;
    let currentUser = null, currentRole = null, currentPassword = null;
    let chatSocket = null;
    let currentChatUser = null;
    let chatUnreadCount = 0;
    
    // ========== ADMIN FUNCTIONS ==========
    async function login() {
        const username = document.getElementById('loginUsername').value;
        const password = document.getElementById('loginPassword').value;
        currentPassword = password;
        
        const res = await fetch(API_URL + '/api/admin/login', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({username: username, password: password})
        });
        const data = await res.json();
        if(data.success) {
            currentUser = username; currentRole = data.role;
            document.getElementById('currentUser').textContent = username;
            document.getElementById('currentRole').textContent = data.role.toUpperCase();
            document.getElementById('currentCredits').textContent = data.credits || 'Unlimited';
            
            let roleInfo = '';
            if(data.role === 'master') {
                roleInfo = '👑 Master: Full access (Trial, Custom, Permanent)';
                document.getElementById('adminTab').style.display = 'block';
                document.getElementById('permanentTab').style.display = 'block';
                document.getElementById('showPermanentBtn').style.display = 'inline-block';
                document.getElementById('statPermanentCard').style.display = 'block';
            } else if(data.role === 'admin') {
                roleInfo = '⚙️ Admin: Trial + Custom licenses';
                document.getElementById('customTab').style.display = 'inline-block';
                document.getElementById('showCustomBtn').style.display = 'inline-block';
                document.getElementById('statCustomCard').style.display = 'block';
            } else {
                roleInfo = '🔧 Moderator: Trial licenses only';
                document.getElementById('customTab').style.display = 'none';
                document.getElementById('showCustomBtn').style.display = 'none';
                document.getElementById('statCustomCard').style.display = 'none';
            }
            document.getElementById('roleInfo').innerHTML = roleInfo;
            document.getElementById('loginScreen').style.display = 'none';
            document.getElementById('mainPanel').style.display = 'block';
            loadStats(); loadMyLicenses(); loadHistory(); loadRegistrations(); loadUserRequests();
            
            // Initialize chat
            initChatSocket();
        } else {
            document.getElementById('loginError').style.display = 'block';
        }
    }
    
    function initChatSocket() {
        chatSocket = io();
        
        chatSocket.on('connect', function() {
            chatSocket.emit('register_user', {username: currentUser, password: currentPassword});
        });
        
        chatSocket.on('registration_success', function(data) {
            loadChatUserList(data.staff_list);
        });
        
        chatSocket.on('new_message', function(data) {
            if (currentChatUser === data.sender) {
                appendChatMessage(data.sender, data.message, false);
                markChatMessagesRead();
            } else {
                chatUnreadCount++;
                updateChatBadge();
            }
            loadChatUserList(null);
        });
        
        chatSocket.on('chat_history', function(data) {
            document.getElementById('chatMessages').innerHTML = '';
            data.messages.forEach(function(msg) {
                appendChatMessage(msg.sender, msg.message, msg.sender !== currentUser);
            });
            scrollChatToBottom();
        });
        
        chatSocket.on('update_conversations', function(data) {
            // Update UI
        });
        
        chatSocket.on('user_typing', function(data) {
            if (data.from === currentChatUser) {
                const indicator = document.getElementById('typingIndicator');
                if (data.is_typing) {
                    indicator.innerHTML = data.from + ' is typing...';
                } else {
                    indicator.innerHTML = '';
                }
            }
        });
        
        chatSocket.on('online_users', function(staffList) {
            loadChatUserList(staffList);
        });
        
        chatSocket.on('user_online', function(data) {
            loadChatUserList(null);
            if (currentChatUser === data.username) {
                appendSystemMessage(data.username + ' is now online');
            }
        });
        
        chatSocket.on('user_offline', function(data) {
            loadChatUserList(null);
            if (currentChatUser === data.username) {
                appendSystemMessage(data.username + ' went offline');
            }
        });
    }
    
    function loadChatUserList(staffList) {
        if (!staffList) {
            chatSocket.emit('get_staff', {username: currentUser});
            return;
        }
        
        const container = document.getElementById('chatUserList');
        container.innerHTML = '<div style="padding: 10px; color: #aaa;">Staff Members:</div>';
        
        staffList.forEach(function(staff) {
            if (staff.username !== currentUser) {
                const userDiv = document.createElement('div');
                userDiv.className = 'chat-user ' + (staff.online ? 'online' : 'offline');
                userDiv.innerHTML = `
                    <span>${staff.avatar}</span>
                    <span style="flex:1">${staff.username}</span>
                    <span style="font-size:10px;">${staff.role}</span>
                    <span style="font-size:10px;">${staff.online ? '🟢' : '⚫'}</span>
                `;
                userDiv.onclick = function() { startChatWith(staff.username); };
                container.appendChild(userDiv);
            }
        });
    }
    
    function startChatWith(username) {
        currentChatUser = username;
        document.getElementById('chatUserList').style.display = 'none';
        document.getElementById('chatMessagesArea').style.display = 'flex';
        document.getElementById('chatInputArea').style.display = 'flex';
        document.getElementById('chatMessagesArea').style.flexDirection = 'column';
        
        chatSocket.emit('join_chat', {username: currentUser, other_user: username});
        
        // Mark messages as read
        setTimeout(markChatMessagesRead, 500);
    }
    
    function sendChatMessage() {
        const input = document.getElementById('chatInput');
        const message = input.value.trim();
        
        if (!message || !currentChatUser) return;
        
        chatSocket.emit('send_message', {
            sender: currentUser,
            receiver: currentChatUser,
            message: message
        });
        
        appendChatMessage(currentUser, message, true);
        input.value = '';
        scrollChatToBottom();
        
        // Stop typing indicator
        if (typingTimeout) clearTimeout(typingTimeout);
        chatSocket.emit('typing', {sender: currentUser, receiver: currentChatUser, is_typing: false});
    }
    
    function appendChatMessage(sender, message, isOwn) {
        const container = document.getElementById('chatMessages');
        const msgDiv = document.createElement('div');
        msgDiv.className = 'chat-message ' + (isOwn ? 'own' : '');
        
        const bubble = document.createElement('div');
        bubble.className = 'chat-bubble ' + (isOwn ? 'own' : '');
        
        if (!isOwn) {
            const nameSpan = document.createElement('div');
            nameSpan.style.cssText = 'font-size: 10px; opacity: 0.7; margin-bottom: 4px;';
            nameSpan.innerHTML = sender;
            bubble.appendChild(nameSpan);
        }
        
        const msgSpan = document.createElement('div');
        msgSpan.innerHTML = message;
        bubble.appendChild(msgSpan);
        
        const timeSpan = document.createElement('div');
        timeSpan.style.cssText = 'font-size: 9px; opacity: 0.5; margin-top: 4px; text-align: right;';
        timeSpan.innerHTML = new Date().toLocaleTimeString();
        bubble.appendChild(timeSpan);
        
        msgDiv.appendChild(bubble);
        container.appendChild(msgDiv);
        scrollChatToBottom();
    }
    
    function appendSystemMessage(message) {
        const container = document.getElementById('chatMessages');
        const msgDiv = document.createElement('div');
        msgDiv.style.cssText = 'text-align: center; margin: 10px;';
        msgDiv.innerHTML = `<span style="background: rgba(255,255,255,0.1); padding: 5px 10px; border-radius: 10px; font-size: 11px; color: #aaa;">${message}</span>`;
        container.appendChild(msgDiv);
        scrollChatToBottom();
    }
    
    function markChatMessagesRead() {
        if (currentChatUser) {
            chatSocket.emit('mark_read', {username: currentUser, other_user: currentChatUser});
            chatUnreadCount = 0;
            updateChatBadge();
        }
    }
    
    function updateChatBadge() {
        const badge = document.getElementById('chatUnread');
        if (badge) {
            badge.textContent = chatUnreadCount;
        }
    }
    
    function scrollChatToBottom() {
        const area = document.getElementById('chatMessages');
        area.scrollTop = area.scrollHeight;
    }
    
    function openChatPanel() {
        const panel = document.getElementById('chatPanel');
        panel.classList.add('open');
        if (chatSocket && currentUser) {
            loadChatUserList(null);
        }
    }
    
    function minimizeChatPanel() {
        const panel = document.getElementById('chatPanel');
        panel.classList.remove('open');
    }
    
    function closeChatPanel() {
        const panel = document.getElementById('chatPanel');
        panel.classList.remove('open');
        document.getElementById('chatUserList').style.display = 'block';
        document.getElementById('chatMessagesArea').style.display = 'none';
        document.getElementById('chatInputArea').style.display = 'none';
        currentChatUser = null;
    }
    
    let typingTimeout = null;
    document.addEventListener('DOMContentLoaded', function() {
        const input = document.getElementById('chatInput');
        if (input) {
            input.addEventListener('input', function() {
                if (chatSocket && currentChatUser) {
                    clearTimeout(typingTimeout);
                    chatSocket.emit('typing', {sender: currentUser, receiver: currentChatUser, is_typing: true});
                    typingTimeout = setTimeout(function() {
                        chatSocket.emit('typing', {sender: currentUser, receiver: currentChatUser, is_typing: false});
                    }, 1000);
                }
            });
        }
    });
    
    function switchTab(tabId) {
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.content').forEach(c => c.classList.remove('active'));
        event.target.classList.add('active');
        document.getElementById(tabId).classList.add('active');
        if(tabId === 'myLicenses') loadMyLicenses();
        if(tabId === 'registrations') loadRegistrations();
        if(tabId === 'userRequests') loadUserRequests();
        if(tabId === 'history') loadHistory();
        if(tabId === 'admins' && currentRole === 'master') loadAdmins();
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
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({admin_username: currentUser, admin_password: currentPassword})
        });
        const data = await res.json();
        if(data.success) {
            document.getElementById('statTrials').textContent = data.trials;
            document.getElementById('statCustom').textContent = data.custom || 0;
            document.getElementById('statPermanent').textContent = data.permanent || 0;
            document.getElementById('statRegistrations').textContent = data.pending_registrations || 0;
            document.getElementById('statRequests').textContent = data.pending_requests || 0;
            document.getElementById('currentCredits').textContent = data.user_credits || 'Unlimited';
        }
    }
    
    function showCredentials(key, user, pass, type, expires) {
        const modal = document.getElementById('credsModal');
        document.getElementById('modalTitle').innerHTML = `🔑 ${key}`;
        document.getElementById('modalBody').innerHTML = `
            <div class="result-box">
                <p><strong>License:</strong> <code>${key}</code> <button class="copy-btn" onclick="copyToClipboard('${key}')">Copy</button></p>
                <p><strong>Username:</strong> <code>${user}</code> <button class="copy-btn" onclick="copyToClipboard('${user}')">Copy</button></p>
                <p><strong>Password:</strong> <code>${pass}</code> <button class="copy-btn" onclick="copyToClipboard('${pass}')">Copy</button></p>
                <p><strong>Type:</strong> ${type}</p>
                <p><strong>Expires:</strong> ${expires || 'NEVER'}</p>
            </div>
        `;
        modal.style.display = 'block';
    }
    
    function copyToClipboard(text) { navigator.clipboard.writeText(text); alert('Copied!'); }
    function copyAllCredentials() {
        let text = '';
        document.querySelectorAll('#modalBody code').forEach(el => text += el.innerText + '\\n');
        navigator.clipboard.writeText(text);
        alert('All copied!');
    }
    
    async function generateTrial() {
        const duration = document.getElementById('trialDuration').value;
        const res = await fetch(API_URL + '/api/admin/generate-trial', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({admin_username: currentUser, admin_password: currentPassword, duration_hours: parseInt(duration)})
        });
        const data = await res.json();
        const resultDiv = document.getElementById('trialResult');
        resultDiv.style.display = 'block';
        if(data.success) {
            showCredentials(data.license_key, data.username, data.password, 'Trial', data.expires_at);
            resultDiv.innerHTML = `✅ CREATED!<br>🔑 ${data.license_key}<br>👤 ${data.username}<br>🔒 ${data.password}<br>💰 Used: ${data.credits_used}<br>💳 Remaining: ${data.remaining_credits}`;
            loadStats(); loadMyLicenses(); loadHistory();
        } else { resultDiv.innerHTML = `❌ ${data.error}`; }
    }
    
    async function createCustomActivation() {
        if(currentRole === 'moderator') { alert('Moderators cannot create Custom licenses!'); return; }
        const username = document.getElementById('customUsername').value;
        const password = document.getElementById('customPassword').value;
        const license = document.getElementById('customLicense').value;
        const durationType = document.getElementById('customDurationType').value;
        const durationValue = parseFloat(document.getElementById('customDurationValue').value);
        if(!username || !password || !license) { alert('Fill all fields!'); return; }
        const res = await fetch(API_URL + '/api/admin/create-custom-activation', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({admin_username: currentUser, admin_password: currentPassword, username, password, license_key: license, duration_type: durationType, duration_value: durationValue})
        });
        const data = await res.json();
        const resultDiv = document.getElementById('customResult');
        resultDiv.style.display = 'block';
        if(data.success) {
            showCredentials(license, username, password, 'Custom', data.expires_at);
            resultDiv.innerHTML = `✅ CREATED!<br>🔑 ${license}<br>👤 ${username}<br>🔒 ${password}<br>📅 ${data.expires_at || 'NEVER'}<br>💰 Used: ${data.credits_used}<br>💳 Remaining: ${data.remaining_credits}`;
            document.getElementById('customUsername').value = '';
            document.getElementById('customPassword').value = '';
            document.getElementById('customLicense').value = '';
            document.getElementById('customDurationValue').value = '';
            loadStats(); loadMyLicenses(); loadHistory();
        } else { resultDiv.innerHTML = `❌ ${data.error}`; }
    }
    
    async function createPermanentLicense() {
        if(currentRole !== 'master') { alert('Only Master can create Permanent licenses!'); return; }
        const license = document.getElementById('permLicenseKey').value;
        const username = document.getElementById('permUsername').value;
        const password = document.getElementById('permPassword').value;
        if(!license) { alert('License key required!'); return; }
        const res = await fetch(API_URL + '/api/admin/create-permanent-license', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({admin_username: currentUser, admin_password: currentPassword, license_key: license, username, password})
        });
        const data = await res.json();
        const resultDiv = document.getElementById('permResult');
        resultDiv.style.display = 'block';
        if(data.success) {
            showCredentials(license, username || 'N/A', password || 'N/A', 'Permanent', 'Never');
            resultDiv.innerHTML = `✅ PERMANENT CREATED!<br>🔑 ${license}<br>💰 Remaining: ${data.remaining_credits}`;
            document.getElementById('permLicenseKey').value = '';
            document.getElementById('permUsername').value = '';
            document.getElementById('permPassword').value = '';
            loadStats(); loadMyLicenses(); loadHistory();
        } else { resultDiv.innerHTML = `❌ ${data.error}`; }
    }
    
    async function loadMyLicenses() {
        await loadMyTrials();
        if(currentRole !== 'moderator') await loadMyCustom();
        if(currentRole === 'master') await loadMyPermanent();
    }
    
    async function loadMyTrials() {
        const res = await fetch(API_URL + '/api/admin/get-my-trials', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({admin_username: currentUser, admin_password: currentPassword})
        });
        const data = await res.json();
        let html = '<table><tr><th>License</th><th>Duration</th><th>HWIDs</th><th>Expires</th><th>Status</th><th>Usage</th><th>Action</th></tr>';
        data.trials.forEach(t => {
            html += `<tr>
                <td>${t.license_key} <button class="copy-btn" onclick="event.stopPropagation(); copyToClipboard('${t.license_key}')">Copy</button></td>
                <td>${t.duration_hours}</td>
                <td>${t.hwid_count || 0}</td>
                <td>${t.expires_at || '-'}</td>
                <td>${t.status}</td>
                <td>${t.usage_count || 0}</td>
                <td><button class="btn-danger" onclick="deleteTrial('${t.license_key}')">Delete</button></td>
            </tr>`;
        });
        html += '</table>';
        document.getElementById('myTrialsList').innerHTML = html;
    }
    
    async function loadMyCustom() {
        const res = await fetch(API_URL + '/api/admin/get-my-custom', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({admin_username: currentUser, admin_password: currentPassword})
        });
        const data = await res.json();
        let html = '<table><tr><th>License</th><th>Username</th><th>Password</th><th>HWIDs</th><th>Expires</th><th>Status</th><th>Usage</th><th>Action</th></tr>';
        data.activations.forEach(a => {
            html += `<tr>
                <td>${a.license_key} <button class="copy-btn" onclick="copyToClipboard('${a.license_key}')">Copy</button></td>
                <td>${a.username} <button class="copy-btn" onclick="copyToClipboard('${a.username}')">Copy</button></td>
                <td>${a.password} <button class="copy-btn" onclick="copyToClipboard('${a.password}')">Copy</button></td>
                <td>${a.hwids ? a.hwids.length : 0}</td>
                <td>${a.expires_at || 'NEVER'}</td>
                <td class="${a.status === 'ACTIVE' ? 'success' : 'warning'}">${a.status}</td>
                <td>${a.usage_count || 0}</td>
                <td><button class="btn-danger" onclick="deleteCustomActivation('${a.license_key}')">Delete</button></td>
            </tr>`;
        });
        html += '</table>';
        document.getElementById('myCustomList').innerHTML = html;
    }
    
    async function loadMyPermanent() {
        const res = await fetch(API_URL + '/api/admin/get-my-permanent', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({admin_username: currentUser, admin_password: currentPassword})
        });
        const data = await res.json();
        let html = '<table><tr><th>License</th><th>Username</th><th>HWIDs</th><th>Status</th><th>Usage</th><th>Action</th></tr>';
        data.licenses.forEach(l => {
            html += `<tr>
                <td>${l.license_key} <button class="copy-btn" onclick="copyToClipboard('${l.license_key}')">Copy</button></td>
                <td>${l.username || '-'}</td>
                <td>${l.hwids ? l.hwids.length : 0}</td>
                <td>${l.status}</td>
                <td>${l.usage_count || 0}</td>
                <td><button class="btn-danger" onclick="deletePermanentLicense('${l.license_key}')">Delete</button></td>
            </tr>`;
        });
        html += '</table>';
        document.getElementById('myPermanentList').innerHTML = html;
    }
    
    async function loadRegistrations() {
        const res = await fetch(API_URL + '/api/admin/get-registrations', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({admin_username: currentUser, admin_password: currentPassword})
        });
        const data = await res.json();
        let html = '<table><tr><th>Date</th><th>Username</th><th>Telegram</th><th>Facebook</th><th>Reason</th><th>Status</th><th>Action</th></tr>';
        data.registrations.forEach((reg, idx) => {
            html += `<tr>
                <td>${new Date(reg.created_at).toLocaleString()}</td>
                <td><strong>${reg.username}</strong></td>
                <td>${reg.telegram || '-'}</td>
                <td>${reg.facebook || '-'}</td>
                <td>${reg.reason ? reg.reason.substring(0, 50) : '-'}</td>
                <td><span class="badge badge-${reg.status}">${reg.status}</span></td>
                <td>
                    ${reg.status === 'pending' ? `
                        <button class="btn-success" onclick="approveRegistration(${idx}, '${reg.username}', '${reg.telegram}')">Approve</button>
                        <button class="btn-danger" onclick="rejectRegistration(${idx})">Reject</button>
                    ` : '-'}
                </td>
            </tr>`;
        });
        html += '</table>';
        document.getElementById('registrationsList').innerHTML = html;
    }
    
    async function approveRegistration(idx, username, telegram) {
        if(!confirm(`Approve registration for ${username}?`)) return;
        const licenseType = prompt('Select license type:\n1 - Trial\n2 - Custom\n3 - Permanent', '1');
        if(!licenseType) return;
        
        if(licenseType === '1') {
            const duration = prompt('Duration in hours (e.g., 24, 168, 720):', '168');
            if(!duration) return;
            const res = await fetch(API_URL + '/api/admin/approve-registration-trial', {
                method: 'POST', headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({admin_username: currentUser, admin_password: currentPassword, registration_index: idx, duration_hours: parseInt(duration)})
            });
            const data = await res.json();
            if(data.success) {
                alert(`License created!\n\nLicense Key: ${data.license_key}\nUsername: ${data.username}\nPassword: ${data.password}\n\nContact user on Telegram: ${telegram}`);
                loadRegistrations(); loadStats();
            } else { alert('Error: ' + data.error); }
        } else if(licenseType === '2') {
            const durationType = prompt('Duration type (hours/days/weeks/months/years/unlimited):', 'days');
            const durationValue = prompt('Duration value:', '7');
            if(!durationType || !durationValue) return;
            const res = await fetch(API_URL + '/api/admin/approve-registration-custom', {
                method: 'POST', headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({admin_username: currentUser, admin_password: currentPassword, registration_index: idx, duration_type: durationType, duration_value: parseFloat(durationValue)})
            });
            const data = await res.json();
            if(data.success) {
                alert(`License created!\n\nLicense Key: ${data.license_key}\nUsername: ${data.username}\nPassword: ${data.password}\n\nContact user on Telegram: ${telegram}`);
                loadRegistrations(); loadStats();
            } else { alert('Error: ' + data.error); }
        } else if(licenseType === '3') {
            const res = await fetch(API_URL + '/api/admin/approve-registration-permanent', {
                method: 'POST', headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({admin_username: currentUser, admin_password: currentPassword, registration_index: idx})
            });
            const data = await res.json();
            if(data.success) {
                alert(`Permanent License created!\n\nLicense Key: ${data.license_key}\nUsername: ${data.username}\nPassword: ${data.password}\n\nContact user on Telegram: ${telegram}`);
                loadRegistrations(); loadStats();
            } else { alert('Error: ' + data.error); }
        }
    }
    
    async function rejectRegistration(idx) {
        if(!confirm('Reject this registration?')) return;
        const res = await fetch(API_URL + '/api/admin/reject-registration', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({admin_username: currentUser, admin_password: currentPassword, registration_index: idx})
        });
        const data = await res.json();
        if(data.success) { alert('Registration rejected!'); loadRegistrations(); loadStats(); }
        else { alert('Error: ' + data.error); }
    }
    
    async function loadUserRequests() {
        const res = await fetch(API_URL + '/api/admin/get-requests', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({admin_username: currentUser, admin_password: currentPassword})
        });
        const data = await res.json();
        let html = '<table><tr><th>Date</th><th>License</th><th>User</th><th>Type</th><th>Message</th><th>Status</th><th>Action</th></tr>';
        data.requests.forEach((req, idx) => {
            html += `<tr>
                <td>${new Date(req.created_at).toLocaleString()}</td>
                <td>${req.license_key}</td>
                <td>${req.username}</td>
                <td>${req.request_type}</td>
                <td>${req.message.substring(0, 50)}...</td>
                <td><span class="badge badge-${req.status}">${req.status}</span></td>
                <td>${req.status === 'pending' ? `<button class="btn-success" onclick="approveRequest(${idx}, '${req.license_key}', '${req.request_type}', ${req.days_requested || 7})">Approve</button>
                    <button class="btn-danger" onclick="rejectRequest(${idx})">Reject</button>` : '-'}</td>
            </tr>`;
        });
        html += '</table>';
        document.getElementById('requestsList').innerHTML = html;
    }
    
    async function approveRequest(reqIdx, licenseKey, reqType, days) {
        if(!confirm(`Approve request for ${licenseKey}?`)) return;
        const res = await fetch(API_URL + '/api/admin/approve-request', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({admin_username: currentUser, admin_password: currentPassword, request_index: reqIdx, license_key: licenseKey, request_type: reqType, days_to_add: days})
        });
        const data = await res.json();
        if(data.success) { alert('Approved!'); loadUserRequests(); loadStats(); }
        else { alert('Error: ' + data.error); }
    }
    
    async function rejectRequest(reqIdx) {
        if(!confirm('Reject this request?')) return;
        const res = await fetch(API_URL + '/api/admin/reject-request', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({admin_username: currentUser, admin_password: currentPassword, request_index: reqIdx})
        });
        const data = await res.json();
        if(data.success) { alert('Rejected!'); loadUserRequests(); }
        else { alert('Error: ' + data.error); }
    }
    
    async function loadHistory() {
        const res = await fetch(API_URL + '/api/admin/get-history', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({admin_username: currentUser, admin_password: currentPassword})
        });
        const data = await res.json();
        let html = '<table><tr><th>Created</th><th>License</th><th>Username</th><th>Password</th><th>Type</th><th>Owner</th><th>Expires</th><th>Action</th></tr>';
        data.history.forEach(h => {
            html += `<tr>
                <td>${new Date(h.created_at).toLocaleString()}</td>
                <td><strong>${h.license_key}</strong> <button class="copy-btn" onclick="copyToClipboard('${h.license_key}')">Copy</button></td>
                <td>${h.username} <button class="copy-btn" onclick="copyToClipboard('${h.username}')">Copy</button></td>
                <td>${h.password} <button class="copy-btn" onclick="copyToClipboard('${h.password}')">Copy</button></td>
                <td>${h.type}</td>
                <td>${h.owner}</td>
                <td>${h.expires_at || 'NEVER'}</td>
                <td><button onclick="showCredentials('${h.license_key}', '${h.username}', '${h.password}', '${h.type}', '${h.expires_at}')">View</button></td>
            </tr>`;
        });
        html += '</table>';
        document.getElementById('historyList').innerHTML = html;
    }
    
    function filterHistory() {
        const search = document.getElementById('historySearch').value.toLowerCase();
        const rows = document.querySelectorAll('#historyList tr');
        rows.forEach((row, i) => { if(i > 0) row.style.display = row.textContent.toLowerCase().includes(search) ? '' : 'none'; });
    }
    
    async function exportHistory() {
        window.open(API_URL + '/api/admin/export-history?admin_username=' + currentUser + '&admin_password=' + currentPassword);
    }
    
    async function loadAdmins() {
        const res = await fetch(API_URL + '/api/admin/get-admins', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({admin_username: currentUser, admin_password: currentPassword})
        });
        const data = await res.json();
        let adminsHtml = '<tr><tr><th>Username</th><th>Credits</th><th>Created</th><th>Action</th></tr>';
        data.admins.forEach(a => { adminsHtml += `<tr><td>${a.username}</td><td>${a.credits}</td><td>${a.created_at || '-'}</td><td><button class="btn-danger" onclick="deleteAdmin('${a.username}')">Delete</button></td></tr>`; });
        adminsHtml += '</table>';
        document.getElementById('adminsList').innerHTML = adminsHtml;
        
        let modsHtml = '<table><tr><th>Username</th><th>Credits</th><th>Created</th><th>Action</th></tr>';
        data.moderators.forEach(m => { modsHtml += `<tr><td>${m.username}</td><td>${m.credits}</td><td>${m.created_at || '-'}</td><td><button class="btn-danger" onclick="deleteModerator('${m.username}')">Delete</button></td></tr>`; });
        modsHtml += '<table>';
        document.getElementById('moderatorsList').innerHTML = modsHtml;
    }
    
    async function addAdmin() {
        const username = document.getElementById('newAdminUser').value;
        const password = document.getElementById('newAdminPass').value;
        const role = document.getElementById('newAdminRole').value;
        const credits = parseFloat(document.getElementById('newAdminCredits').value);
        const res = await fetch(API_URL + '/api/admin/add-admin', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({admin_username: currentUser, admin_password: currentPassword, new_username: username, new_password: password, role: role, credits: credits})
        });
        const data = await res.json();
        if(data.success) { alert('User added!'); loadAdmins(); }
        else { alert('Error: ' + data.error); }
    }
    
    async function changeUserRole() {
        const username = document.getElementById('roleChangeUser').value;
        const newRole = document.getElementById('newRoleSelect').value;
        const res = await fetch(API_URL + '/api/admin/change-role', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({admin_username: currentUser, admin_password: currentPassword, target_username: username, new_role: newRole})
        });
        const data = await res.json();
        if(data.success) { alert(`Role changed to ${newRole}!`); loadAdmins(); }
        else { alert('Error: ' + data.error); }
    }
    
    async function changeOtherPassword() {
        const targetUser = document.getElementById('targetUsername').value;
        const newPass = document.getElementById('newPasswordForTarget').value;
        const res = await fetch(API_URL + '/api/admin/change-other-password', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({admin_username: currentUser, admin_password: currentPassword, target_username: targetUser, new_password: newPass})
        });
        const data = await res.json();
        if(data.success) { alert('Password changed!'); }
        else { alert('Error: ' + data.error); }
    }
    
    async function manageCredits() {
        const username = document.getElementById('creditUsername').value;
        const amount = parseFloat(document.getElementById('creditAmount').value);
        const res = await fetch(API_URL + '/api/admin/manage-credits', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({admin_username: currentUser, admin_password: currentPassword, target_username: username, amount: amount})
        });
        const data = await res.json();
        if(data.success) { alert(`New balance: ${data.new_balance}`); loadAdmins(); if(username === currentUser) loadStats(); }
        else { alert('Error: ' + data.error); }
    }
    
    async function changePassword() {
        const oldPass = document.getElementById('oldPassword').value;
        const newPass = document.getElementById('newPassword').value;
        const confirmPass = document.getElementById('confirmPassword').value;
        if(newPass !== confirmPass) { alert('Passwords do not match!'); return; }
        const res = await fetch(API_URL + '/api/admin/change-password', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({username: currentUser, old_password: oldPass, new_password: newPass})
        });
        const data = await res.json();
        const resultDiv = document.getElementById('passwordResult');
        resultDiv.style.display = 'block';
        if(data.success) { resultDiv.innerHTML = '✅ Password changed! Please login again.'; setTimeout(() => location.reload(), 2000); }
        else { resultDiv.innerHTML = '❌ ' + data.error; }
    }
    
    async function loadMonitor() {
        const res = await fetch(API_URL + '/api/admin/get-monitor-data', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({admin_username: currentUser, admin_password: currentPassword})
        });
        const data = await res.json();
        document.getElementById('monitorData').innerHTML = `📊 STATUS<br><br>🔹 Trials: ${data.my_trials}<br>🔹 Custom: ${data.my_custom}<br>🔹 Permanent: ${data.my_permanent}<br>🔹 Registrations: ${data.registrations}<br>🔹 Requests: ${data.pending_requests}<br>🔹 History: ${data.history_count}<br>🔹 Active Users: ${data.active_users}<br><br>⏰ ${data.server_time}`;
    }
    
    async function deleteTrial(key) { if(confirm('Delete this trial?')) { await fetch(API_URL + '/api/admin/delete-trial', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({admin_username:currentUser,admin_password:currentPassword,license_key:key})}); loadMyTrials(); loadStats(); } }
    async function deleteCustomActivation(key) { if(confirm('Delete this activation?')) { await fetch(API_URL + '/api/admin/delete-custom-activation', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({admin_username:currentUser,admin_password:currentPassword,license_key:key})}); loadMyCustom(); loadStats(); } }
    async function deletePermanentLicense(key) { if(confirm('Delete this license?')) { await fetch(API_URL + '/api/admin/delete-permanent-license', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({admin_username:currentUser,admin_password:currentPassword,license_key:key})}); loadMyPermanent(); loadStats(); } }
    async function deleteAdmin(username) { if(confirm(`Delete ${username}?`)) { await fetch(API_URL + '/api/admin/delete-admin', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({admin_username:currentUser,admin_password:currentPassword,target_username:username,role:'admin'})}); loadAdmins(); } }
    async function deleteModerator(username) { if(confirm(`Delete ${username}?`)) { await fetch(API_URL + '/api/admin/delete-admin', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({admin_username:currentUser,admin_password:currentPassword,target_username:username,role:'moderator'})}); loadAdmins(); } }
    
    function closeModal() { document.getElementById('credsModal').style.display = 'none'; }
    setInterval(() => { if(document.getElementById('mainPanel').style.display === 'block') loadStats(); }, 30000);
</script>
</body>
</html>
"""

# ==================================================
# 🔐 API ENDPOINTS (Keep all your existing endpoints)
# ==================================================

# [PASTE ALL YOUR EXISTING API ENDPOINTS HERE]
# The endpoints from your original server.py go here...
# (I'll include them in the final output)

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
    pending_requests = sum(1 for r in USER_REQUESTS if r.get("status") == "pending")
    pending_registrations = sum(1 for r in USER_REGISTRATIONS if r.get("status") == "pending")
    
    return jsonify({
        "success": True,
        "trials": len(licenses["trials"]),
        "custom": len(licenses["custom"]),
        "permanent": len(licenses["permanent"]),
        "history_count": len(history),
        "pending_requests": pending_requests,
        "pending_registrations": pending_registrations,
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
    expires_at = datetime.utcnow() + timedelta(hours=dur)
    
    TRIAL_LICENSES[lic] = {
        "type": "trial",
        "owner": auth["username"],
        "hwids": [],
        "duration_hours": dur,
        "start_time": None,
        "expires_at": expires_at.isoformat(),
        "activated_at": None
    }
    TRIAL_USERS[user] = {"password": pwd, "linked_license": lic}
    VALID_USERS[user] = pwd
    
    add_to_history(lic, user, pwd, "Trial", auth["username"], expires_at.isoformat(), {"duration_hours": dur})
    
    save_data()
    remaining = get_credits(auth["username"])
    
    return jsonify({
        "success": True,
        "license_key": lic,
        "username": user,
        "password": pwd,
        "expires_at": expires_at.isoformat(),
        "credits_used": credits_cost,
        "remaining_credits": remaining
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
    
    add_to_history(license_key, username, password, "Custom", auth["username"], 
                   expires_at.isoformat() if expires_at else "UNLIMITED", 
                   {"duration_type": duration_type, "duration_value": duration_value})
    
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
    
    add_to_history(license_key, username if username else "N/A", password if password else "N/A", 
                   "Permanent", auth["username"], "NEVER", {})
    
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
                "password": v.get("password"),
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
    pending_registrations = sum(1 for r in USER_REGISTRATIONS if r.get("status") == "pending")
    
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
        "registrations": pending_registrations,
        "pending_requests": pending_requests,
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
                if user in VALID_USERS:
                    del VALID_USERS[user]
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
        
        username = CUSTOM_ACTIVATIONS[key].get("username")
        if username in VALID_USERS:
            del VALID_USERS[username]
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
        
        username = PERMANENT_LICENSES[key].get("username")
        if username and username in VALID_USERS:
            del VALID_USERS[username]
        del PERMANENT_LICENSES[key]
        save_data()
        return jsonify({"success": True}), 200
    return jsonify({"success": False, "error": "Not found"}), 404

@app.route('/api/admin/get-registrations', methods=['POST'])
def admin_get_registrations():
    data = request.get_json()
    auth = check_admin_auth(data)
    if not auth["authorized"]:
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    if auth["role"] == "master":
        registrations = USER_REGISTRATIONS
    else:
        registrations = []
    
    registrations.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return jsonify({"registrations": registrations}), 200

@app.route('/api/admin/approve-registration-trial', methods=['POST'])
def admin_approve_registration_trial():
    data = request.get_json()
    auth = check_admin_auth(data)
    if not auth["authorized"] or auth["role"] != "master":
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    reg_index = data.get("registration_index")
    duration_hours = data.get("duration_hours", 168)
    
    if reg_index is None or reg_index >= len(USER_REGISTRATIONS):
        return jsonify({"success": False, "error": "Registration not found"}), 404
    
    reg = USER_REGISTRATIONS[reg_index]
    
    lic = f"JEPFX-TRIAL-{uuid.uuid4().hex[:8].upper()}"
    user = reg["username"]
    pwd = reg["password"]
    expires_at = datetime.utcnow() + timedelta(hours=duration_hours)
    
    TRIAL_LICENSES[lic] = {
        "type": "trial",
        "owner": auth["username"],
        "hwids": [],
        "duration_hours": duration_hours,
        "start_time": None,
        "expires_at": expires_at.isoformat(),
        "activated_at": None
    }
    TRIAL_USERS[user] = {"password": pwd, "linked_license": lic}
    VALID_USERS[user] = pwd
    
    add_to_history(lic, user, pwd, "Trial", auth["username"], expires_at.isoformat(), {"duration_hours": duration_hours})
    
    USER_REGISTRATIONS[reg_index]["status"] = "approved"
    USER_REGISTRATIONS[reg_index]["license_key"] = lic
    USER_REGISTRATIONS[reg_index]["approved_at"] = datetime.utcnow().isoformat()
    
    save_data()
    
    return jsonify({
        "success": True,
        "license_key": lic,
        "username": user,
        "password": pwd
    }), 200

@app.route('/api/admin/approve-registration-custom', methods=['POST'])
def admin_approve_registration_custom():
    data = request.get_json()
    auth = check_admin_auth(data)
    if not auth["authorized"] or auth["role"] != "master":
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    reg_index = data.get("registration_index")
    duration_type = data.get("duration_type", "days")
    duration_value = float(data.get("duration_value", 30))
    
    if reg_index is None or reg_index >= len(USER_REGISTRATIONS):
        return jsonify({"success": False, "error": "Registration not found"}), 404
    
    reg = USER_REGISTRATIONS[reg_index]
    
    now = datetime.utcnow()
    expires_at = None
    
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
    
    license_key = f"JEPFX-CUSTOM-{uuid.uuid4().hex[:8].upper()}"
    
    CUSTOM_ACTIVATIONS[license_key] = {
        "username": reg["username"],
        "password": reg["password"],
        "license_key": license_key,
        "owner": auth["username"],
        "hwids": [],
        "expires_at": expires_at.isoformat() if expires_at else None,
        "created_at": now.isoformat(),
        "activated": False
    }
    
    VALID_USERS[reg["username"]] = reg["password"]
    
    add_to_history(license_key, reg["username"], reg["password"], "Custom", auth["username"], 
                   expires_at.isoformat() if expires_at else "UNLIMITED", 
                   {"duration_type": duration_type, "duration_value": duration_value})
    
    USER_REGISTRATIONS[reg_index]["status"] = "approved"
    USER_REGISTRATIONS[reg_index]["license_key"] = license_key
    USER_REGISTRATIONS[reg_index]["approved_at"] = now.isoformat()
    
    save_data()
    
    return jsonify({
        "success": True,
        "license_key": license_key,
        "username": reg["username"],
        "password": reg["password"]
    }), 200

@app.route('/api/admin/approve-registration-permanent', methods=['POST'])
def admin_approve_registration_permanent():
    data = request.get_json()
    auth = check_admin_auth(data)
    if not auth["authorized"] or auth["role"] != "master":
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    reg_index = data.get("registration_index")
    
    if reg_index is None or reg_index >= len(USER_REGISTRATIONS):
        return jsonify({"success": False, "error": "Registration not found"}), 404
    
    reg = USER_REGISTRATIONS[reg_index]
    
    license_key = f"JEPFX-PERM-{uuid.uuid4().hex[:8].upper()}"
    
    PERMANENT_LICENSES[license_key] = {
        "type": "permanent",
        "owner": auth["username"],
        "username": reg["username"],
        "password": reg["password"],
        "hwids": [],
        "expires_at": None,
        "created_at": datetime.utcnow().isoformat()
    }
    
    VALID_USERS[reg["username"]] = reg["password"]
    
    add_to_history(license_key, reg["username"], reg["password"], "Permanent", auth["username"], "NEVER", {})
    
    USER_REGISTRATIONS[reg_index]["status"] = "approved"
    USER_REGISTRATIONS[reg_index]["license_key"] = license_key
    USER_REGISTRATIONS[reg_index]["approved_at"] = datetime.utcnow().isoformat()
    
    save_data()
    
    return jsonify({
        "success": True,
        "license_key": license_key,
        "username": reg["username"],
        "password": reg["password"]
    }), 200

@app.route('/api/admin/reject-registration', methods=['POST'])
def admin_reject_registration():
    data = request.get_json()
    auth = check_admin_auth(data)
    if not auth["authorized"] or auth["role"] != "master":
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    reg_index = data.get("registration_index")
    
    if reg_index is None or reg_index >= len(USER_REGISTRATIONS):
        return jsonify({"success": False, "error": "Registration not found"}), 404
    
    USER_REGISTRATIONS[reg_index]["status"] = "rejected"
    USER_REGISTRATIONS[reg_index]["rejected_at"] = datetime.utcnow().isoformat()
    
    save_data()
    return jsonify({"success": True}), 200

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
    return render_template_string(USER_PORTAL_HTML)

@app.route('/api/user/register', methods=['POST'])
def user_register():
    data = request.get_json()
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    telegram = data.get("telegram", "").strip()
    facebook = data.get("facebook", "").strip()
    reason = data.get("reason", "").strip()
    
    if not username or not password or not telegram:
        return jsonify({"success": False, "error": "Username, password, and Telegram contact are required"}), 400
    
    if username in VALID_USERS or username in TRIAL_USERS or username in [r.get("username") for r in USER_REGISTRATIONS if r.get("status") == "pending"]:
        return jsonify({"success": False, "error": "Username already taken or pending approval"}), 400
    
    USER_REGISTRATIONS.append({
        "username": username,
        "password": password,
        "telegram": telegram,
        "facebook": facebook,
        "reason": reason,
        "status": "pending",
        "created_at": datetime.utcnow().isoformat()
    })
    save_data()
    
    return jsonify({"success": True, "message": "Registration submitted. Admin will review and contact you."}), 200

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
    
    if expires_at and expires_at not in ["NEVER", "UNLIMITED"]:
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
        "expires_at": expires_at if expires_at else "NEVER",
        "is_expired": is_expired,
        "days_left": days_left,
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
        return jsonify({"status": "activated", "msg": f"Activated on {len(activation['hwids'])} device(s)"}), 200
    
    if key in PERMANENT_LICENSES:
        lic = PERMANENT_LICENSES[key]
        if "hwids" not in lic:
            lic["hwids"] = []
        if hwid not in lic["hwids"]:
            lic["hwids"].append(hwid)
            save_data()
        log_usage(key, "activation", {"hwid": hwid})
        return jsonify({"status": "activated"}), 200
    
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
        if hwid not in lic["hwids"]:
            lic["hwids"].append(hwid)
            save_data()
        log_usage(key, "activation", {"hwid": hwid})
        return jsonify({"status": "activated"}), 200
    
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
    return render_template_string(ADMIN_HTML)

@app.route('/')
def home():
    return jsonify({
        "status": "online",
        "message": "JEPFX License Server Running with Live Chat",
        "endpoints": {
            "activate": "/api/activate",
            "verify": "/api/verify-license",
            "validate_user": "/api/validate-user",
            "check_password": "/api/check-password",
            "admin_panel": "/admin",
            "user_portal": "/user"
        }
    })

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=10000, debug=False)