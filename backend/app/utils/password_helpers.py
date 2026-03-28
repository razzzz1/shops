# app/utils/password_helpers.py
# ──────────────────────────────
# Password hashing and verification using bcrypt.
#
# Why bcrypt?
# ───────────
# • Automatically generates and embeds a unique random salt per hash.
#   Two calls with the same password produce completely different hashes —
#   that is CORRECT and expected behaviour.
# • The `rounds` parameter (work factor) makes hashing intentionally slow.
#   At rounds=12, hashing takes ~250ms — negligible for a real user, but
#   it means an attacker can only try ~4 passwords/second instead of
#   millions.  This makes brute-force attacks impractical.
# • The hash is self-contained: the salt and work factor are embedded in
#   the hash string itself, so we only store ONE column in the database.
#
# What we NEVER do:
# • Store plain-text passwords.
# • Use MD5 or SHA-256 directly (they are too fast — no work factor).
# • Roll our own hashing algorithm.

import bcrypt


def hash_password(plain_text: str) -> str:
    """
    Hash a plain-text password with bcrypt and return the hash string.

    The returned string is safe to store in the `password_hash` column.
    It looks like: "$2b$12$<22-char-salt><31-char-hash>"

    Parameters
    ----------
    plain_text : str
        The raw password the user typed (e.g. "MySecret123!").

    Returns
    -------
    str
        A 60-character bcrypt hash string.

    Example
    -------
    >>> h = hash_password("hunter2")
    >>> h.startswith("$2b$12$")
    True
    >>> len(h)
    60
    """
    # bcrypt requires bytes, not a str
    encoded = plain_text.encode("utf-8")

    # gensalt(rounds=12) generates a random salt and embeds the work factor.
    # Increasing rounds doubles the hashing time — adjust only when hardware
    # improves and 250ms feels fast.
    salt   = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(encoded, salt)

    # Decode back to str so SQLAlchemy can store it as VARCHAR
    return hashed.decode("utf-8")


def check_password(plain_text: str, hashed: str) -> bool:
    """
    Verify a plain-text password against a stored bcrypt hash.

    bcrypt.checkpw re-derives the salt from the stored hash and compares
    the result in constant time (no timing attacks).

    Parameters
    ----------
    plain_text : str
        The raw password from the login form.
    hashed : str
        The bcrypt hash stored in the database.

    Returns
    -------
    bool
        True  if the password matches the hash.
        False if the password is wrong or the hash is malformed.

    Example
    -------
    >>> h = hash_password("hunter2")
    >>> check_password("hunter2", h)
    True
    >>> check_password("wrong", h)
    False
    """
    try:
        return bcrypt.checkpw(
            plain_text.encode("utf-8"),
            hashed.encode("utf-8"),
        )
    except Exception:
        # Catch malformed hash strings — treat as wrong password, not a crash
        return False