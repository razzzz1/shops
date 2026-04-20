
# app/routes/auth_routes.py
# ──────────────────────────
# Authentication blueprint — every endpoint related to identity:
#
#   POST   /api/auth/login           email + password → JWT tokens
#   POST   /api/auth/refresh         swap refresh token → new access token
#   POST   /api/auth/logout          client-side logout (stateless signal)
#   POST   /api/auth/invite          merchant/admin sends an invitation email
#   GET    /api/auth/verify-invite   frontend checks token before showing form
#   POST   /api/auth/register        invitee completes registration
#
# All endpoints return JSON.  Errors follow the shape {"message": "..."}.

from datetime import datetime, timezone, timedelta

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity,
)
from flask_mail import Message

from app.extensions import db, mail
from app.models     import User, Store, InvitationToken
from app.utils      import (
    hash_password,
    check_password,
    generate_invitation_token,
    verify_invitation_token,
    role_required,
)

# A Blueprint groups related routes under a common prefix.
# The prefix ("/api/auth") is set when the blueprint is registered
# in app/__init__.py via app.register_blueprint(auth_bp, url_prefix="/api/auth").
auth_bp = Blueprint("auth", __name__)


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/auth/login
# ─────────────────────────────────────────────────────────────────────────────

@auth_bp.route("/login", methods=["POST"])
def login():
    """
    Authenticate with email + password.

    Request body (JSON)
    -------------------
    {
        "email":    "user@example.com",
        "password": "MySecret123!"
    }

    Success response (200)
    ----------------------
    {
        "access_token":  "<short-lived JWT>",
        "refresh_token": "<long-lived JWT>",
        "user":          { ...user fields... }
    }

    The access token is used for every subsequent API call (Authorization header).
    The refresh token is used ONLY to obtain a new access token when it expires.
    """
    data = request.get_json(silent=True) or {}

    email    = data.get("email",    "").strip().lower()
    password = data.get("password", "")

    # ── Validate that both fields were provided ────────────────────────────────
    if not email or not password:
        return jsonify({"message": "Email and password are required."}), 400

    # ── Look up user by email ─────────────────────────────────────────────────
    user = User.query.filter_by(email=email).first()

    # ── Check credentials ─────────────────────────────────────────────────────
    # We return the SAME error message whether the email doesn't exist or the
    # password is wrong.  This prevents "user enumeration" — an attacker
    # learning which emails are registered by watching the error messages.
    if not user or not check_password(password, user.password_hash):
        return jsonify({"message": "Invalid email or password."}), 401

    # ── Check account status ──────────────────────────────────────────────────
    if not user.is_active:
        return jsonify({
            "message": "Your account has been deactivated. Contact your administrator."
        }), 403

    # ── Issue tokens ──────────────────────────────────────────────────────────
    # We store the user's integer id as the JWT "identity" (the `sub` claim).
    # Every protected endpoint reads this back with get_jwt_identity() to
    # know which user is making the request.
    access_token  = create_access_token(identity=user.id)
    refresh_token = create_refresh_token(identity=user.id)

    return jsonify({
        "access_token":  access_token,
        "refresh_token": refresh_token,
        "user":          user.to_dict(include_store=True),
    }), 200


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/auth/refresh
# ─────────────────────────────────────────────────────────────────────────────

@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)   # requires a REFRESH token, not an access token
def refresh():
    """
    Issue a new short-lived access token using a valid refresh token.

    The client sends the refresh token in the Authorization header:
        Authorization: Bearer <refresh_token>

    Returns {"access_token": "<new access token>"}

    This keeps the user logged in without re-entering their password,
    while still rotating access tokens frequently for security.
    """
    user_id      = get_jwt_identity()
    access_token = create_access_token(identity=user_id)
    return jsonify({"access_token": access_token}), 200


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/auth/logout
# ─────────────────────────────────────────────────────────────────────────────

@auth_bp.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    """
    Signal a logout.

    Because JWTs are stateless, the server cannot invalidate a token once
    issued.  The client is responsible for deleting the tokens from storage
    (localStorage / cookie).

    In a production system you would add the JWT ID (jti claim) to a Redis
    blocklist here.  For now we simply acknowledge the request.
    """
    return jsonify({"message": "Logged out. Please clear your tokens."}), 200


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/auth/invite
# ─────────────────────────────────────────────────────────────────────────────

@auth_bp.route("/invite", methods=["POST"])
@jwt_required()
@role_required("merchant", "admin")
def send_invitation(current_user: User):
    """
    Send a tokenised registration link to a new user's email address.

    Who can invite whom
    ───────────────────
    • Merchant  →  can invite admins (must supply a store_id)
    • Admin     →  can only invite clerks (store_id is taken from their own account)

    Request body (JSON)
    -------------------
    {
        "email":    "newclerk@example.com",
        "role":     "clerk",          ← "admin" only allowed for merchant
        "store_id": 1                 ← required for merchant; ignored for admin
    }

    On success an email is dispatched and a row is written to invitation_tokens.
    """
    data = request.get_json(silent=True) or {}

    recipient_email = data.get("email", "").strip().lower()
    intended_role   = data.get("role",  "").strip()

    # ── Input validation ──────────────────────────────────────────────────────
    if not recipient_email or not intended_role:
        return jsonify({"message": "'email' and 'role' are required."}), 400

    # ── Enforce role hierarchy ────────────────────────────────────────────────
    if current_user.role == "admin":
        # Admins can ONLY create clerk accounts
        if intended_role != "clerk":
            return jsonify({"message": "Admins can only invite clerks."}), 403
        # Admin always invites into their own store — no choice
        store_id = current_user.store_id

    elif current_user.role == "merchant":
        # Merchants invite admins (the admin then invites their own clerks)
        if intended_role not in ("admin", "clerk"):
            return jsonify({"message": "Invalid role. Choose 'admin' or 'clerk'."}), 400
        store_id = data.get("store_id") or current_user.store_id

    # ── Verify the target store exists ────────────────────────────────────────
    store = Store.query.get(store_id)
    if not store:
        return jsonify({"message": f"Store with id={store_id} not found."}), 404

    # ── Guard against duplicate accounts ─────────────────────────────────────
    if User.query.filter_by(email=recipient_email).first():
        return jsonify({
            "message": f"A user with email '{recipient_email}' already exists."
        }), 409

    # ── Generate a signed token and persist it ────────────────────────────────
    raw_token = generate_invitation_token(recipient_email, intended_role, store_id)

    expires_seconds = current_app.config.get("INVITATION_TOKEN_EXPIRES", 86400)
    token_record = InvitationToken(
        token      = raw_token,
        email      = recipient_email,
        role       = intended_role,
        store_id   = store_id,
        inviter_id = current_user.id,
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_seconds),
    )
    db.session.add(token_record)
    db.session.commit()

    # ── Build the invitation URL ──────────────────────────────────────────────
    frontend_url = current_app.config.get("FRONTEND_URL", "http://localhost:3000")
    invite_url   = f"{frontend_url}/register?token={raw_token}"
    expiry_hours = expires_seconds // 3600

    # ── Always print the link to the terminal ────────────────────────────────
    # This means you can ALWAYS copy the link from the Flask terminal,
    # regardless of whether the email actually sends.
    print("\n" + "="*60)
    print("  INVITATION LINK (copy and open in browser)")
    print("="*60)
    print(f"  To:      {recipient_email}")
    print(f"  Role:    {intended_role}")
    print(f"  Store:   {store.name}")
    print(f"  Expires: {expiry_hours} hours")
    print(f"\n  {invite_url}\n")
    print("="*60 + "\n")

    # ── Also try to send via email (optional) ────────────────────────────────
    email_sent = False
    try:
        msg = Message(
            subject    = "You're invited to join StockFlow",
            recipients = [recipient_email],
            html       = f"""
            <div style="font-family:sans-serif;max-width:520px;margin:auto">
              <h2 style="color:#5b6af5">You have been invited!</h2>
              <p>
                <strong>{current_user.full_name}</strong> has invited you to join
                <strong>{store.name}</strong> as a <strong>{intended_role}</strong>
                on StockFlow.
              </p>
              <p>Click the button below to set up your account.
                 This link expires in <strong>{expiry_hours} hours</strong>.
              </p>
              <a href="{invite_url}"
                 style="display:inline-block;background:#5b6af5;color:#fff;
                        padding:12px 28px;border-radius:8px;text-decoration:none;
                        font-weight:600;margin:16px 0">
                Accept Invitation
              </a>
              <p style="color:#888;font-size:12px">
                If you weren't expecting this invitation, you can safely ignore it.
              </p>
            </div>
            """,
        )
        mail.send(msg)
        email_sent = True
    except Exception as exc:
        # Email failed — that's OK, the link is printed in the terminal above
        current_app.logger.warning(f"Email not sent for {recipient_email}: {exc}")

    # ── Always return success — the link is always in the terminal ────────────
    return jsonify({
        "message": f"Invitation created for {recipient_email}. Check the Flask terminal for the registration link.",
        "token_id":   token_record.id,
        "invite_url": invite_url,      # also returned in the API response
        "email_sent": email_sent,
    }), 201


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/auth/verify-invite?token=<token>
# ─────────────────────────────────────────────────────────────────────────────

@auth_bp.route("/verify-invite", methods=["GET"])
def verify_invite():
    """
    Validate an invitation token and return the embedded metadata.

    The React frontend calls this when the user lands on /register?token=...
    If the response is {"valid": true}, the registration form is shown,
    pre-filled with the email and role from the token.

    If the token is invalid or expired, the frontend shows an error page
    instead of the form.
    """
    raw_token = request.args.get("token", "").strip()

    if not raw_token:
        return jsonify({"valid": False, "message": "No token provided."}), 400

    # ── Check the database record first ──────────────────────────────────────
    # The DB record tells us whether the token has already been used,
    # independently of the cryptographic check below.
    record = InvitationToken.query.filter_by(token=raw_token).first()

    if not record:
        return jsonify({"valid": False, "message": "Invitation not found."}), 404

    if not record.is_valid():
        reason = "already been used" if record.is_used else "expired"
        return jsonify({
            "valid":   False,
            "message": f"This invitation has {reason}."
        }), 400

    # ── Verify the cryptographic signature ────────────────────────────────────
    payload = verify_invitation_token(raw_token)
    if not payload:
        return jsonify({"valid": False, "message": "Token is invalid or tampered."}), 400

    # ── All good — return the metadata the registration form needs ────────────
    return jsonify({
        "valid":    True,
        "email":    record.email,
        "role":     record.role,
        "store_id": record.store_id,
    }), 200


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/auth/register
# ─────────────────────────────────────────────────────────────────────────────

@auth_bp.route("/register", methods=["POST"])
def register():
    """
    Complete registration from an invitation token.

    The invitation token encodes the email, role, and store — the invitee
    only needs to provide their name and chosen password.

    Request body (JSON)
    -------------------
    {
        "token":      "<invitation token from URL>",
        "first_name": "Jane",
        "last_name":  "Smith",
        "password":   "MySecret123!"
    }

    On success, the user is logged in immediately (tokens returned).
    The invitation token is marked as used so it cannot be reused.
    """
    data = request.get_json(silent=True) or {}

    raw_token  = data.get("token",      "").strip()
    first_name = data.get("first_name", "").strip()
    last_name  = data.get("last_name",  "").strip()
    password   = data.get("password",   "")

    # ── Validate all required fields are present ──────────────────────────────
    if not all([raw_token, first_name, last_name, password]):
        return jsonify({
            "message": "token, first_name, last_name, and password are all required."
        }), 400

    # ── Enforce minimum password length ───────────────────────────────────────
    if len(password) < 8:
        return jsonify({
            "message": "Password must be at least 8 characters long."
        }), 400

    # ── Validate the token record (is_used + expires_at) ─────────────────────
    record = InvitationToken.query.filter_by(token=raw_token).first()

    if not record or not record.is_valid():
        return jsonify({
            "message": "This invitation is invalid or has expired."
        }), 400

    # ── Validate the cryptographic signature ──────────────────────────────────
    payload = verify_invitation_token(raw_token)
    if not payload:
        return jsonify({"message": "Token could not be verified."}), 400

    # ── Guard against race condition (two tabs submitting at once) ────────────
    if User.query.filter_by(email=record.email).first():
        return jsonify({
            "message": "An account with this email already exists."
        }), 409

    # ── Create the new user ───────────────────────────────────────────────────
    new_user = User(
        email         = record.email,
        password_hash = hash_password(password),
        first_name    = first_name,
        last_name     = last_name,
        role          = record.role,       # role comes from the token — not the request body
        store_id      = record.store_id,   # store comes from the token — not the request body
        is_active     = True,
    )
    db.session.add(new_user)

    # ── Consume the token so it cannot be used again ──────────────────────────
    record.is_used = True

    db.session.commit()

    # ── Log the new user in immediately ──────────────────────────────────────
    access_token  = create_access_token(identity=new_user.id)
    refresh_token = create_refresh_token(identity=new_user.id)

    return jsonify({
        "message":       "Registration successful. Welcome to StockFlow!",
        "access_token":  access_token,
        "refresh_token": refresh_token,
        "user":          new_user.to_dict(include_store=True),
    }), 201


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/auth/create-user
# ─────────────────────────────────────────────────────────────────────────────

@auth_bp.route("/create-user", methods=["POST"])
@jwt_required()
@role_required("merchant", "admin")
def create_user_directly(current_user: User):
    """
    Create a user account directly — no email/invitation needed.

    This is a simplified alternative to the invitation flow.
    Merchant can create admins and clerks.
    Admin can only create clerks in their own store.

    Request body (JSON)
    -------------------
    {
        "email":      "newclerk@example.com",
        "first_name": "Jane",
        "last_name":  "Smith",
        "password":   "SecurePass1!",
        "role":       "clerk",
        "store_id":   1          (optional — admin uses their own store)
    }
    """
    data = request.get_json(silent=True) or {}

    email      = data.get("email",      "").strip().lower()
    first_name = data.get("first_name", "").strip()
    last_name  = data.get("last_name",  "").strip()
    password   = data.get("password",   "")
    role       = data.get("role",       "clerk").strip()

    # ── Validate required fields ──────────────────────────────────────────────
    if not all([email, first_name, last_name, password]):
        return jsonify({
            "message": "email, first_name, last_name and password are all required."
        }), 400

    if len(password) < 8:
        return jsonify({"message": "Password must be at least 8 characters."}), 400

    # ── Role permission check ─────────────────────────────────────────────────
    if current_user.role == "admin":
        if role != "clerk":
            return jsonify({"message": "Admins can only create clerk accounts."}), 403
        store_id = current_user.store_id
    else:
        # Merchant
        if role not in ("admin", "clerk"):
            return jsonify({"message": "Role must be 'admin' or 'clerk'."}), 400
        store_id = int(data.get("store_id") or current_user.store_id)

    # ── Check email not already taken ─────────────────────────────────────────
    if User.query.filter_by(email=email).first():
        return jsonify({"message": f"A user with email '{email}' already exists."}), 409

    # ── Create the user ───────────────────────────────────────────────────────
    new_user = User(
        email         = email,
        password_hash = hash_password(password),
        first_name    = first_name,
        last_name     = last_name,
        role          = role,
        store_id      = store_id,
        is_active     = True,
    )
    db.session.add(new_user)
    db.session.commit()

    return jsonify({
        "message": f"User {email} created successfully.",
        "user":    new_user.to_dict(include_store=True),
    }), 201