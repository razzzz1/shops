# tests/test_reports.py
# ──────────────────────
# Tests for app/routes/report_routes.py:
#
#   GET /api/reports/summary
#   GET /api/reports/weekly
#   GET /api/reports/monthly
#   GET /api/reports/annual
#   GET /api/reports/products/<id>
#   GET /api/reports/payment-status
#
# Strategy: seed a known InventoryEntry directly in the DB, then call the
# report endpoints and assert that the aggregated numbers are correct.
# This tests the aggregation logic without relying on the inventory routes.

import pytest
from datetime import date, timedelta
from tests.conftest import auth_headers
from app.models     import InventoryEntry
from app.extensions import db


# ─────────────────────────────────────────────────────────────────────────────
# Helper: seed inventory entries directly
# ─────────────────────────────────────────────────────────────────────────────

def seed_entry(db_session, store_id, product_id, clerk_id,
               received=100, in_stock=90, spoilt=10,
               buying=50.0, selling=80.0,
               payment_status="unpaid", entry_date=None):
    """
    Insert a raw InventoryEntry row for report testing.
    Returns the entry object.
    """
    entry = InventoryEntry(
        store_id          = store_id,
        product_id        = product_id,
        clerk_id          = clerk_id,
        quantity_received = received,
        quantity_in_stock = in_stock,
        quantity_spoilt   = spoilt,
        buying_price      = buying,
        selling_price     = selling,
        payment_status    = payment_status,
        entry_date        = entry_date or date.today(),
    )
    db_session.add(entry)
    db_session.commit()
    return entry


# ═════════════════════════════════════════════════════════════════════════════
# GET /api/reports/summary
# ═════════════════════════════════════════════════════════════════════════════

class TestSummary:

    def test_summary_returns_correct_totals(
        self, client, admin_token, seeded_store, seeded_product, seeded_clerk, db_session
    ):
        """
        Seed two entries (one paid, one unpaid) and assert that summary
        totals are computed correctly.
        """
        seed_entry(db_session,
                   store_id=seeded_store["id"],
                   product_id=seeded_product["id"],
                   clerk_id=seeded_clerk["id"],
                   received=100, in_stock=90, spoilt=10,
                   buying=50.0, selling=80.0,
                   payment_status="paid")

        seed_entry(db_session,
                   store_id=seeded_store["id"],
                   product_id=seeded_product["id"],
                   clerk_id=seeded_clerk["id"],
                   received=50, in_stock=45, spoilt=5,
                   buying=50.0, selling=80.0,
                   payment_status="unpaid")

        response = client.get("/api/reports/summary", headers=auth_headers(admin_token))
        assert response.status_code == 200

        data = response.get_json()
        assert data["total_received"] == 150           # 100 + 50
        assert data["total_in_stock"] == 135           # 90  + 45
        assert data["total_spoilt"]   == 15            # 10  + 5
        assert data["paid_cost"]      == 100 * 50.0    # 5000
        assert data["unpaid_cost"]    == 50  * 50.0    # 2500
        # Revenue potential = in_stock * selling_price
        assert data["revenue_potential"] == (90 + 45) * 80.0   # 10800

    def test_summary_with_no_entries_returns_zeros(
        self, client, admin_token
    ):
        """No entries yet → all totals are 0."""
        response = client.get("/api/reports/summary", headers=auth_headers(admin_token))
        assert response.status_code == 200

        data = response.get_json()
        assert data["total_received"] == 0
        assert data["entry_count"]    == 0

    def test_clerk_can_access_summary(self, client, clerk_token):
        """Clerks are allowed to view the summary → 200."""
        response = client.get("/api/reports/summary", headers=auth_headers(clerk_token))
        assert response.status_code == 200

    def test_unauthenticated_returns_401(self, client):
        """No JWT → 401."""
        response = client.get("/api/reports/summary")
        assert response.status_code == 401


# ═════════════════════════════════════════════════════════════════════════════
# GET /api/reports/weekly
# ═════════════════════════════════════════════════════════════════════════════

class TestWeeklyReport:

    def test_weekly_always_returns_7_data_points(self, client, admin_token):
        """Even with no entries, the weekly report has exactly 7 items."""
        response = client.get("/api/reports/weekly", headers=auth_headers(admin_token))
        assert response.status_code == 200

        data = response.get_json()
        assert data["period"] == "weekly"
        assert len(data["data"]) == 7

    def test_weekly_data_includes_todays_entry(
        self, client, admin_token, seeded_store, seeded_product, seeded_clerk, db_session
    ):
        """An entry dated today should appear in the rolling 7-day report."""
        today = date.today()
        seed_entry(db_session,
                   store_id=seeded_store["id"],
                   product_id=seeded_product["id"],
                   clerk_id=seeded_clerk["id"],
                   received=80, in_stock=75, spoilt=5,
                   entry_date=today)

        response = client.get("/api/reports/weekly", headers=auth_headers(admin_token))
        data = response.get_json()["data"]

        today_row = next((r for r in data if r["date"] == today.isoformat()), None)
        assert today_row is not None
        assert today_row["received"] == 80
        assert today_row["spoilt"]   == 5

    def test_entry_outside_window_not_included(
        self, client, admin_token, seeded_store, seeded_product, seeded_clerk, db_session
    ):
        """An entry from 30 days ago should not appear in the 7-day window."""
        old_date = date.today() - timedelta(days=30)
        seed_entry(db_session,
                   store_id=seeded_store["id"],
                   product_id=seeded_product["id"],
                   clerk_id=seeded_clerk["id"],
                   received=999,
                   entry_date=old_date)

        response = client.get("/api/reports/weekly", headers=auth_headers(admin_token))
        data = response.get_json()["data"]

        # None of the 7 days should contain 999
        total_received = sum(r["received"] for r in data)
        assert total_received == 0   # nothing in the 7-day window

    def test_invalid_start_date_returns_400(self, client, admin_token):
        """Malformed start_date → 400."""
        response = client.get(
            "/api/reports/weekly?start_date=not-a-date",
            headers=auth_headers(admin_token),
        )
        assert response.status_code == 400


# ═════════════════════════════════════════════════════════════════════════════
# GET /api/reports/monthly
# ═════════════════════════════════════════════════════════════════════════════

class TestMonthlyReport:

    def test_monthly_returns_correct_day_count(self, client, admin_token):
        """June has 30 days — monthly report should return 30 data points."""
        response = client.get(
            "/api/reports/monthly?year=2024&month=6",
            headers=auth_headers(admin_token),
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["year"]       == 2024
        assert data["month"]      == 6
        assert len(data["data"])  == 30

    def test_january_has_31_days(self, client, admin_token):
        """January has 31 days."""
        response = client.get(
            "/api/reports/monthly?year=2024&month=1",
            headers=auth_headers(admin_token),
        )
        assert len(response.get_json()["data"]) == 31

    def test_invalid_month_returns_400(self, client, admin_token):
        """month=13 is out of range → 400."""
        response = client.get(
            "/api/reports/monthly?year=2024&month=13",
            headers=auth_headers(admin_token),
        )
        assert response.status_code == 400

    def test_monthly_aggregates_entry_correctly(
        self, client, admin_token, seeded_store, seeded_product, seeded_clerk, db_session
    ):
        """An entry on June 15 should appear under the June 15 row."""
        seed_entry(db_session,
                   store_id=seeded_store["id"],
                   product_id=seeded_product["id"],
                   clerk_id=seeded_clerk["id"],
                   received=60, in_stock=55, spoilt=5,
                   entry_date=date(2024, 6, 15))

        response = client.get(
            "/api/reports/monthly?year=2024&month=6",
            headers=auth_headers(admin_token),
        )
        data = response.get_json()["data"]

        june_15 = next((r for r in data if r["date"] == "2024-06-15"), None)
        assert june_15 is not None
        assert june_15["received"] == 60


# ═════════════════════════════════════════════════════════════════════════════
# GET /api/reports/annual
# ═════════════════════════════════════════════════════════════════════════════

class TestAnnualReport:

    def test_annual_always_returns_12_months(self, client, admin_token):
        """Even with no data, annual report returns 12 items."""
        response = client.get(
            "/api/reports/annual?year=2024",
            headers=auth_headers(admin_token),
        )
        assert response.status_code == 200

        data = response.get_json()
        assert data["year"]      == 2024
        assert len(data["data"]) == 12

    def test_annual_month_labels_are_correct(self, client, admin_token):
        """The 12 month labels should be Jan through Dec."""
        response = client.get(
            "/api/reports/annual?year=2024",
            headers=auth_headers(admin_token),
        )
        labels = [row["label"] for row in response.get_json()["data"]]
        assert labels == [
            "Jan", "Feb", "Mar", "Apr", "May", "Jun",
            "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
        ]

    def test_annual_aggregates_march_entry(
        self, client, admin_token, seeded_store, seeded_product, seeded_clerk, db_session
    ):
        """An entry in March 2024 should appear under month=3 (label='Mar')."""
        seed_entry(db_session,
                   store_id=seeded_store["id"],
                   product_id=seeded_product["id"],
                   clerk_id=seeded_clerk["id"],
                   received=200,
                   entry_date=date(2024, 3, 10))

        response = client.get(
            "/api/reports/annual?year=2024",
            headers=auth_headers(admin_token),
        )
        data = response.get_json()["data"]

        march_row = next((r for r in data if r["month"] == 3), None)
        assert march_row is not None
        assert march_row["received"] == 200
        assert march_row["label"]    == "Mar"


# ═════════════════════════════════════════════════════════════════════════════
# GET /api/reports/products/<id>
# ═════════════════════════════════════════════════════════════════════════════

class TestProductReport:

    def test_product_report_returns_entries_and_stats(
        self, client, admin_token, seeded_store, seeded_product, seeded_clerk, db_session
    ):
        """Product report includes all entries and computed summary stats."""
        # Seed two entries for the same product
        seed_entry(db_session,
                   store_id=seeded_store["id"],
                   product_id=seeded_product["id"],
                   clerk_id=seeded_clerk["id"],
                   received=100, spoilt=10,
                   entry_date=date(2024, 1, 1))

        seed_entry(db_session,
                   store_id=seeded_store["id"],
                   product_id=seeded_product["id"],
                   clerk_id=seeded_clerk["id"],
                   received=200, spoilt=20,
                   entry_date=date(2024, 2, 1))

        response = client.get(
            f"/api/reports/products/{seeded_product['id']}",
            headers=auth_headers(admin_token),
        )
        assert response.status_code == 200

        data = response.get_json()
        assert data["total_received"] == 300          # 100 + 200
        assert data["total_spoilt"]   == 30           # 10  + 20
        assert data["spoil_rate_pct"] == 10.0         # 30/300 * 100
        assert data["entry_count"]    == 2
        assert len(data["entries"])   == 2

    def test_clerk_cannot_access_product_report(
        self, client, clerk_token, seeded_product
    ):
        """Product report is admin/merchant only → 403 for clerk."""
        response = client.get(
            f"/api/reports/products/{seeded_product['id']}",
            headers=auth_headers(clerk_token),
        )
        assert response.status_code == 403

    def test_nonexistent_product_returns_404(self, client, admin_token):
        """Product id not found → 404."""
        response = client.get(
            "/api/reports/products/999999",
            headers=auth_headers(admin_token),
        )
        assert response.status_code == 404


# ═════════════════════════════════════════════════════════════════════════════
# GET /api/reports/payment-status
# ═════════════════════════════════════════════════════════════════════════════

class TestPaymentStatusReport:

    def test_payment_report_separates_paid_and_unpaid(
        self, client, admin_token, seeded_store, seeded_product, seeded_clerk, db_session
    ):
        """
        Seed one paid and two unpaid entries; verify they are split correctly
        and that cost totals match.
        """
        seed_entry(db_session,
                   store_id=seeded_store["id"],
                   product_id=seeded_product["id"],
                   clerk_id=seeded_clerk["id"],
                   received=100, buying=50.0,
                   payment_status="paid")

        seed_entry(db_session,
                   store_id=seeded_store["id"],
                   product_id=seeded_product["id"],
                   clerk_id=seeded_clerk["id"],
                   received=50, buying=50.0,
                   payment_status="unpaid")

        seed_entry(db_session,
                   store_id=seeded_store["id"],
                   product_id=seeded_product["id"],
                   clerk_id=seeded_clerk["id"],
                   received=30, buying=50.0,
                   payment_status="unpaid")

        response = client.get(
            "/api/reports/payment-status",
            headers=auth_headers(admin_token),
        )
        assert response.status_code == 200

        data = response.get_json()

        # Paid section
        assert data["paid"]["count"]      == 1
        assert data["paid"]["total_cost"] == 100 * 50.0     # 5000

        # Unpaid section
        assert data["unpaid"]["count"]      == 2
        assert data["unpaid"]["total_cost"] == (50 + 30) * 50.0    # 4000

    def test_clerk_cannot_access_payment_report(self, client, clerk_token):
        """Clerk role → 403."""
        response = client.get(
            "/api/reports/payment-status",
            headers=auth_headers(clerk_token),
        )
        assert response.status_code == 403

    def test_empty_store_returns_zero_totals(self, client, admin_token):
        """No entries at all → both groups have count=0 and total_cost=0."""
        response = client.get(
            "/api/reports/payment-status",
            headers=auth_headers(admin_token),
        )
        assert response.status_code == 200

        data = response.get_json()
        assert data["paid"]["count"]        == 0
        assert data["paid"]["total_cost"]   == 0
        assert data["unpaid"]["count"]      == 0
        assert data["unpaid"]["total_cost"] == 0