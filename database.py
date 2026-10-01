"""
SQLite persistence layer.

Holds the "enterprise" business data (production, inventory, sales, HR,
finance, procurement, quality) that the Data Agent and SQL Agent read from,
plus the operational tables the platform uses to run itself
(workflows, approvals, actions).
"""
import sqlite3
import json
import random
import datetime as dt
from contextlib import contextmanager
from pathlib import Path

from app.config import settings

SCHEMA = """
-- ---------- Business data tables ----------
CREATE TABLE IF NOT EXISTS production (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    line TEXT NOT NULL,
    units_planned INTEGER NOT NULL,
    units_produced INTEGER NOT NULL,
    defect_units INTEGER NOT NULL,
    downtime_minutes INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    sku TEXT NOT NULL,
    warehouse TEXT NOT NULL,
    quantity_on_hand INTEGER NOT NULL,
    reorder_point INTEGER NOT NULL,
    unit_cost REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS sales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    region TEXT NOT NULL,
    product TEXT NOT NULL,
    units_sold INTEGER NOT NULL,
    revenue REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS hr (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    department TEXT NOT NULL,
    headcount INTEGER NOT NULL,
    open_positions INTEGER NOT NULL,
    attrition_count INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS finance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    department TEXT NOT NULL,
    budget REAL NOT NULL,
    actual_spend REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS procurement (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    supplier TEXT NOT NULL,
    item TEXT NOT NULL,
    order_qty INTEGER NOT NULL,
    lead_time_days INTEGER NOT NULL,
    on_time INTEGER NOT NULL -- 1/0
);

CREATE TABLE IF NOT EXISTS quality (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    line TEXT NOT NULL,
    inspections INTEGER NOT NULL,
    failures INTEGER NOT NULL,
    complaint_count INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    department TEXT NOT NULL,
    status TEXT NOT NULL,
    percent_complete INTEGER NOT NULL,
    budget REAL NOT NULL,
    actual_spend REAL NOT NULL,
    due_date TEXT NOT NULL
);

-- ---------- Platform operational tables ----------
CREATE TABLE IF NOT EXISTS workflows (
    id TEXT PRIMARY KEY,
    domain TEXT NOT NULL,
    query TEXT NOT NULL,
    status TEXT NOT NULL,          -- running | awaiting_approval | completed | rejected | failed
    trace_json TEXT NOT NULL,      -- full step-by-step agent trace
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS approvals (
    id TEXT PRIMARY KEY,
    workflow_id TEXT NOT NULL,
    domain TEXT NOT NULL,
    summary TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    risk_score INTEGER NOT NULL,
    risk_level TEXT NOT NULL,
    status TEXT NOT NULL,          -- pending | approved | rejected
    decided_by TEXT,
    decision_comment TEXT,
    created_at TEXT NOT NULL,
    decided_at TEXT
);

CREATE TABLE IF NOT EXISTS actions (
    id TEXT PRIMARY KEY,
    workflow_id TEXT NOT NULL,
    domain TEXT NOT NULL,
    action_type TEXT NOT NULL,
    description TEXT NOT NULL,
    result_json TEXT NOT NULL,
    status TEXT NOT NULL,          -- executed | failed
    created_at TEXT NOT NULL
);
"""


@contextmanager
def get_conn():
    conn = sqlite3.connect(settings.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(SCHEMA)


def _is_seeded(conn) -> bool:
    row = conn.execute("SELECT COUNT(*) AS c FROM production").fetchone()
    return row["c"] > 0


def seed_sample_data(force: bool = False) -> None:
    """Populate the business tables with deterministic synthetic data so the
    platform is immediately explorable without any external data source."""
    random.seed(42)
    with get_conn() as conn:
        if _is_seeded(conn) and not force:
            return

        if force:
            for t in ["production", "inventory", "sales", "hr", "finance", "procurement", "quality", "projects"]:
                conn.execute(f"DELETE FROM {t}")

        today = dt.date.today()
        days = [today - dt.timedelta(days=i) for i in range(30)][::-1]

        # Production — line "A" starts drifting into more defects/downtime near the end
        lines = ["Line-A", "Line-B", "Line-C"]
        for d in days:
            for line in lines:
                planned = random.randint(900, 1100)
                drift = 1.0
                if line == "Line-A" and (today - d).days < 6:
                    drift = 1.6  # recent anomaly spike
                defect_rate = random.uniform(0.01, 0.03) * drift
                downtime = int(random.uniform(5, 40) * drift)
                produced = int(planned * random.uniform(0.92, 1.0))
                conn.execute(
                    "INSERT INTO production (date, line, units_planned, units_produced, defect_units, downtime_minutes) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (d.isoformat(), line, planned, produced, int(produced * defect_rate), downtime),
                )

        # Inventory — a few SKUs deliberately dip below reorder point
        skus = [("SKU-1001", "West-WH"), ("SKU-1002", "East-WH"), ("SKU-1003", "West-WH"), ("SKU-1004", "Central-WH")]
        for d in days:
            for sku, wh in skus:
                base = 500 if sku != "SKU-1002" else 150
                qty = max(0, int(base - (today - d).days * random.uniform(3, 9)))
                conn.execute(
                    "INSERT INTO inventory (date, sku, warehouse, quantity_on_hand, reorder_point, unit_cost) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (d.isoformat(), sku, wh, qty, 120, round(random.uniform(8, 60), 2)),
                )

        # Sales
        regions = ["North", "South", "East", "West"]
        products = ["Widget-Pro", "Widget-Lite", "Widget-Max"]
        for d in days:
            for region in regions:
                for product in products:
                    units = random.randint(20, 200)
                    price = {"Widget-Pro": 89.0, "Widget-Lite": 39.0, "Widget-Max": 149.0}[product]
                    conn.execute(
                        "INSERT INTO sales (date, region, product, units_sold, revenue) VALUES (?, ?, ?, ?, ?)",
                        (d.isoformat(), region, product, units, round(units * price, 2)),
                    )

        # HR
        depts = ["Engineering", "Sales", "Operations", "Support"]
        for d in days[::3]:
            for dept in depts:
                headcount = {"Engineering": 120, "Sales": 60, "Operations": 90, "Support": 45}[dept]
                conn.execute(
                    "INSERT INTO hr (date, department, headcount, open_positions, attrition_count) VALUES (?, ?, ?, ?, ?)",
                    (d.isoformat(), dept, headcount, random.randint(1, 8), random.randint(0, 3)),
                )

        # Finance — Operations dept overspending
        for d in days[::3]:
            for dept in depts:
                budget = {"Engineering": 200000, "Sales": 120000, "Operations": 90000, "Support": 50000}[dept]
                overspend_factor = 1.35 if dept == "Operations" else random.uniform(0.85, 1.05)
                conn.execute(
                    "INSERT INTO finance (date, department, budget, actual_spend) VALUES (?, ?, ?, ?)",
                    (d.isoformat(), dept, budget / 10, round((budget / 10) * overspend_factor, 2)),
                )

        # Procurement — one supplier with degrading on-time performance
        suppliers = ["Acme Parts", "Northwind Supply", "Globex Materials"]
        for d in days:
            for supplier in suppliers:
                on_time_prob = 0.55 if supplier == "Globex Materials" and (today - d).days < 10 else 0.92
                conn.execute(
                    "INSERT INTO procurement (date, supplier, item, order_qty, lead_time_days, on_time) VALUES (?, ?, ?, ?, ?, ?)",
                    (d.isoformat(), supplier, "Raw-Material-X", random.randint(50, 400),
                     random.randint(3, 21), 1 if random.random() < on_time_prob else 0),
                )

        # Quality — complaint spike on Line-A recently, correlating with production drift
        for d in days:
            for line in lines:
                inspections = random.randint(30, 60)
                base_fail = 0.04
                if line == "Line-A" and (today - d).days < 6:
                    base_fail = 0.11
                failures = int(inspections * base_fail)
                conn.execute(
                    "INSERT INTO quality (date, line, inspections, failures, complaint_count) VALUES (?, ?, ?, ?, ?)",
                    (d.isoformat(), line, inspections, failures, random.randint(0, 3) + (2 if base_fail > 0.08 else 0)),
                )

        # Projects
        sample_projects = [
            ("ERP Rollout Phase 2", "Operations", "at_risk", 55, 250000, 210000, (today + dt.timedelta(days=25)).isoformat()),
            ("Warehouse Automation", "Operations", "on_track", 70, 180000, 120000, (today + dt.timedelta(days=60)).isoformat()),
            ("Sales CRM Migration", "Sales", "on_track", 40, 90000, 35000, (today + dt.timedelta(days=45)).isoformat()),
            ("Supplier Diversification", "Procurement", "delayed", 30, 60000, 52000, (today + dt.timedelta(days=10)).isoformat()),
        ]
        for p in sample_projects:
            conn.execute(
                "INSERT INTO projects (name, department, status, percent_complete, budget, actual_spend, due_date) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)", p,
            )


def dict_rows(rows) -> list:
    return [dict(r) for r in rows]
