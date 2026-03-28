# app/models/invitation_token.py
# ───────────────────────────────
# InvitationToken model — a signed, time-limited token sent by email
# to allow a new user to self-register.
#
# Why tokens instead of an open registration page?
# ─────────────────────────────────────────────────
# The system spec requires that ONLY the merchant can add admins, and
# ONLY admins can add clerks.  There is no public sign-up page.
# Instead, an invitation email contains a unique URL with a token.
# The invitee clicks it, fills in their name + password, and an account
# is created with exactly the role and store the inviter intended.
#
# Security properties
# ───────────────────
# • The token is signed by itsdangerous using the app's SECRET_KEY,
#   so it cannot be forged or tampered with.
# • expires_at is checked server-side; old links stop working after 24 h.
# • is_used is flipped to True once registration completes,
#   so each token can only be used ONCE.
#
# Invitation flow
# ───────────────
#   1. Merchant/admin  →  POST /api/auth/invite
#   2. Backend generates token, stores this row, emails the link
#   3. Invitee clicks   →  GET  /api/auth/verify-invite?token=...
#   4. Invitee submits  →  POST /api/auth/register  { token, name, password }
#   5. Backend validates, creates User, sets is_used=True

from datetime import datetime, timezone
from app.extensions import db


class InvitationToken(db.Model):
    __tablename__ = "invitation_tokens"

    # ── Primary key ────────────────────────────────────────────────────────────
    id = db.Column(db.Integer, primary_key=True)

    # ── The token string ───────────────────────────────────────────────────────
    # index=True speeds up the lookup when the invitee submits the token
    token = db.Column(db.String(512), unique=True, nullable=False, index=True)

    # ── Who is being invited ───────────────────────────────────────────────────
    email    = db.Column(db.String(255), nullable=False)   # recipient's email
    role     = db.Column(
        db.Enum("admin", "clerk", name="invite_role_enum"),
        nullable=False,
    )
    # Which store the new user will join
    store_id = db.Column(db.Integer, db.ForeignKey("stores.id"), nullable=True)

    # ── Who sent the invitation ────────────────────────────────────────────────
    inviter_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    # ── Lifecycle fields ───────────────────────────────────────────────────────
    is_used    = db.Column(db.Boolean, default=False, nullable=False)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)

    # ── Timestamp ─────────────────────────────────────────────────────────────
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    inviter = db.relationship("User", back_populates="sent_invitations")

    # ── Helpers ────────────────────────────────────────────────────────────────
    def __repr__(self):
        return (
            f"<InvitationToken id={self.id} "
            f"email={self.email} "
            f"role={self.role} "
            f"used={self.is_used}>"
        )

    def is_valid(self) -> bool:
        """
        Return True only if this token can still be used for registration.

        A token is valid when:
          • It has NOT already been consumed (is_used = False)
          • The current time is BEFORE the expiry timestamp
        """
        now = datetime.now(timezone.utc)
        return (not self.is_used) and (now < self.expires_at)

    def to_dict(self):
        return {
            "id":         self.id,
            "email":      self.email,
            "role":       self.role,
            "store_id":   self.store_id,
            "inviter_id": self.inviter_id,
            "is_used":    self.is_used,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }