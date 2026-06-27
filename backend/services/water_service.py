"""
Water Service — all sensor data CRUD and analytics queries.
Uses PostgreSQL via the db_conn context manager.
PostgreSQL placeholders are %s (not ? like SQLite).
"""

import logging
from datetime import datetime, timedelta, timezone
from database.db import db_conn

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# INSERT helpers
# ---------------------------------------------------------------------------

def insert_sensor_reading(flow_rate: float, tank_level: float) -> int:
    with db_conn() as (conn, cur):
        cur.execute(
            "INSERT INTO sensor_data (flow_rate, tank_level) VALUES (%s, %s) RETURNING id",
            (flow_rate, tank_level)
        )
        row_id = cur.fetchone()["id"]
        conn.commit()
    return row_id


def insert_leak_log(status: str, confidence: float):
    with db_conn() as (conn, cur):
        cur.execute(
            "INSERT INTO leak_logs (status, confidence) VALUES (%s, %s)",
            (status, confidence)
        )
        conn.commit()


def insert_cost_log(estimated_cost: float):
    with db_conn() as (conn, cur):
        cur.execute(
            "INSERT INTO cost_logs (estimated_cost) VALUES (%s)",
            (estimated_cost,)
        )
        conn.commit()


# ---------------------------------------------------------------------------
# READ helpers
# ---------------------------------------------------------------------------

def _ts(row: dict) -> dict:
    """Convert timestamptz to ISO string so Flask can JSON-serialise it."""
    if row and "timestamp" in row and hasattr(row["timestamp"], "isoformat"):
        row = dict(row)
        row["timestamp"] = row["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
    return row


def get_latest_reading() -> dict | None:
    with db_conn() as (_, cur):
        cur.execute("SELECT * FROM sensor_data ORDER BY id DESC LIMIT 1")
        row = cur.fetchone()
    return _ts(dict(row)) if row else None


def get_recent_readings(limit: int = 50) -> list[dict]:
    with db_conn() as (_, cur):
        cur.execute(
            "SELECT * FROM sensor_data ORDER BY id DESC LIMIT %s", (limit,)
        )
        rows = cur.fetchall()
    return [_ts(dict(r)) for r in rows]


def get_readings_last_24h() -> list[dict]:
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    with db_conn() as (_, cur):
        cur.execute(
            "SELECT * FROM sensor_data WHERE timestamp >= %s ORDER BY timestamp ASC",
            (since,)
        )
        rows = cur.fetchall()
    return [_ts(dict(r)) for r in rows]


def get_hourly_consumption() -> list[dict]:
    """Total flow per hour for the last 24 hours."""
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    with db_conn() as (_, cur):
        cur.execute(
            """
            SELECT   TO_CHAR(timestamp AT TIME ZONE 'UTC', 'HH24') AS hour,
                     ROUND(SUM(flow_rate)::NUMERIC, 2)              AS total_flow
            FROM     sensor_data
            WHERE    timestamp >= %s
            GROUP BY hour
            ORDER BY hour ASC
            """,
            (since,)
        )
        rows = cur.fetchall()
    return [dict(r) for r in rows]


def get_daily_consumption(days: int = 7) -> list[dict]:
    """Daily total flow for last N days."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    with db_conn() as (_, cur):
        cur.execute(
            """
            SELECT   (timestamp AT TIME ZONE 'UTC')::DATE::TEXT AS date,
                     ROUND(SUM(flow_rate)::NUMERIC, 2)          AS total_flow
            FROM     sensor_data
            WHERE    timestamp >= %s
            GROUP BY date
            ORDER BY date ASC
            """,
            (since,)
        )
        rows = cur.fetchall()
    return [dict(r) for r in rows]


def get_tank_level_trend(limit: int = 30) -> list[dict]:
    with db_conn() as (_, cur):
        cur.execute(
            """
            SELECT timestamp, tank_level
            FROM   sensor_data
            ORDER  BY id DESC
            LIMIT  %s
            """,
            (limit,)
        )
        rows = list(reversed(cur.fetchall()))
    return [_ts(dict(r)) for r in rows]


def get_recent_leak_logs(limit: int = 10) -> list[dict]:
    with db_conn() as (_, cur):
        cur.execute(
            "SELECT * FROM leak_logs ORDER BY id DESC LIMIT %s", (limit,)
        )
        rows = cur.fetchall()
    return [_ts(dict(r)) for r in rows]


def get_cost_trend(limit: int = 30) -> list[dict]:
    with db_conn() as (_, cur):
        cur.execute(
            "SELECT * FROM cost_logs ORDER BY id DESC LIMIT %s", (limit,)
        )
        rows = list(reversed(cur.fetchall()))
    return [_ts(dict(r)) for r in rows]


def get_daily_report_data() -> dict:
    """Aggregate data used by the AI daily report."""
    with db_conn() as (_, cur):
        # Average flow
        cur.execute(
            """
            SELECT ROUND(AVG(flow_rate)::NUMERIC, 2) AS avg_flow
            FROM   sensor_data
            WHERE  timestamp >= NOW() - INTERVAL '1 day'
            """
        )
        avg = cur.fetchone()

        # Peak hour
        cur.execute(
            """
            SELECT   TO_CHAR(timestamp AT TIME ZONE 'UTC','HH24') AS hour,
                     SUM(flow_rate) AS total
            FROM     sensor_data
            WHERE    timestamp >= NOW() - INTERVAL '1 day'
            GROUP BY hour
            ORDER BY total DESC
            LIMIT    1
            """
        )
        peak = cur.fetchone()

        # Leak incidents
        cur.execute(
            """
            SELECT COUNT(*) AS count
            FROM   leak_logs
            WHERE  status = 'Leak'
            AND    timestamp >= NOW() - INTERVAL '1 day'
            """
        )
        leaks = cur.fetchone()

    return {
        "avg_flow":       float(avg["avg_flow"]) if avg and avg["avg_flow"] else 0,
        "peak_hour":      peak["hour"]           if peak else "N/A",
        "leak_incidents": int(leaks["count"])    if leaks else 0
    }
