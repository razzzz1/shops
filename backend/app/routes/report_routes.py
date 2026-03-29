# app/routes/report_routes.py
# ────────────────────────────
# Reporting blueprint — aggregates InventoryEntry data for charts and tables.
#
#   GET /api/reports/summary           overall KPIs for a store + date range
#   GET /api/reports/weekly            7-day rolling data, grouped by day
#   GET /api/reports/monthly           one month's data, grouped by day
#   GET /api/reports/annual            one year's data, grouped by month
#   GET /api/reports/products/<id>     single product performance over time
#   GET /api/reports/payment-status    paid vs unpaid breakdown with totals
#
# All report endpoints return data that the React frontend feeds directly
# into Recharts — the structure is designed to match Recharts' data prop
# format (a list of objects with consistent keys).

from calendar import monthrange
from datetime import date, timedelta

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required

from app.models import InventoryEntry, Product
from app.utils  import role_required

report_bp = Blueprint("reports", __name__)


# ─────────────────────────────────────────────────────────────────────────────
# Internal helper
# ─────────────────────────────────────────────────────────────────────────────

def _resolve_store_id(current_user, args) -> int | None:
    """
    Return the effective store_id for a report query.

    Admin and clerk are always locked to their own store.
    Merchant can specify any store via ?store_id=; if omitted we return None
    (meaning the route handler will query across all stores).
    """
    if current_user.role in ("admin", "clerk"):
        return current_user.store_id
    return args.get("store_id", type=int)


def _parse_date(date_str: str, param_name: str):
    """
    Parse a YYYY-MM-DD string into a date object.
    Returns (date_obj, None) on success or (None, error_response) on failure.
    """
    try:
        return date.fromisoformat(date_str), None
    except ValueError:
        return None, (
            jsonify({"message": f"Invalid {param_name}. Use YYYY-MM-DD format."}),
            400,
        )


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/reports/summary
# ─────────────────────────────────────────────────────────────────────────────

@report_bp.route("/summary", methods=["GET"])
@jwt_required()
@role_required("merchant", "admin", "clerk")
def summary(current_user):
    """
    High-level KPI snapshot for a store and optional date range.

    Query params
    ────────────
    ?store_id=1             merchant: target store (omit = all stores)
    ?from_date=2024-01-01   start of date range
    ?to_date=2024-12-31     end of date range

    Response shape
    ──────────────
    {
        "store_id":          1,
        "entry_count":       120,
        "total_received":    5000,
        "total_in_stock":    4700,
        "total_spoilt":      300,
        "revenue_potential": 352500.00,
        "paid_cost":         180000.00,
        "unpaid_cost":        45000.00
    }
    """
    store_id = _resolve_store_id(current_user, request.args)

    query = InventoryEntry.query
    if store_id:
        query = query.filter_by(store_id=store_id)

    # Apply optional date range
    if request.args.get("from_date"):
        d, err = _parse_date(request.args["from_date"], "from_date")
        if err:
            return err
        query = query.filter(InventoryEntry.entry_date >= d)

    if request.args.get("to_date"):
        d, err = _parse_date(request.args["to_date"], "to_date")
        if err:
            return err
        query = query.filter(InventoryEntry.entry_date <= d)

    entries = query.all()

    # ── Compute aggregates in Python ──────────────────────────────────────────
    # For dataset sizes typical in an SME (hundreds to low thousands of rows),
    # Python-side aggregation is simpler to read and test than raw SQL GROUP BY.
    total_received    = sum(e.quantity_received for e in entries)
    total_in_stock    = sum(e.quantity_in_stock  for e in entries)
    total_spoilt      = sum(e.quantity_spoilt    for e in entries)
    revenue_potential = sum(e.total_revenue_potential for e in entries)
    paid_cost         = sum(e.total_cost for e in entries if e.payment_status == "paid")
    unpaid_cost       = sum(e.total_cost for e in entries if e.payment_status == "unpaid")

    return jsonify({
        "store_id":          store_id,
        "entry_count":       len(entries),
        "total_received":    total_received,
        "total_in_stock":    total_in_stock,
        "total_spoilt":      total_spoilt,
        "revenue_potential": round(revenue_potential, 2),
        "paid_cost":         round(paid_cost, 2),
        "unpaid_cost":       round(unpaid_cost, 2),
    }), 200


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/reports/weekly
# ─────────────────────────────────────────────────────────────────────────────

@report_bp.route("/weekly", methods=["GET"])
@jwt_required()
@role_required("merchant", "admin", "clerk")
def weekly_report(current_user):
    """
    Return per-day aggregates for a 7-day window.

    Query params
    ────────────
    ?start_date=2024-06-01   first day of the window (default: 6 days ago)
    ?store_id=1              merchant only

    Response — always 7 data points (zero-filled for days with no entries)
    -----------------------------------------------------------------------
    {
        "period":     "weekly",
        "start":      "2024-06-01",
        "end":        "2024-06-07",
        "data": [
            {
                "date":        "2024-06-01",
                "received":    80,
                "in_stock":    75,
                "spoilt":      5,
                "paid_cost":   4400.00,
                "unpaid_cost": 0.00
            },
            ...  (7 items total)
        ]
    }
    """
    store_id = _resolve_store_id(current_user, request.args)

    # Default: rolling 7 days ending today
    if request.args.get("start_date"):
        start, err = _parse_date(request.args["start_date"], "start_date")
        if err:
            return err
    else:
        start = date.today() - timedelta(days=6)

    end = start + timedelta(days=6)

    # ── Pre-fill all 7 days with zeros ────────────────────────────────────────
    # This ensures the chart always has 7 data points even if some days have
    # no entries — avoids gaps in the line/bar chart.
    daily = {}
    for i in range(7):
        d = (start + timedelta(days=i)).isoformat()
        daily[d] = {
            "date":        d,
            "received":    0,
            "in_stock":    0,
            "spoilt":      0,
            "paid_cost":   0.0,
            "unpaid_cost": 0.0,
        }

    # ── Query and aggregate ───────────────────────────────────────────────────
    query = InventoryEntry.query.filter(
        InventoryEntry.entry_date >= start,
        InventoryEntry.entry_date <= end,
    )
    if store_id:
        query = query.filter_by(store_id=store_id)

    for entry in query.all():
        key = entry.entry_date.isoformat()
        if key not in daily:
            continue
        daily[key]["received"] += entry.quantity_received
        daily[key]["in_stock"] += entry.quantity_in_stock
        daily[key]["spoilt"]   += entry.quantity_spoilt
        if entry.payment_status == "paid":
            daily[key]["paid_cost"]   += entry.total_cost
        else:
            daily[key]["unpaid_cost"] += entry.total_cost

    # Round costs
    for row in daily.values():
        row["paid_cost"]   = round(row["paid_cost"],   2)
        row["unpaid_cost"] = round(row["unpaid_cost"], 2)

    return jsonify({
        "period": "weekly",
        "start":  start.isoformat(),
        "end":    end.isoformat(),
        "data":   list(daily.values()),
    }), 200


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/reports/monthly
# ─────────────────────────────────────────────────────────────────────────────

@report_bp.route("/monthly", methods=["GET"])
@jwt_required()
@role_required("merchant", "admin", "clerk")
def monthly_report(current_user):
    """
    Return per-day aggregates for one calendar month.

    Query params
    ────────────
    ?year=2024    (default: current year)
    ?month=6      (default: current month)
    ?store_id=1   merchant only

    Response — one data point per day of the month (28–31 items).
    """
    store_id  = _resolve_store_id(current_user, request.args)
    today     = date.today()
    year      = request.args.get("year",  type=int, default=today.year)
    month     = request.args.get("month", type=int, default=today.month)

    if not (1 <= month <= 12):
        return jsonify({"message": "month must be between 1 and 12."}), 400

    _, days_in_month = monthrange(year, month)
    start = date(year, month, 1)
    end   = date(year, month, days_in_month)

    # Pre-fill every day of the month with zeros
    daily = {}
    for i in range(days_in_month):
        d = (start + timedelta(days=i)).isoformat()
        daily[d] = {
            "date": d, "received": 0, "in_stock": 0,
            "spoilt": 0, "paid_cost": 0.0, "unpaid_cost": 0.0,
        }

    query = InventoryEntry.query.filter(
        InventoryEntry.entry_date >= start,
        InventoryEntry.entry_date <= end,
    )
    if store_id:
        query = query.filter_by(store_id=store_id)

    for entry in query.all():
        key = entry.entry_date.isoformat()
        if key not in daily:
            continue
        daily[key]["received"] += entry.quantity_received
        daily[key]["in_stock"] += entry.quantity_in_stock
        daily[key]["spoilt"]   += entry.quantity_spoilt
        if entry.payment_status == "paid":
            daily[key]["paid_cost"]   += entry.total_cost
        else:
            daily[key]["unpaid_cost"] += entry.total_cost

    for row in daily.values():
        row["paid_cost"]   = round(row["paid_cost"],   2)
        row["unpaid_cost"] = round(row["unpaid_cost"], 2)

    return jsonify({
        "period": "monthly",
        "year":   year,
        "month":  month,
        "data":   list(daily.values()),
    }), 200


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/reports/annual
# ─────────────────────────────────────────────────────────────────────────────

@report_bp.route("/annual", methods=["GET"])
@jwt_required()
@role_required("merchant", "admin", "clerk")
def annual_report(current_user):
    """
    Return per-month aggregates for a full calendar year.

    Query params
    ────────────
    ?year=2024   (default: current year)
    ?store_id=1  merchant only

    Response — always 12 data points (one per month, zero-filled).
    This feeds directly into Recharts BarChart / LineChart.
    """
    store_id = _resolve_store_id(current_user, request.args)
    year     = request.args.get("year", type=int, default=date.today().year)

    start = date(year, 1,  1)
    end   = date(year, 12, 31)

    # Month labels used as the X-axis tick in the chart
    MONTH_LABELS = [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
    ]

    # Pre-fill all 12 months with zeros
    monthly = {
        i: {
            "month":       i,
            "label":       MONTH_LABELS[i - 1],
            "received":    0,
            "in_stock":    0,
            "spoilt":      0,
            "paid_cost":   0.0,
            "unpaid_cost": 0.0,
        }
        for i in range(1, 13)
    }

    query = InventoryEntry.query.filter(
        InventoryEntry.entry_date >= start,
        InventoryEntry.entry_date <= end,
    )
    if store_id:
        query = query.filter_by(store_id=store_id)

    for entry in query.all():
        m = entry.entry_date.month
        monthly[m]["received"] += entry.quantity_received
        monthly[m]["in_stock"] += entry.quantity_in_stock
        monthly[m]["spoilt"]   += entry.quantity_spoilt
        if entry.payment_status == "paid":
            monthly[m]["paid_cost"]   += entry.total_cost
        else:
            monthly[m]["unpaid_cost"] += entry.total_cost

    for row in monthly.values():
        row["paid_cost"]   = round(row["paid_cost"],   2)
        row["unpaid_cost"] = round(row["unpaid_cost"], 2)

    return jsonify({
        "period": "annual",
        "year":   year,
        "data":   list(monthly.values()),
    }), 200


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/reports/products/<id>
# ─────────────────────────────────────────────────────────────────────────────

@report_bp.route("/products/<int:product_id>", methods=["GET"])
@jwt_required()
@role_required("merchant", "admin")
def product_report(current_user, product_id: int):
    """
    Full performance history for a single product.

    Returns every InventoryEntry for the product in date order, plus
    computed summary stats: total received, total spoilt, spoil rate %.

    Used by the merchant's "drill into individual product performance" view.
    """
    product = Product.query.get_or_404(product_id, description="Product not found.")

    # Non-merchant admins can only see products in their own store
    if current_user.role == "admin" and product.store_id != current_user.store_id:
        return jsonify({"message": "Access denied."}), 403

    entries = (
        InventoryEntry.query
        .filter_by(product_id=product_id)
        .order_by(InventoryEntry.entry_date)
        .all()
    )

    total_received = sum(e.quantity_received for e in entries)
    total_spoilt   = sum(e.quantity_spoilt   for e in entries)
    spoil_rate_pct = (
        round(total_spoilt / total_received * 100, 2)
        if total_received else 0
    )
    total_revenue_potential = sum(e.total_revenue_potential for e in entries)

    return jsonify({
        "product":               product.to_dict(),
        "total_received":        total_received,
        "total_spoilt":          total_spoilt,
        "spoil_rate_pct":        spoil_rate_pct,
        "total_revenue_potential": round(total_revenue_potential, 2),
        "entry_count":           len(entries),
        # Embed entries without repeating the product sub-object on every row
        "entries": [e.to_dict(include_product=False) for e in entries],
    }), 200


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/reports/payment-status
# ─────────────────────────────────────────────────────────────────────────────

@report_bp.route("/payment-status", methods=["GET"])
@jwt_required()
@role_required("merchant", "admin")
def payment_status_report(current_user):
    """
    Return all inventory entries split into "paid" and "unpaid" groups,
    with running totals for each.

    Used by the admin Payment Tracker page and merchant's store payment view.
    The two groups are returned separately so the frontend can render them
    in clearly separated sections as required by the spec.

    Query params
    ────────────
    ?store_id=1   merchant only
    """
    store_id = _resolve_store_id(current_user, request.args)

    query = InventoryEntry.query
    if store_id:
        query = query.filter_by(store_id=store_id)

    # Fetch both groups with a single DB round-trip using Python filtering
    all_entries = query.order_by(InventoryEntry.entry_date.desc()).all()

    paid_entries   = [e for e in all_entries if e.payment_status == "paid"]
    unpaid_entries = [e for e in all_entries if e.payment_status == "unpaid"]

    paid_total   = sum(e.total_cost for e in paid_entries)
    unpaid_total = sum(e.total_cost for e in unpaid_entries)

    return jsonify({
        "paid": {
            "count":      len(paid_entries),
            "total_cost": round(paid_total, 2),
            "entries":    [e.to_dict() for e in paid_entries],
        },
        "unpaid": {
            "count":      len(unpaid_entries),
            "total_cost": round(unpaid_total, 2),
            "entries":    [e.to_dict() for e in unpaid_entries],
        },
    }), 200