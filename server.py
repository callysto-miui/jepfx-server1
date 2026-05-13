# ------------------------------
# VERIFY LICENSE VALIDITY
# ------------------------------
@app.route('/api/verify-license', methods=['POST'])
def verify():
    data = request.get_json()
    hwid = data.get("hwid", "")
    key_hash = data.get("hash", "")
    now = datetime.utcnow()

    # Check permanent licenses
    for key, lic in LICENSES.items():
        if hashlib.sha256(key.encode()).hexdigest() == key_hash:
            if lic["type"] == "unlimited" and hwid in lic["hwid"]:
                return jsonify({"ok": True}), 200
            if lic["type"] == "single" and lic["hwid"] == hwid:
                return jsonify({"ok": True}), 200

    # Check trial licenses
    for key, lic in TRIAL_LICENSES.items():
        if hashlib.sha256(key.encode()).hexdigest() == key_hash:
            if lic["hwid"] == hwid and lic["expires_at"] and now < lic["expires_at"]:
                return jsonify({"ok": True}), 200
            if lic["expires_at"] and now > lic["expires_at"]:
                return jsonify({"expired": True}), 403
            return jsonify({"invalid": True}), 403

    return jsonify({"invalid": True}), 403

# ------------------------------
# USER LOGIN VALIDATION
# ------------------------------
@app.route('/api/validate-user', methods=['POST'])
def validate_user():
    username = request.get_json().get("username", "")
    if username in VALID_USERS or username in TRIAL_USERS:
        return jsonify({"ok": True}), 200
    return "", 403

@app.route('/api/check-password', methods=['POST'])
def check_password():
    data = request.get_json()
    username = data.get("username", "")
    password = data.get("password", "")

    # Check permanent users
    if username in VALID_USERS and VALID_USERS[username] == password:
        return jsonify({"ok": True}), 200
    # Check trial users
    if username in TRIAL_USERS and TRIAL_USERS[username]["password"] == password:
        return jsonify({"ok": True}), 200

    return "", 403

# ==================================================
# START SERVER
# ==================================================
if name == "main":
    app.run(host="0.0.0.0", port=10000, debug=False)
