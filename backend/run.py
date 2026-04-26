
# run.py
# ───────
# Entry point for the Flask development server.
#
# Usage:
#   python3 run.py                ← start dev server on port 5000
#   flask seed-superuser          ← create first merchant account + default store
#   flask seed-demo               ← seed FULL demo data (stores, products, users, entries)
#   flask db init                 ← initialise migrations folder (once only)
#   flask db migrate -m "message" ← generate a new migration
#   flask db upgrade              ← apply pending migrations to the DB

import os
from app import create_app
from app.extensions import db

config_name = os.getenv("FLASK_ENV", "development")
app = create_app(config_name)


# ─────────────────────────────────────────────────────────────────────────────
# flask seed-superuser
# Creates the merchant account and one default store
# ─────────────────────────────────────────────────────────────────────────────
@app.cli.command("seed-superuser")
def seed_superuser():
    """Create the first merchant account and a default store."""
    from app.models import User, Store
    from app.utils  import hash_password

    store = Store.query.first()
    if not store:
        store = Store(name="Main Store", location="Nairobi CBD")
        db.session.add(store)
        db.session.flush()
        print(f"  ✓ Store created: '{store.name}'")
    else:
        print(f"  ℹ Using existing store: '{store.name}'")

    email = "merchant@stockflow.app"
    if User.query.filter_by(email=email).first():
        print(f"  ℹ Merchant {email} already exists — skipping.")
        return

    merchant = User(
        email         = email,
        password_hash = hash_password("ChangeMe123!"),
        first_name    = "John",
        last_name     = "Merchant",
        role          = "merchant",
        store_id      = store.id,
    )
    db.session.add(merchant)
    db.session.commit()

    print(f"  ✓ Merchant created!")
    print(f"    Email    : {email}")
    print(f"    Password : ChangeMe123!")


# ─────────────────────────────────────────────────────────────────────────────
# flask seed-demo
# Seeds COMPLETE demo data so the whole app is usable immediately
# ─────────────────────────────────────────────────────────────────────────────
@app.cli.command("seed-demo")
def seed_demo():
    """
    Seed full demo data:
      - 2 stores
      - 1 merchant, 2 admins, 2 clerks
      - 8 products per store
      - 30 inventory entries with realistic data
      - 5 supply requests (pending + resolved)

    Run after flask db upgrade:
        flask seed-demo

    Login accounts created:
        merchant@stockflow.app  / ChangeMe123!
        admin1@stockflow.app    / AdminPass1!
        admin2@stockflow.app    / AdminPass1!
        clerk1@stockflow.app    / ClerkPass1!
        clerk2@stockflow.app    / ClerkPass1!
    """
    from datetime import date, timedelta
    from app.models import User, Store, Product, InventoryEntry, SupplyRequest
    from app.utils  import hash_password

    print("\n  StockFlow Demo Seed")
    print("  " + "="*40)

    # ── 1. Create stores ──────────────────────────────────────────────────────
    store1 = Store.query.filter_by(name="Westlands Branch").first()
    if not store1:
        store1 = Store(name="Westlands Branch", location="Westlands, Nairobi")
        db.session.add(store1)
        print("  ✓ Store created: Westlands Branch")

    store2 = Store.query.filter_by(name="CBD Branch").first()
    if not store2:
        store2 = Store(name="CBD Branch", location="Moi Avenue, Nairobi")
        db.session.add(store2)
        print("  ✓ Store created: CBD Branch")

    db.session.flush()

    # ── 2. Create users ───────────────────────────────────────────────────────
    users_to_create = [
        # (email, first, last, role, password, store)
        ("merchant@stockflow.app", "John",  "Kamau",   "merchant", "ChangeMe123!", store1),
        ("admin1@stockflow.app",   "Mary",  "Wanjiru", "admin",    "AdminPass1!",  store1),
        ("admin2@stockflow.app",   "Peter", "Ochieng", "admin",    "AdminPass1!",  store2),
        ("clerk1@stockflow.app",   "Grace", "Akinyi",  "clerk",    "ClerkPass1!",  store1),
        ("clerk2@stockflow.app",   "James", "Mwangi",  "clerk",    "ClerkPass1!",  store2),
    ]

    created_users = {}
    for email, first, last, role, pwd, store in users_to_create:
        user = User.query.filter_by(email=email).first()
        if not user:
            user = User(
                email         = email,
                password_hash = hash_password(pwd),
                first_name    = first,
                last_name     = last,
                role          = role,
                store_id      = store.id,
                is_active     = True,
            )
            db.session.add(user)
            print(f"  ✓ User created: {email} [{role}]")
        created_users[email] = user

    db.session.flush()

    # ── 3. Create products ────────────────────────────────────────────────────
    products_data = [
        # (store, name, sku, category, unit, buy, sell, reorder)
        (store1, "Full Cream Milk 1L",     "MILK-001", "Dairy",    "litres",  55,  75,  20),
        (store1, "Bread 700g",             "BRD-001",  "Bakery",   "pieces",  45,  65,  15),
        (store1, "Orange Juice 500ml",     "OJ-001",   "Drinks",   "bottles", 80,  110, 12),
        (store1, "Sugar 1kg",              "SUG-001",  "Dry Goods","kg",      120, 150, 10),
        (store1, "Cooking Oil 2L",         "OIL-001",  "Dry Goods","litres",  280, 340, 8),
        (store1, "Eggs (Tray of 30)",      "EGG-001",  "Dairy",    "trays",   320, 400, 5),
        (store1, "Yoghurt 500ml",          "YOG-001",  "Dairy",    "bottles", 95,  130, 10),
        (store1, "Mineral Water 500ml",    "WAT-001",  "Drinks",   "bottles", 25,  40,  30),
        (store2, "Full Cream Milk 1L",     "MILK-001", "Dairy",    "litres",  55,  75,  20),
        (store2, "Bread 700g",             "BRD-001",  "Bakery",   "pieces",  45,  65,  15),
        (store2, "Rice 2kg",               "RCE-001",  "Dry Goods","kg",      180, 230, 10),
        (store2, "Maize Flour 2kg",        "FLR-001",  "Dry Goods","kg",      150, 190, 10),
        (store2, "Tomato Sauce 500g",      "TOM-001",  "Condiments","bottles",85, 120, 8),
        (store2, "Chicken 1kg",            "CHK-001",  "Meat",     "kg",      380, 480, 5),
        (store2, "Mineral Water 500ml",    "WAT-001",  "Drinks",   "bottles", 25,  40,  30),
        (store2, "Orange Juice 500ml",     "OJ-001",   "Drinks",   "bottles", 80,  110, 12),
    ]

    created_products = {}
    for store, name, sku, cat, unit, buy, sell, reorder in products_data:
        existing = Product.query.filter_by(sku=sku).first()
        if existing:
            print(f"Skipping {sku} - already exists")
            continue
        if not existing:
            p = Product(
                store_id      = store.id,
                name          = name,
                sku           = sku,
                category      = cat,
                unit          = unit,
                buying_price  = buy,
                selling_price = sell,
                reorder_level = reorder,
                is_active     = True,
            )
            db.session.add(p)
            created_products[f"{store.id}-{name}"] = p
            print(f"  ✓ Product: {name} (Store: {store.name})")
        else:
            created_products[f"{store.id}-{name}"] = existing

    db.session.flush()

    # ── 4. Create inventory entries for the past 30 days ──────────────────────
    if InventoryEntry.query.count() == 0:
        clerk1 = User.query.filter_by(email="clerk1@stockflow.app").first()
        clerk2 = User.query.filter_by(email="clerk2@stockflow.app").first()

        # Store 1 products
        s1_products = Product.query.filter_by(store_id=store1.id).all()
        # Store 2 products
        s2_products = Product.query.filter_by(store_id=store2.id).all()

        import random
        random.seed(42)  # reproducible data

        entries_created = 0
        today = date.today()

        # Create entries for the last 30 days — a few per week
        for days_ago in range(0, 30, 2):  # every 2 days = ~15 entries per store
            entry_date = today - timedelta(days=days_ago)

            # Store 1 entries
            for product in random.sample(s1_products, min(3, len(s1_products))):
                received  = random.randint(50, 200)
                spoilt    = random.randint(0, max(1, received // 20))
                in_stock  = received - spoilt
                is_paid   = days_ago > 7  # older entries are paid

                entry = InventoryEntry(
                    store_id          = store1.id,
                    product_id        = product.id,
                    clerk_id          = clerk1.id if clerk1 else None,
                    quantity_received = received,
                    quantity_in_stock = in_stock,
                    quantity_spoilt   = spoilt,
                    buying_price      = float(product.buying_price),
                    selling_price     = float(product.selling_price),
                    payment_status    = "paid" if is_paid else "unpaid",
                    entry_date        = entry_date,
                )
                db.session.add(entry)
                entries_created += 1

            # Store 2 entries
            for product in random.sample(s2_products, min(3, len(s2_products))):
                received  = random.randint(40, 180)
                spoilt    = random.randint(0, max(1, received // 20))
                in_stock  = received - spoilt
                is_paid   = days_ago > 7

                entry = InventoryEntry(
                    store_id          = store2.id,
                    product_id        = product.id,
                    clerk_id          = clerk2.id if clerk2 else None,
                    quantity_received = received,
                    quantity_in_stock = in_stock,
                    quantity_spoilt   = spoilt,
                    buying_price      = float(product.buying_price),
                    selling_price     = float(product.selling_price),
                    payment_status    = "paid" if is_paid else "unpaid",
                    entry_date        = entry_date,
                )
                db.session.add(entry)
                entries_created += 1

        print(f"  ✓ Created {entries_created} inventory entries (last 30 days)")

    else:
        print("  ℹ Inventory entries already exist — skipping")

    # ── 5. Create supply requests ─────────────────────────────────────────────
    if SupplyRequest.query.count() == 0:
        clerk1   = User.query.filter_by(email="clerk1@stockflow.app").first()
        clerk2   = User.query.filter_by(email="clerk2@stockflow.app").first()
        admin1   = User.query.filter_by(email="admin1@stockflow.app").first()
        s1_prods = Product.query.filter_by(store_id=store1.id).limit(3).all()
        s2_prods = Product.query.filter_by(store_id=store2.id).limit(2).all()

        from datetime import datetime, timezone

        supply_requests = [
            # Store 1 — pending
            SupplyRequest(
                store_id=store1.id, product_id=s1_prods[0].id,
                clerk_id=clerk1.id if clerk1 else None,
                quantity_requested=150, status="pending",
                reason="Running low — less than 20 units left",
            ),
            # Store 1 — approved
            SupplyRequest(
                store_id=store1.id, product_id=s1_prods[1].id,
                clerk_id=clerk1.id if clerk1 else None,
                admin_id=admin1.id if admin1 else None,
                quantity_requested=100, status="approved",
                reason="Weekly restock needed",
                admin_note="Order placed with supplier — delivery Tuesday",
                resolved_at=datetime.now(timezone.utc),
            ),
            # Store 1 — declined
            SupplyRequest(
                store_id=store1.id, product_id=s1_prods[2].id if len(s1_prods) > 2 else s1_prods[0].id,
                clerk_id=clerk1.id if clerk1 else None,
                admin_id=admin1.id if admin1 else None,
                quantity_requested=500, status="declined",
                reason="Need large stock for upcoming holiday",
                admin_note="Budget not available this month — resubmit next quarter",
                resolved_at=datetime.now(timezone.utc),
            ),
            # Store 2 — pending
            SupplyRequest(
                store_id=store2.id, product_id=s2_prods[0].id,
                clerk_id=clerk2.id if clerk2 else None,
                quantity_requested=80, status="pending",
                reason="Stock running out faster than expected",
            ),
            # Store 2 — pending
            SupplyRequest(
                store_id=store2.id, product_id=s2_prods[1].id if len(s2_prods) > 1 else s2_prods[0].id,
                clerk_id=clerk2.id if clerk2 else None,
                quantity_requested=60, status="pending",
                reason="Low stock alert",
            ),
        ]

        for req in supply_requests:
            db.session.add(req)

        print(f"  ✓ Created {len(supply_requests)} supply requests")
    else:
        print("  ℹ Supply requests already exist — skipping")

    db.session.commit()

    print()
    print("  " + "="*40)
    print("  ✅ Demo data seeded successfully!")
    print()
    print("  Login accounts:")
    print("  ┌─────────────────────────────────┬──────────────┬──────────┐")
    print("  │ Email                           │ Password     │ Role     │")
    print("  ├─────────────────────────────────┼──────────────┼──────────┤")
    print("  │ merchant@stockflow.app          │ ChangeMe123! │ merchant │")
    print("  │ admin1@stockflow.app            │ AdminPass1!  │ admin    │")
    print("  │ admin2@stockflow.app            │ AdminPass1!  │ admin    │")
    print("  │ clerk1@stockflow.app            │ ClerkPass1!  │ clerk    │")
    print("  │ clerk2@stockflow.app            │ ClerkPass1!  │ clerk    │")
    print("  └─────────────────────────────────┴──────────────┴──────────┘")
    print()


# ── Start development server ───────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(
        host  = "0.0.0.0",
        port  = int(os.getenv("PORT", "5000")),
        debug = app.config.get("DEBUG", True),
    )