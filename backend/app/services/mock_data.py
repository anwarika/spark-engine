from __future__ import annotations

import math
import random
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Mapping, Sequence


SUPPORTED_PROFILES = ("ecommerce", "saas", "marketing", "finance", "sales")
SUPPORTED_SCALES = ("small", "medium", "large", "xl")


@dataclass(frozen=True)
class MockSpec:
    profile: str = "ecommerce"
    scale: str = "small"  # small | medium | large | xl
    seed: int = 1
    days: int = 180


def _clamp_int(v: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, int(v)))


def _iso(d: date) -> str:
    return d.isoformat()


def _month_key(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def _norm_profile(profile: str) -> str:
    p = (profile or "ecommerce").lower().strip()
    return p if p in SUPPORTED_PROFILES else "ecommerce"


def _norm_scale(scale: str) -> str:
    s = (scale or "small").lower().strip()
    return s if s in SUPPORTED_SCALES else "small"


def _rng(seed: int) -> random.Random:
    return random.Random(int(seed))


def _pick(rng: random.Random, seq: Sequence[Any]) -> Any:
    return seq[rng.randrange(0, len(seq))]


def _wchoice(rng: random.Random, values: Sequence[Any], weights: Sequence[float]) -> Any:
    return rng.choices(list(values), weights=list(weights), k=1)[0]


def _sizes(profile: str, scale: str) -> Dict[str, int]:
    """
    Profile-specific scaling: keep worst-case row counts bounded for local dev.
    """
    profile = _norm_profile(profile)
    scale = _norm_scale(scale)

    if profile == "ecommerce":
        if scale == "small":
            return {"users": 1_000, "products": 250, "orders": 5_000, "tasks": 200}
        if scale == "medium":
            return {"users": 10_000, "products": 1_000, "orders": 50_000, "tasks": 1_000}
        if scale == "large":
            return {"users": 50_000, "products": 5_000, "orders": 250_000, "tasks": 5_000}
        return {"users": 200_000, "products": 20_000, "orders": 1_000_000, "tasks": 20_000}

    if profile == "saas":
        if scale == "small":
            return {"accounts": 1_000, "users": 4_000, "subscriptions": 1_100, "invoices": 6_000, "events": 50_000}
        if scale == "medium":
            return {"accounts": 10_000, "users": 40_000, "subscriptions": 11_000, "invoices": 60_000, "events": 300_000}
        if scale == "large":
            return {"accounts": 50_000, "users": 200_000, "subscriptions": 55_000, "invoices": 300_000, "events": 1_000_000}
        return {"accounts": 200_000, "users": 800_000, "subscriptions": 220_000, "invoices": 1_200_000, "events": 2_000_000}

    if profile == "marketing":
        if scale == "small":
            return {"campaigns": 200, "ad_groups": 600, "ads": 2_000, "leads": 5_000, "touchpoints": 20_000}
        if scale == "medium":
            return {"campaigns": 1_000, "ad_groups": 3_000, "ads": 10_000, "leads": 50_000, "touchpoints": 250_000}
        if scale == "large":
            return {"campaigns": 3_000, "ad_groups": 10_000, "ads": 30_000, "leads": 200_000, "touchpoints": 1_000_000}
        return {"campaigns": 7_000, "ad_groups": 25_000, "ads": 80_000, "leads": 700_000, "touchpoints": 2_500_000}

    if profile == "finance":
        if scale == "small":
            return {"coa_accounts": 80, "vendors": 400, "customers": 500, "transactions": 30_000, "invoices": 8_000}
        if scale == "medium":
            return {"coa_accounts": 120, "vendors": 2_000, "customers": 3_000, "transactions": 250_000, "invoices": 60_000}
        if scale == "large":
            return {"coa_accounts": 160, "vendors": 8_000, "customers": 12_000, "transactions": 1_000_000, "invoices": 250_000}
        return {"coa_accounts": 220, "vendors": 25_000, "customers": 35_000, "transactions": 2_000_000, "invoices": 700_000}

    # sales
    if scale == "small":
        return {"accounts": 2_000, "contacts": 6_000, "opps": 6_000, "activities": 30_000, "reps": 40}
    if scale == "medium":
        return {"accounts": 20_000, "contacts": 60_000, "opps": 60_000, "activities": 300_000, "reps": 250}
    if scale == "large":
        return {"accounts": 80_000, "contacts": 240_000, "opps": 250_000, "activities": 1_200_000, "reps": 900}
    return {"accounts": 250_000, "contacts": 800_000, "opps": 800_000, "activities": 3_000_000, "reps": 2_500}


def _base_meta(spec: MockSpec, counts: Mapping[str, int], schema_version: int) -> Dict[str, Any]:
    return {
        "profile": _norm_profile(spec.profile),
        "scale": _norm_scale(spec.scale),
        "seed": int(spec.seed),
        "days": _clamp_int(spec.days, 7, 3650),
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "counts": dict(counts),
        "schema_version": int(schema_version),
    }


def generate_mock_dataset(spec: MockSpec) -> Dict[str, Any]:
    """
    Generate a deterministic, dashboard-friendly dataset for BI dashboards.

    Profiles:
    - ecommerce: products/orders/order_items + traffic metrics
    - saas: accounts/subscriptions/invoices/payments/events + mrr/retention metrics
    - marketing: campaigns/spend/touchpoints/leads + attribution metrics
    - finance: GL/transactions/invoices/vendors + monthly P&L rollups
    - sales: accounts/opportunities/activities + pipeline/quota metrics
    """
    profile = _norm_profile(spec.profile)
    if profile == "ecommerce":
        return _generate_ecommerce(spec)
    if profile == "saas":
        return _generate_saas(spec)
    if profile == "marketing":
        return _generate_marketing(spec)
    if profile == "finance":
        return _generate_finance(spec)
    if profile == "sales":
        return _generate_sales(spec)
    return _generate_ecommerce(spec)


def _generate_ecommerce(spec: MockSpec) -> Dict[str, Any]:
    sizes = _sizes("ecommerce", spec.scale)
    days = _clamp_int(spec.days, 7, 3650)
    rng = _rng(spec.seed)

    regions = ["North", "South", "East", "West", "Central"]
    channels = ["web", "mobile", "partner", "retail"]
    order_statuses = ["pending", "processing", "shipped", "delivered", "cancelled", "refunded"]
    priorities = ["low", "medium", "high"]
    task_statuses = ["pending", "in_progress", "blocked", "completed"]
    roles = ["user", "admin", "analyst", "moderator"]
    user_statuses = ["active", "inactive"]

    categories = ["Electronics", "Accessories", "Furniture", "Home", "Outdoors", "Apparel", "Beauty", "Grocery"]
    first_names = [
        "Alex", "Sam", "Jordan", "Taylor", "Casey", "Morgan", "Riley", "Avery", "Jamie", "Cameron",
        "Drew", "Reese", "Parker", "Quinn", "Hayden", "Rowan", "Skyler", "Logan", "Emerson", "Finley",
    ]
    last_names = [
        "Johnson", "Smith", "Brown", "Davis", "Miller", "Wilson", "Moore", "Taylor", "Anderson", "Thomas",
        "Jackson", "White", "Harris", "Martin", "Thompson", "Garcia", "Martinez", "Robinson", "Clark", "Lewis",
    ]
    adjectives = ["Pro", "Ultra", "Lite", "Max", "Prime", "Smart", "Essential", "Classic", "Plus", "Air", "Eco", "Flex"]
    product_nouns = [
        "Laptop", "Mouse", "Keyboard", "Monitor", "Headphones", "Webcam", "Chair", "Desk Lamp", "Backpack",
        "Water Bottle", "Sneakers", "Jacket", "Blender", "Coffee Maker", "Skincare Set", "Yoga Mat",
        "Camping Tent", "Smartwatch", "Phone Case", "USB-C Cable",
    ]

    today = date.today()
    start = today - timedelta(days=days - 1)
    all_days = [start + timedelta(days=i) for i in range(days)]

    users: List[Dict[str, Any]] = []
    for user_id in range(1, sizes["users"] + 1):
        fn = _pick(rng, first_names)
        ln = _pick(rng, last_names)
        name = f"{fn} {ln}"
        email = f"{fn.lower()}.{ln.lower()}{user_id}@example.com"
        joined = start - timedelta(days=rng.randint(0, 365))
        users.append(
            {
                "id": user_id,
                "name": name,
                "email": email,
                "role": _wchoice(rng, roles, [0.86, 0.04, 0.08, 0.02]),
                "status": _wchoice(rng, user_statuses, [0.93, 0.07]),
                "joined": _iso(joined),
                "region": _wchoice(rng, regions, [0.22, 0.20, 0.18, 0.18, 0.22]),
            }
        )

    products: List[Dict[str, Any]] = []
    for product_id in range(1, sizes["products"] + 1):
        category = _pick(rng, categories)
        name = f"{_pick(rng, product_nouns)} {_pick(rng, adjectives)}"
        base_price = {
            "Electronics": rng.uniform(120, 1800),
            "Accessories": rng.uniform(8, 180),
            "Furniture": rng.uniform(45, 900),
            "Home": rng.uniform(10, 250),
            "Outdoors": rng.uniform(15, 600),
            "Apparel": rng.uniform(12, 220),
            "Beauty": rng.uniform(8, 160),
            "Grocery": rng.uniform(2, 60),
        }.get(category, rng.uniform(10, 250))
        price = round(base_price * (1.0 + rng.uniform(-0.08, 0.12)), 2)
        stock = max(0, int(rng.gauss(120, 90)))
        rating = round(min(5.0, max(2.8, rng.gauss(4.35, 0.35))), 1)
        status = "in_stock" if stock > 0 else "out_of_stock"
        if 0 < stock < 15:
            status = "low_stock"
        products.append(
            {
                "id": product_id,
                "name": name,
                "category": category,
                "price": price,
                "stock": stock,
                "rating": rating,
                "status": status,
            }
        )

    # Orders distributed across the date range with mild seasonality
    day_weights: List[float] = []
    for i, d in enumerate(all_days):
        weekly = 1.0 + 0.18 * math.sin((2.0 * math.pi * (d.weekday())) / 7.0)
        trend = 0.85 + (i / max(1, days - 1)) * 0.35
        month_boost = 1.0 + (0.08 if d.month in (11, 12) else 0.0)
        day_weights.append(max(0.1, weekly * trend * month_boost))
    total_w = sum(day_weights)
    day_probs = [w / total_w for w in day_weights]

    sampled_days = rng.choices(all_days, weights=day_probs, k=sizes["orders"])

    def _pick_user() -> Dict[str, Any]:
        return users[rng.randrange(0, len(users))]

    def _pick_product() -> Dict[str, Any]:
        return products[rng.randrange(0, len(products))]

    orders: List[Dict[str, Any]] = []
    order_items: List[Dict[str, Any]] = []
    sales: List[Dict[str, Any]] = []  # legacy-ish: one row per order

    for idx in range(1, sizes["orders"] + 1):
        d = sampled_days[idx - 1]
        u = _pick_user()
        age_days = (today - d).days
        if age_days < 7:
            status = _wchoice(rng, order_statuses, [0.20, 0.28, 0.20, 0.18, 0.08, 0.06])
        else:
            status = _wchoice(rng, order_statuses, [0.06, 0.10, 0.18, 0.56, 0.05, 0.05])

        items_count = _wchoice(rng, [1, 2, 3, 4, 5], [0.42, 0.28, 0.16, 0.09, 0.05])
        region = u["region"]
        channel = _wchoice(rng, channels, [0.55, 0.30, 0.08, 0.07])

        order_total = 0.0
        for _ in range(int(items_count)):
            p = _pick_product()
            qty = _wchoice(rng, [1, 2, 3, 4], [0.72, 0.18, 0.07, 0.03])
            unit_price = float(p["price"])
            promo = _wchoice(rng, [0.0, 0.05, 0.10, 0.15], [0.70, 0.18, 0.09, 0.03])
            effective_price = round(unit_price * (1.0 - float(promo)), 2)
            revenue = round(effective_price * int(qty), 2)
            order_total += revenue
            order_items.append(
                {
                    "order_id": idx,  # join key to orders.order_index
                    "product_id": p["id"],
                    "product": p["name"],
                    "category": p["category"],
                    "quantity": int(qty),
                    "unit_price": effective_price,
                    "revenue": revenue,
                }
            )

        order_total = round(order_total, 2)
        orders.append(
            {
                "id": 1_000_000 + idx,
                "order_index": idx,
                "customer_id": u["id"],
                "customer": u["name"],
                "items": int(items_count),
                "total": order_total,
                "status": status,
                "date": _iso(d),
                "region": region,
                "channel": channel,
            }
        )
        sales.append(
            {
                "id": idx,
                "date": _iso(d),
                "product": order_items[-1]["product"],
                "quantity": int(items_count),
                "revenue": order_total,
                "region": region,
            }
        )

    tasks: List[Dict[str, Any]] = []
    for task_id in range(1, sizes["tasks"] + 1):
        assignee = _pick_user()
        due = today + timedelta(days=rng.randint(-30, 45))
        tasks.append(
            {
                "id": task_id,
                "title": f"{_pick(rng, ['Update', 'Fix', 'Design', 'Review', 'Ship', 'Optimize', 'Investigate'])} "
                f"{_pick(rng, ['dashboard', 'pipeline', 'alerting', 'API', 'UI', 'report', 'tests', 'caching'])}",
                "assignee": assignee["name"],
                "assignee_id": assignee["id"],
                "status": _wchoice(rng, task_statuses, [0.28, 0.34, 0.08, 0.30]),
                "priority": _wchoice(rng, priorities, [0.36, 0.44, 0.20]),
                "due": _iso(due),
            }
        )

    revenue_by_day: Dict[str, float] = {}
    orders_by_day: Dict[str, int] = {}
    delivered_by_day: Dict[str, int] = {}
    for o in orders:
        ds = o["date"]
        orders_by_day[ds] = orders_by_day.get(ds, 0) + 1
        revenue_by_day[ds] = revenue_by_day.get(ds, 0.0) + float(o["total"])
        if o["status"] == "delivered":
            delivered_by_day[ds] = delivered_by_day.get(ds, 0) + 1

    metrics: List[Dict[str, Any]] = []
    for d in all_days:
        ds = _iso(d)
        day_orders = orders_by_day.get(ds, 0)
        day_revenue = round(revenue_by_day.get(ds, 0.0), 2)
        base_sessions = int(max(50, rng.gauss(900, 140)))
        sessions = int(base_sessions + day_orders * rng.uniform(0.9, 1.4))
        pageviews = int(sessions * rng.uniform(1.6, 2.9))
        users_count = int(sessions * rng.uniform(0.62, 0.88))
        conversions = int(max(0, delivered_by_day.get(ds, int(day_orders * rng.uniform(0.45, 0.70)))))
        metrics.append(
            {
                "date": ds,
                "pageviews": pageviews,
                "users": users_count,
                "revenue": day_revenue,
                "conversions": conversions,
                "orders": day_orders,
                "sessions": sessions,
            }
        )

    total_revenue = round(sum(float(o["total"]) for o in orders), 2)
    total_orders = len(orders)
    active_users = sum(1 for u in users if u["status"] == "active")
    avg_order_value = round(total_revenue / max(1, total_orders), 2)

    revenue_by_product: Dict[str, float] = {}
    for item in order_items:
        name = item["product"]
        revenue_by_product[name] = revenue_by_product.get(name, 0.0) + float(item["revenue"])
    top_product = max(revenue_by_product.items(), key=lambda kv: kv[1])[0] if revenue_by_product else ""

    counts = {
        "users": len(users),
        "products": len(products),
        "orders": len(orders),
        "order_items": len(order_items),
        "tasks": len(tasks),
        "metrics": len(metrics),
    }
    return {
        "meta": _base_meta(MockSpec(profile="ecommerce", scale=spec.scale, seed=spec.seed, days=days), counts, 2),
        "products": products,
        "users": users,
        "sales": sales,
        "tasks": tasks,
        "metrics": metrics,
        "orders": orders,
        "order_items": order_items,
        "summary": {
            "total_revenue": total_revenue,
            "total_orders": total_orders,
            "active_users": active_users,
            "avg_order_value": avg_order_value,
            "top_product": top_product,
            "growth_rate": round(rng.uniform(6.0, 22.0), 1),
        },
    }


def _generate_saas(spec: MockSpec) -> Dict[str, Any]:
    sizes = _sizes("saas", spec.scale)
    days = _clamp_int(spec.days, 30, 3650)
    rng = _rng(spec.seed)

    today = date.today()
    start = today - timedelta(days=days - 1)
    all_days = [start + timedelta(days=i) for i in range(days)]

    regions = ["NA", "EMEA", "APAC", "LATAM"]
    segments = ["SMB", "Mid-Market", "Enterprise"]
    industries = ["FinTech", "E-commerce", "Healthcare", "Education", "Media", "Manufacturing", "DevTools", "Cybersecurity"]

    plan_tiers = [
        {"id": "plan_free", "name": "Free", "tier": "free", "price_monthly": 0, "seat_limit": 3},
        {"id": "plan_starter", "name": "Starter", "tier": "starter", "price_monthly": 49, "seat_limit": 10},
        {"id": "plan_pro", "name": "Pro", "tier": "pro", "price_monthly": 199, "seat_limit": 50},
        {"id": "plan_business", "name": "Business", "tier": "business", "price_monthly": 799, "seat_limit": 200},
        {"id": "plan_enterprise", "name": "Enterprise", "tier": "enterprise", "price_monthly": 2500, "seat_limit": 1000},
    ]

    account_statuses = ["active", "trialing", "churned", "paused"]
    subscription_statuses = ["active", "trialing", "past_due", "canceled"]

    # Accounts
    accounts: List[Dict[str, Any]] = []
    for i in range(1, sizes["accounts"] + 1):
        created = start - timedelta(days=rng.randint(0, 540))
        segment = _wchoice(rng, segments, [0.62, 0.28, 0.10])
        region = _wchoice(rng, regions, [0.45, 0.27, 0.20, 0.08])
        industry = _pick(rng, industries)
        status = _wchoice(rng, account_statuses, [0.80, 0.10, 0.06, 0.04])
        accounts.append(
            {
                "id": i,
                "name": f"Acme Corp {i:06d}",
                "region": region,
                "segment": segment,
                "industry": industry,
                "created_at": _iso(created),
                "status": status,
                "employees": int(max(5, rng.gauss(120 if segment == 'SMB' else (600 if segment == 'Mid-Market' else 2500), 120))),
            }
        )

    # Users (members) attached to accounts
    users: List[Dict[str, Any]] = []
    first_names = ["Alex", "Sam", "Jordan", "Taylor", "Casey", "Morgan", "Riley", "Avery", "Jamie", "Cameron"]
    last_names = ["Johnson", "Smith", "Brown", "Davis", "Miller", "Wilson", "Moore", "Anderson", "Thomas", "Martin"]
    for user_id in range(1, sizes["users"] + 1):
        acc_id = rng.randint(1, sizes["accounts"])
        fn = _pick(rng, first_names)
        ln = _pick(rng, last_names)
        created = start - timedelta(days=rng.randint(0, 365))
        users.append(
            {
                "id": user_id,
                "account_id": acc_id,
                "name": f"{fn} {ln}",
                "email": f"{fn.lower()}.{ln.lower()}{user_id}@example.com",
                "role": _wchoice(rng, ["member", "admin", "owner"], [0.86, 0.12, 0.02]),
                "created_at": _iso(created),
                "status": _wchoice(rng, ["active", "inactive"], [0.93, 0.07]),
            }
        )

    # Subscriptions (mostly one per account, some multi-product)
    subscriptions: List[Dict[str, Any]] = []
    subscription_events: List[Dict[str, Any]] = []

    sub_id = 1
    for acc in accounts:
        # probability of having a paid subscription
        seg = acc["segment"]
        p_paid = 0.22 if seg == "SMB" else (0.38 if seg == "Mid-Market" else 0.62)
        has_sub = rng.random() < (p_paid + 0.10)  # include some free/trial subs
        if not has_sub:
            continue

        # choose plan: skew up by segment
        if seg == "SMB":
            plan = _wchoice(rng, plan_tiers, [0.20, 0.45, 0.28, 0.06, 0.01])
        elif seg == "Mid-Market":
            plan = _wchoice(rng, plan_tiers, [0.05, 0.25, 0.45, 0.20, 0.05])
        else:
            plan = _wchoice(rng, plan_tiers, [0.02, 0.08, 0.30, 0.35, 0.25])

        start_dt = start - timedelta(days=rng.randint(0, max(30, days)))
        status = _wchoice(rng, subscription_statuses, [0.78, 0.10, 0.06, 0.06])

        # churn / cancel
        canceled_at = None
        if status == "canceled":
            canceled_at = _iso(start_dt + timedelta(days=rng.randint(30, 420)))

        seats = int(max(1, min(plan["seat_limit"], rng.gauss(6 if seg == "SMB" else (25 if seg == "Mid-Market" else 180), 12))))
        base_mrr = float(plan["price_monthly"]) * max(1, math.ceil(seats / max(1, plan["seat_limit"] / 10)))
        mrr = round(base_mrr * rng.uniform(0.92, 1.15), 2)

        subscriptions.append(
            {
                "id": sub_id,
                "account_id": acc["id"],
                "plan_id": plan["id"],
                "plan_name": plan["name"],
                "plan_tier": plan["tier"],
                "status": status,
                "start_date": _iso(start_dt),
                "canceled_at": canceled_at,
                "seats": seats,
                "mrr": mrr,
                "currency": "USD",
            }
        )

        # add 0-2 lifecycle events
        for _ in range(rng.randint(0, 2)):
            ev_date = start_dt + timedelta(days=rng.randint(14, 240))
            if ev_date > today:
                continue
            ev_type = _wchoice(rng, ["upgrade", "downgrade", "seat_change"], [0.44, 0.18, 0.38])
            delta = round(mrr * rng.uniform(-0.25, 0.40), 2) if ev_type != "downgrade" else round(-abs(mrr * rng.uniform(0.05, 0.22)), 2)
            subscription_events.append(
                {
                    "id": len(subscription_events) + 1,
                    "subscription_id": sub_id,
                    "account_id": acc["id"],
                    "event_date": _iso(ev_date),
                    "event_type": ev_type,
                    "mrr_delta": delta,
                }
            )

        sub_id += 1

        if sub_id > sizes["subscriptions"]:
            break

    # Invoices & payments (monthly)
    invoices: List[Dict[str, Any]] = []
    payments: List[Dict[str, Any]] = []
    invoice_id = 1
    for sub in subscriptions:
        # invoice months: last N months
        months_back = min(24, max(6, days // 30 + 6))
        for m in range(months_back):
            inv_month = (today.replace(day=1) - timedelta(days=30 * m))
            inv_date = inv_month + timedelta(days=rng.randint(0, 6))
            if inv_date < start - timedelta(days=30):
                continue
            amount = round(float(sub["mrr"]) * rng.uniform(0.95, 1.05), 2)
            status = _wchoice(rng, ["paid", "paid", "paid", "open", "void"], [0.75, 0.0, 0.0, 0.20, 0.05])
            invoices.append(
                {
                    "id": invoice_id,
                    "account_id": sub["account_id"],
                    "subscription_id": sub["id"],
                    "invoice_date": _iso(inv_date),
                    "period_month": _month_key(inv_date),
                    "amount": amount,
                    "currency": "USD",
                    "status": status,
                }
            )
            if status == "paid":
                pay_date = inv_date + timedelta(days=rng.randint(0, 10))
                payments.append(
                    {
                        "id": len(payments) + 1,
                        "invoice_id": invoice_id,
                        "account_id": sub["account_id"],
                        "payment_date": _iso(pay_date),
                        "amount": amount,
                        "method": _wchoice(rng, ["card", "ach", "wire"], [0.62, 0.30, 0.08]),
                        "status": "succeeded",
                    }
                )
            invoice_id += 1
            if invoice_id > sizes["invoices"]:
                break
        if invoice_id > sizes["invoices"]:
            break

    # Product usage events (kept bounded)
    event_types = ["login", "api_call", "report_run", "dashboard_view", "export", "invite_sent"]
    events: List[Dict[str, Any]] = []
    for i in range(1, sizes["events"] + 1):
        d = _pick(rng, all_days)
        acc_id = rng.randint(1, sizes["accounts"])
        user_id = rng.randint(1, sizes["users"])
        events.append(
            {
                "id": i,
                "event_date": _iso(d),
                "account_id": acc_id,
                "user_id": user_id,
                "event_type": _wchoice(rng, event_types, [0.14, 0.34, 0.10, 0.26, 0.06, 0.10]),
                "value": round(max(0.0, rng.gauss(1.0, 0.6)), 3),
            }
        )

    # KPI time series: MRR, ARR, churn, retention-ish
    # approximate MRR by month using invoices
    mrr_by_month: Dict[str, float] = {}
    paid_invoices = [inv for inv in invoices if inv["status"] == "paid"]
    for inv in paid_invoices:
        mk = inv["period_month"]
        mrr_by_month[mk] = mrr_by_month.get(mk, 0.0) + float(inv["amount"])

    months = sorted({inv["period_month"] for inv in invoices})
    kpi_monthly: List[Dict[str, Any]] = []
    prev_mrr = None
    for mk in months:
        mrr = round(mrr_by_month.get(mk, 0.0), 2)
        arr = round(mrr * 12.0, 2)
        churned = int(max(0, rng.gauss(18 if spec.scale == "xl" else 6, 4)))
        active_accounts = int(min(sizes["accounts"], max(50, rng.gauss(sizes["accounts"] * 0.42, sizes["accounts"] * 0.06))))
        net_new_mrr = round(mrr - (prev_mrr or 0.0), 2) if prev_mrr is not None else None
        churn_rate = round(min(0.12, max(0.002, churned / max(1, active_accounts))), 4)
        kpi_monthly.append(
            {
                "month": mk,
                "mrr": mrr,
                "arr": arr,
                "net_new_mrr": net_new_mrr,
                "active_accounts": active_accounts,
                "churned_accounts": churned,
                "churn_rate": churn_rate,
                "gross_retention": round(1.0 - churn_rate * rng.uniform(0.8, 1.2), 4),
                "net_retention": round(1.0 + rng.uniform(-0.01, 0.08), 4),
            }
        )
        prev_mrr = mrr

    # Also provide daily metrics for charting
    metrics: List[Dict[str, Any]] = []
    # spread monthly MRR roughly across days for smooth charts
    mrr_daily = 0.0
    if kpi_monthly:
        mrr_daily = float(kpi_monthly[-1]["mrr"])
    for d in all_days:
        signups = int(max(0, rng.gauss(38, 12)))
        trials = int(max(0, rng.gauss(20, 8)))
        activations = int(max(0, rng.gauss(trials * 0.55, 3)))
        churned = int(max(0, rng.gauss(2.2, 1.2)))
        mrr_daily = max(0.0, mrr_daily + rng.gauss(120.0, 220.0) - churned * rng.uniform(40, 220))
        metrics.append(
            {
                "date": _iso(d),
                "mrr": round(mrr_daily, 2),
                "arr": round(mrr_daily * 12.0, 2),
                "signups": signups,
                "trials": trials,
                "activations": activations,
                "churned_accounts": churned,
                "active_accounts": int(max(10, rng.gauss(sizes["accounts"] * 0.42, sizes["accounts"] * 0.05))),
            }
        )

    summary = {
        "mrr": round(mrr_daily, 2),
        "arr": round(mrr_daily * 12.0, 2),
        "active_accounts": int(max(10, rng.gauss(sizes["accounts"] * 0.42, sizes["accounts"] * 0.05))),
        "active_users": int(max(10, rng.gauss(sizes["users"] * 0.50, sizes["users"] * 0.06))),
        "gross_retention": kpi_monthly[-1]["gross_retention"] if kpi_monthly else None,
        "net_retention": kpi_monthly[-1]["net_retention"] if kpi_monthly else None,
    }

    counts = {
        "accounts": len(accounts),
        "users": len(users),
        "subscriptions": len(subscriptions),
        "subscription_events": len(subscription_events),
        "invoices": len(invoices),
        "payments": len(payments),
        "events": len(events),
        "metrics": len(metrics),
        "kpi_monthly": len(kpi_monthly),
    }
    return {
        "meta": _base_meta(MockSpec(profile="saas", scale=spec.scale, seed=spec.seed, days=days), counts, 1),
        "plans": plan_tiers,
        "accounts": accounts,
        "users": users,
        "subscriptions": subscriptions,
        "subscription_events": subscription_events,
        "invoices": invoices,
        "payments": payments,
        "events": events,
        "metrics": metrics,
        "kpi_monthly": kpi_monthly,
        "summary": summary,
    }


def _generate_marketing(spec: MockSpec) -> Dict[str, Any]:
    sizes = _sizes("marketing", spec.scale)
    days = _clamp_int(spec.days, 30, 3650)
    rng = _rng(spec.seed)

    today = date.today()
    start = today - timedelta(days=days - 1)
    all_days = [start + timedelta(days=i) for i in range(days)]

    channels = ["search", "social", "display", "email", "affiliate", "events", "content"]
    platforms = ["google_ads", "meta", "linkedin", "tiktok", "x", "bing", "dv360"]

    # Campaign hierarchy
    campaigns: List[Dict[str, Any]] = []
    ad_groups: List[Dict[str, Any]] = []
    ads: List[Dict[str, Any]] = []

    for cid in range(1, sizes["campaigns"] + 1):
        ch = _wchoice(rng, channels, [0.34, 0.20, 0.14, 0.14, 0.06, 0.04, 0.08])
        platform = _wchoice(rng, platforms, [0.30, 0.22, 0.16, 0.08, 0.06, 0.10, 0.08])
        created = start - timedelta(days=rng.randint(0, 540))
        objective = _wchoice(rng, ["pipeline", "leads", "brand", "retargeting"], [0.46, 0.26, 0.18, 0.10])
        campaigns.append(
            {
                "id": cid,
                "name": f"{platform}:{ch}:Q{((created.month - 1) // 3) + 1}-{created.year}",
                "channel": ch,
                "platform": platform,
                "objective": objective,
                "status": _wchoice(rng, ["active", "paused", "ended"], [0.78, 0.14, 0.08]),
                "created_at": _iso(created),
            }
        )

    # Ad groups & ads
    ag_id = 1
    ad_id = 1
    for c in campaigns:
        group_count = 1 + (0 if sizes["campaigns"] > 3000 else rng.randint(1, 3))
        for _ in range(group_count):
            if ag_id > sizes["ad_groups"]:
                break
            ad_groups.append(
                {
                    "id": ag_id,
                    "campaign_id": c["id"],
                    "name": f"AG-{c['id']}-{ag_id}",
                    "targeting": _wchoice(rng, ["broad", "lookalike", "remarketing", "keyword"], [0.34, 0.22, 0.18, 0.26]),
                }
            )
            ad_count = 2 + rng.randint(0, 4)
            for _ in range(ad_count):
                if ad_id > sizes["ads"]:
                    break
                ads.append(
                    {
                        "id": ad_id,
                        "ad_group_id": ag_id,
                        "campaign_id": c["id"],
                        "creative_type": _wchoice(rng, ["static", "video", "carousel", "text"], [0.36, 0.22, 0.16, 0.26]),
                        "headline": f"Grow faster {ad_id}",
                        "landing_page": _wchoice(rng, ["/pricing", "/demo", "/signup", "/guides/bi"], [0.32, 0.28, 0.22, 0.18]),
                    }
                )
                ad_id += 1
                if ad_id > sizes["ads"]:
                    break
            ag_id += 1
        if ag_id > sizes["ad_groups"] or ad_id > sizes["ads"]:
            break

    # Daily spend/perf at campaign level
    ad_spend_daily: List[Dict[str, Any]] = []
    for c in campaigns:
        base = 35.0 if c["channel"] in ("email", "content") else (120.0 if c["channel"] in ("social", "search") else 70.0)
        for d in all_days:
            if c["status"] == "ended" and rng.random() < 0.92:
                continue
            spend = max(0.0, rng.gauss(base, base * 0.35))
            impressions = int(max(0, spend * rng.uniform(80, 250)))
            clicks = int(max(0, impressions * rng.uniform(0.005, 0.035)))
            leads = int(max(0, clicks * rng.uniform(0.01, 0.10)))
            opps = int(max(0, leads * rng.uniform(0.06, 0.22)))
            ad_spend_daily.append(
                {
                    "date": _iso(d),
                    "campaign_id": c["id"],
                    "channel": c["channel"],
                    "platform": c["platform"],
                    "spend": round(spend, 2),
                    "impressions": impressions,
                    "clicks": clicks,
                    "leads": leads,
                    "opportunities": opps,
                }
            )

    # Leads and touchpoints for attribution
    lead_statuses = ["new", "mql", "sql", "won", "lost"]
    lead_sources = ["paid", "organic", "partner", "direct", "event"]
    leads: List[Dict[str, Any]] = []
    touchpoints: List[Dict[str, Any]] = []

    for lid in range(1, sizes["leads"] + 1):
        created = start + timedelta(days=rng.randint(0, days - 1))
        status = _wchoice(rng, lead_statuses, [0.30, 0.26, 0.20, 0.10, 0.14])
        source = _wchoice(rng, lead_sources, [0.52, 0.18, 0.10, 0.14, 0.06])
        won = status == "won"
        revenue = round(max(0.0, rng.gauss(18_000 if won else 7_000, 8_000)), 2) if won else 0.0
        leads.append(
            {
                "id": lid,
                "created_at": _iso(created),
                "status": status,
                "source": source,
                "segment": _wchoice(rng, ["SMB", "Mid-Market", "Enterprise"], [0.64, 0.26, 0.10]),
                "country": _wchoice(rng, ["US", "UK", "DE", "FR", "IN", "SG", "BR", "CA"], [0.38, 0.08, 0.07, 0.06, 0.17, 0.06, 0.10, 0.08]),
                "attributed_revenue": revenue,
            }
        )
        tp_count = 2 + rng.randint(0, 4)
        for _ in range(tp_count):
            if len(touchpoints) >= sizes["touchpoints"]:
                break
            tp_date = created - timedelta(days=rng.randint(0, 28))
            c = campaigns[rng.randrange(0, len(campaigns))]
            touchpoints.append(
                {
                    "id": len(touchpoints) + 1,
                    "lead_id": lid,
                    "touch_date": _iso(tp_date),
                    "campaign_id": c["id"],
                    "channel": c["channel"],
                    "platform": c["platform"],
                    "touch_type": _wchoice(rng, ["impression", "click", "visit", "form_submit"], [0.42, 0.30, 0.18, 0.10]),
                }
            )
        if len(touchpoints) >= sizes["touchpoints"]:
            break

    # Attribution rollup (simple last-touch + first-touch)
    attributed_last_touch: Dict[str, float] = {}
    attributed_first_touch: Dict[str, float] = {}
    for lead in leads:
        if not lead["attributed_revenue"]:
            continue
        lid = lead["id"]
        tps = [t for t in touchpoints if t["lead_id"] == lid]
        if not tps:
            continue
        tps_sorted = sorted(tps, key=lambda t: t["touch_date"])
        first = tps_sorted[0]["channel"]
        last = tps_sorted[-1]["channel"]
        attributed_first_touch[first] = attributed_first_touch.get(first, 0.0) + float(lead["attributed_revenue"])
        attributed_last_touch[last] = attributed_last_touch.get(last, 0.0) + float(lead["attributed_revenue"])

    # Metrics time series (daily)
    spend_by_day: Dict[str, float] = {}
    imps_by_day: Dict[str, int] = {}
    clicks_by_day: Dict[str, int] = {}
    leads_by_day: Dict[str, int] = {}
    opps_by_day: Dict[str, int] = {}
    for row in ad_spend_daily:
        ds = row["date"]
        spend_by_day[ds] = spend_by_day.get(ds, 0.0) + float(row["spend"])
        imps_by_day[ds] = imps_by_day.get(ds, 0) + int(row["impressions"])
        clicks_by_day[ds] = clicks_by_day.get(ds, 0) + int(row["clicks"])
        leads_by_day[ds] = leads_by_day.get(ds, 0) + int(row["leads"])
        opps_by_day[ds] = opps_by_day.get(ds, 0) + int(row["opportunities"])

    metrics: List[Dict[str, Any]] = []
    for d in all_days:
        ds = _iso(d)
        spend = round(spend_by_day.get(ds, 0.0), 2)
        imps = imps_by_day.get(ds, 0)
        clicks = clicks_by_day.get(ds, 0)
        leads_n = leads_by_day.get(ds, 0)
        opps_n = opps_by_day.get(ds, 0)
        cpc = round(spend / max(1, clicks), 4)
        cpl = round(spend / max(1, leads_n), 4)
        metrics.append(
            {
                "date": ds,
                "spend": spend,
                "impressions": imps,
                "clicks": clicks,
                "leads": leads_n,
                "opportunities": opps_n,
                "cpc": cpc,
                "cpl": cpl,
            }
        )

    summary = {
        "total_spend": round(sum(spend_by_day.values()), 2),
        "total_leads": int(sum(leads_by_day.values())),
        "total_opportunities": int(sum(opps_by_day.values())),
        "attributed_revenue_last_touch": round(sum(attributed_last_touch.values()), 2),
        "top_channel_last_touch": max(attributed_last_touch.items(), key=lambda kv: kv[1])[0] if attributed_last_touch else None,
    }

    counts = {
        "campaigns": len(campaigns),
        "ad_groups": len(ad_groups),
        "ads": len(ads),
        "ad_spend_daily": len(ad_spend_daily),
        "leads": len(leads),
        "touchpoints": len(touchpoints),
        "metrics": len(metrics),
    }
    return {
        "meta": _base_meta(MockSpec(profile="marketing", scale=spec.scale, seed=spec.seed, days=days), counts, 1),
        "campaigns": campaigns,
        "ad_groups": ad_groups,
        "ads": ads,
        "ad_spend_daily": ad_spend_daily,
        "leads": leads,
        "touchpoints": touchpoints,
        "attribution": {
            "last_touch_by_channel": {k: round(v, 2) for k, v in attributed_last_touch.items()},
            "first_touch_by_channel": {k: round(v, 2) for k, v in attributed_first_touch.items()},
        },
        "metrics": metrics,
        "summary": summary,
    }


def _generate_finance(spec: MockSpec) -> Dict[str, Any]:
    sizes = _sizes("finance", spec.scale)
    days = _clamp_int(spec.days, 90, 3650)
    rng = _rng(spec.seed)

    today = date.today()
    start = today - timedelta(days=days - 1)
    all_days = [start + timedelta(days=i) for i in range(days)]

    # Chart of accounts
    coa_categories = [
        ("Revenue", "revenue"),
        ("COGS", "cogs"),
        ("Operating Expenses", "opex"),
        ("Other Income", "other_income"),
        ("Other Expense", "other_expense"),
    ]
    gl_accounts: List[Dict[str, Any]] = []
    for i in range(1, sizes["coa_accounts"] + 1):
        cat_name, cat_key = _wchoice(rng, coa_categories, [0.18, 0.12, 0.55, 0.08, 0.07])
        gl_accounts.append(
            {
                "id": i,
                "code": f"{4000 + i}",
                "name": f"{cat_name} {i}",
                "category": cat_key,
            }
        )

    vendors = [{"id": i, "name": f"Vendor {i:05d}", "category": _wchoice(rng, ["cloud", "payroll", "tools", "rent", "legal", "marketing"], [0.24, 0.26, 0.20, 0.12, 0.08, 0.10])} for i in range(1, sizes["vendors"] + 1)]
    customers = [{"id": i, "name": f"Customer {i:05d}", "segment": _wchoice(rng, ["SMB", "Mid-Market", "Enterprise"], [0.62, 0.28, 0.10])} for i in range(1, sizes["customers"] + 1)]

    # AR/AP invoices
    invoices: List[Dict[str, Any]] = []
    for i in range(1, sizes["invoices"] + 1):
        d = _pick(rng, all_days)
        inv_type = _wchoice(rng, ["ar", "ap"], [0.55, 0.45])
        amount = round(max(50.0, abs(rng.gauss(8_000 if inv_type == "ar" else 3_500, 6_000))), 2)
        invoices.append(
            {
                "id": i,
                "invoice_date": _iso(d),
                "type": inv_type,
                "customer_id": rng.randint(1, sizes["customers"]) if inv_type == "ar" else None,
                "vendor_id": rng.randint(1, sizes["vendors"]) if inv_type == "ap" else None,
                "amount": amount,
                "status": _wchoice(rng, ["open", "paid", "void"], [0.18, 0.78, 0.04]),
                "currency": "USD",
            }
        )

    # Transactions: single-sided postings for simplicity (amount with sign by category)
    transactions: List[Dict[str, Any]] = []
    for i in range(1, sizes["transactions"] + 1):
        d = _pick(rng, all_days)
        gl = gl_accounts[rng.randrange(0, len(gl_accounts))]
        cat = gl["category"]
        magnitude = abs(rng.gauss(320.0 if cat == "opex" else (1200.0 if cat == "revenue" else 520.0), 420.0))
        amount = round(magnitude, 2)
        # sign convention: revenue positive, expenses negative
        if cat in ("cogs", "opex", "other_expense"):
            amount = -amount
        if cat == "other_income":
            amount = amount * 0.65
        transactions.append(
            {
                "id": i,
                "date": _iso(d),
                "gl_account_id": gl["id"],
                "gl_category": cat,
                "amount": amount,
                "vendor_id": rng.randint(1, sizes["vendors"]) if amount < 0 and rng.random() < 0.55 else None,
                "customer_id": rng.randint(1, sizes["customers"]) if amount > 0 and rng.random() < 0.70 else None,
                "memo": _wchoice(rng, ["invoice", "payroll", "aws", "subscription", "refund", "contractor", "rent"], [0.16, 0.18, 0.20, 0.14, 0.06, 0.14, 0.12]),
            }
        )

    # Monthly P&L rollup
    pnl_by_month: Dict[str, Dict[str, float]] = {}
    for t in transactions:
        mk = _month_key(date.fromisoformat(t["date"]))
        if mk not in pnl_by_month:
            pnl_by_month[mk] = {"revenue": 0.0, "cogs": 0.0, "opex": 0.0, "other_income": 0.0, "other_expense": 0.0}
        pnl_by_month[mk][t["gl_category"]] = pnl_by_month[mk].get(t["gl_category"], 0.0) + float(t["amount"])

    pnl_monthly: List[Dict[str, Any]] = []
    for mk in sorted(pnl_by_month.keys()):
        rev = pnl_by_month[mk]["revenue"]
        cogs = pnl_by_month[mk]["cogs"]
        opex = pnl_by_month[mk]["opex"]
        other_inc = pnl_by_month[mk]["other_income"]
        other_exp = pnl_by_month[mk]["other_expense"]
        gross_profit = rev + cogs  # cogs is negative
        ebitda = gross_profit + opex + other_inc + other_exp
        pnl_monthly.append(
            {
                "month": mk,
                "revenue": round(rev, 2),
                "cogs": round(cogs, 2),
                "opex": round(opex, 2),
                "gross_profit": round(gross_profit, 2),
                "gross_margin": round((gross_profit / rev) if rev else 0.0, 4),
                "ebitda": round(ebitda, 2),
            }
        )

    # Daily metrics (subset for charts)
    by_day: Dict[str, Dict[str, float]] = {}
    for t in transactions:
        ds = t["date"]
        if ds not in by_day:
            by_day[ds] = {"revenue": 0.0, "cogs": 0.0, "opex": 0.0}
        cat = t["gl_category"]
        if cat in by_day[ds]:
            by_day[ds][cat] += float(t["amount"])
    metrics: List[Dict[str, Any]] = []
    for d in all_days:
        ds = _iso(d)
        rev = by_day.get(ds, {}).get("revenue", 0.0)
        cogs = by_day.get(ds, {}).get("cogs", 0.0)
        opex = by_day.get(ds, {}).get("opex", 0.0)
        gp = rev + cogs
        metrics.append(
            {
                "date": ds,
                "revenue": round(rev, 2),
                "cogs": round(cogs, 2),
                "opex": round(opex, 2),
                "gross_profit": round(gp, 2),
            }
        )

    total_rev = round(sum(r["revenue"] for r in pnl_monthly), 2) if pnl_monthly else 0.0
    total_opex = round(sum(r["opex"] for r in pnl_monthly), 2) if pnl_monthly else 0.0
    summary = {
        "total_revenue": total_rev,
        "total_opex": total_opex,
        "months": len(pnl_monthly),
        "latest_month": pnl_monthly[-1]["month"] if pnl_monthly else None,
        "latest_ebitda": pnl_monthly[-1]["ebitda"] if pnl_monthly else None,
    }

    counts = {
        "gl_accounts": len(gl_accounts),
        "vendors": len(vendors),
        "customers": len(customers),
        "invoices": len(invoices),
        "transactions": len(transactions),
        "pnl_monthly": len(pnl_monthly),
        "metrics": len(metrics),
    }
    return {
        "meta": _base_meta(MockSpec(profile="finance", scale=spec.scale, seed=spec.seed, days=days), counts, 1),
        "gl_accounts": gl_accounts,
        "vendors": vendors,
        "customers": customers,
        "invoices": invoices,
        "transactions": transactions,
        "pnl_monthly": pnl_monthly,
        "metrics": metrics,
        "summary": summary,
    }


def _generate_sales(spec: MockSpec) -> Dict[str, Any]:
    sizes = _sizes("sales", spec.scale)
    days = _clamp_int(spec.days, 90, 3650)
    rng = _rng(spec.seed)

    today = date.today()
    start = today - timedelta(days=days - 1)
    all_days = [start + timedelta(days=i) for i in range(days)]

    regions = ["NA", "EMEA", "APAC", "LATAM"]
    segments = ["SMB", "Mid-Market", "Enterprise"]
    stages = ["Prospecting", "Qualified", "Discovery", "Proposal", "Negotiation", "Closed Won", "Closed Lost"]

    # Sales reps
    reps: List[Dict[str, Any]] = []
    for rid in range(1, sizes["reps"] + 1):
        reps.append(
            {
                "id": rid,
                "name": f"Rep {rid:04d}",
                "team": _wchoice(rng, ["AE", "SDR", "AM"], [0.64, 0.24, 0.12]),
                "region": _wchoice(rng, regions, [0.46, 0.26, 0.20, 0.08]),
                "segment": _wchoice(rng, segments, [0.64, 0.26, 0.10]),
            }
        )

    # Accounts + contacts
    accounts: List[Dict[str, Any]] = []
    for aid in range(1, sizes["accounts"] + 1):
        created = start - timedelta(days=rng.randint(0, 900))
        accounts.append(
            {
                "id": aid,
                "name": f"Account {aid:06d}",
                "region": _wchoice(rng, regions, [0.46, 0.26, 0.20, 0.08]),
                "segment": _wchoice(rng, segments, [0.64, 0.26, 0.10]),
                "industry": _wchoice(rng, ["FinTech", "SaaS", "E-commerce", "Healthcare", "Media", "Manufacturing"], [0.18, 0.22, 0.16, 0.14, 0.16, 0.14]),
                "employees": int(max(5, rng.gauss(140, 160))),
                "created_at": _iso(created),
            }
        )

    contacts: List[Dict[str, Any]] = []
    for cid in range(1, sizes["contacts"] + 1):
        aid = rng.randint(1, sizes["accounts"])
        contacts.append(
            {
                "id": cid,
                "account_id": aid,
                "name": f"Contact {cid:07d}",
                "title": _wchoice(rng, ["VP", "Director", "Manager", "IC", "C-level"], [0.18, 0.22, 0.30, 0.22, 0.08]),
                "email": f"contact{cid}@example.com",
            }
        )

    # Opportunities
    opps: List[Dict[str, Any]] = []
    stage_history: List[Dict[str, Any]] = []
    bookings: List[Dict[str, Any]] = []
    opp_id = 1
    for _ in range(sizes["opps"]):
        account_id = rng.randint(1, sizes["accounts"])
        rep = reps[rng.randrange(0, len(reps))]
        created = start + timedelta(days=rng.randint(0, days - 1))
        amount = round(max(1_000.0, abs(rng.gauss(18_000, 28_000))), 2)
        stage = _wchoice(rng, stages, [0.18, 0.18, 0.18, 0.16, 0.10, 0.10, 0.10])
        probability = {
            "Prospecting": 0.10,
            "Qualified": 0.20,
            "Discovery": 0.35,
            "Proposal": 0.55,
            "Negotiation": 0.72,
            "Closed Won": 1.00,
            "Closed Lost": 0.00,
        }[stage]
        close = created + timedelta(days=rng.randint(14, 120))
        opps.append(
            {
                "id": opp_id,
                "account_id": account_id,
                "rep_id": rep["id"],
                "created_at": _iso(created),
                "close_date": _iso(close),
                "stage": stage,
                "probability": probability,
                "amount": amount,
                "forecast_category": _wchoice(rng, ["pipeline", "best_case", "commit"], [0.52, 0.28, 0.20]),
            }
        )
        # stage history: 2-4 changes
        sh_count = 2 + rng.randint(0, 2)
        stage_idx = min(stages.index(stage), len(stages) - 1)
        cur_dt = created
        for si in range(sh_count):
            cur_stage = stages[min(stage_idx, si)] if stage in ("Closed Won", "Closed Lost") else stages[min(len(stages) - 3, si)]
            stage_history.append(
                {
                    "id": len(stage_history) + 1,
                    "opportunity_id": opp_id,
                    "changed_at": _iso(cur_dt),
                    "stage": cur_stage,
                }
            )
            cur_dt = cur_dt + timedelta(days=rng.randint(4, 18))

        if stage == "Closed Won":
            bookings.append(
                {
                    "id": len(bookings) + 1,
                    "opportunity_id": opp_id,
                    "booking_date": _iso(close),
                    "amount": amount,
                    "type": _wchoice(rng, ["new", "expansion", "renewal"], [0.56, 0.26, 0.18]),
                }
            )
        opp_id += 1

    # Activities (calls/emails/meetings)
    activities: List[Dict[str, Any]] = []
    activity_types = ["call", "email", "meeting", "demo", "note"]
    for i in range(1, sizes["activities"] + 1):
        d = _pick(rng, all_days)
        opp = opps[rng.randrange(0, len(opps))]
        activities.append(
            {
                "id": i,
                "date": _iso(d),
                "opportunity_id": opp["id"],
                "rep_id": opp["rep_id"],
                "type": _wchoice(rng, activity_types, [0.26, 0.34, 0.16, 0.12, 0.12]),
                "outcome": _wchoice(rng, ["positive", "neutral", "negative"], [0.54, 0.34, 0.12]),
            }
        )

    # Quota monthly by rep
    quota_monthly: List[Dict[str, Any]] = []
    months = sorted({_month_key(d) for d in all_days})
    for rep in reps:
        base = 70_000 if rep["team"] == "AE" else (12_000 if rep["team"] == "SDR" else 55_000)
        for mk in months:
            quota_monthly.append(
                {
                    "rep_id": rep["id"],
                    "month": mk,
                    "quota": round(max(5_000.0, rng.gauss(base, base * 0.18)), 2),
                }
            )

    # Daily pipeline snapshot (aggregated)
    pipeline_daily: List[Dict[str, Any]] = []
    for d in all_days:
        ds = _iso(d)
        open_opps = [o for o in opps if o["created_at"] <= ds and o["stage"] not in ("Closed Won", "Closed Lost")]
        pipe_amt = sum(float(o["amount"]) for o in open_opps)
        weighted = sum(float(o["amount"]) * float(o["probability"]) for o in open_opps)
        won_today = sum(float(b["amount"]) for b in bookings if b["booking_date"] == ds)
        pipeline_daily.append(
            {
                "date": ds,
                "open_opps": len(open_opps),
                "pipeline_amount": round(pipe_amt, 2),
                "weighted_pipeline": round(weighted, 2),
                "bookings": round(won_today, 2),
            }
        )

    # Metrics time series: reuse pipeline_daily
    metrics = pipeline_daily
    summary = {
        "open_opps": metrics[-1]["open_opps"] if metrics else 0,
        "pipeline_amount": metrics[-1]["pipeline_amount"] if metrics else 0.0,
        "bookings_total": round(sum(float(b["amount"]) for b in bookings), 2),
        "win_rate": round(len([o for o in opps if o["stage"] == "Closed Won"]) / max(1, len([o for o in opps if o["stage"] in ("Closed Won", "Closed Lost")])), 4),
    }

    counts = {
        "reps": len(reps),
        "accounts": len(accounts),
        "contacts": len(contacts),
        "opportunities": len(opps),
        "stage_history": len(stage_history),
        "activities": len(activities),
        "bookings": len(bookings),
        "quota_monthly": len(quota_monthly),
        "metrics": len(metrics),
    }
    return {
        "meta": _base_meta(MockSpec(profile="sales", scale=spec.scale, seed=spec.seed, days=days), counts, 1),
        "reps": reps,
        "accounts": accounts,
        "contacts": contacts,
        "opportunities": opps,
        "opportunity_stage_history": stage_history,
        "activities": activities,
        "bookings": bookings,
        "quota_monthly": quota_monthly,
        "metrics": metrics,
        "summary": summary,
    }


