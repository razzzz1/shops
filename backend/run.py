# run.py
# ───────
# Entry point for the Flask development server.
#
# Usage:
#   python run.py                    ← start dev server on port 5000
#   flask seed-superuser             ← create the first merchant account
#   flask db init                    ← initialise the migrations folder (once)
#   flask db migrate -m "message"    ← generate a new migration
#   flask db upgrade                 ← apply pending migrations to the DB
#
# For production, replace `python run.py` with a proper WSGI server:
#   gunicorn "run:app" --workers 4 --bind 0.0.0.0:5000

import os
from app import create_app
from app.extensions import db

# Read the environment name from FLASK_ENV; default to "development"
config_name = os.getenv("FLASK_ENV", "development")
app = create_app(config_name)


# ── CLI command: bootstrap the first merchant account ─────────────────────────
@app.cli.command("seed-superuser")
def seed_superuser():
    """
    Create the very first merchant (superuser) account and a default store.

    Run ONCE after setting up the database:
        flask db upgrade
        flask seed-superuser

    The merchant can then invite admins via the /api/auth/invite endpoint.
    IMPORTANT: change the password immediately after first login.
    """
    from app.models import User, Store
    from app.utils  import hash_password

    # ── Create a default store if none exist yet ──────────────────────────────
    store = Store.query.first()
    if not store:
        store = Store(name="Main Store", location="Headquarters")
        db.session.add(store)
        db.session.flush()  # get the store.id without committing
        print(f"  ✓ Default store created: '{store.name}'")
    else:
        print(f"  ℹ Using existing store: '{store.name}'")

    # ── Create the merchant if the email isn't already taken ─────────────────
    email = "merchant@stockflow.app"
    if User.query.filter_by(email=email).first():
        print(f"  ℹ Superuser {email} already exists — skipping.")
        return

    merchant = User(
        email         = email,
        password_hash = hash_password("ChangeMe123!"),
        first_name    = "Super",
        last_name     = "Merchant",
        role          = "merchant",
        store_id      = store.id,
    )
    db.session.add(merchant)
    db.session.commit()

    print(f"  ✓ Superuser created!")
    print(f"    Email    : {email}")
    print(f"    Password : ChangeMe123!")
    print()
    print("  ⚠  IMPORTANT: Change this password immediately after first login!")


# ── Start development server ───────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(
        host  = "0.0.0.0",
        port  = int(os.getenv("PORT", "5000")),
        debug = app.config.get("DEBUG", True),
    )