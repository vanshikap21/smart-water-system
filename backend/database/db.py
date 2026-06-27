"""
Database layer — PostgreSQL via psycopg2.
Connection is managed through a pool (psycopg2.pool.ThreadedConnectionPool)
so concurrent Flask threads share connections safely.
"""

import logging
import os
import psycopg2
import psycopg2.extras
from psycopg2.pool import ThreadedConnectionPool
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pool — created once at module import time
# ---------------------------------------------------------------------------
_pool: ThreadedConnectionPool | None = None


def _build_dsn() -> str:
    """Build DSN from individual env vars OR a full DATABASE_URL."""
    url = os.getenv("DATABASE_URL")
    if url:
        # Render / Railway export it as postgres:// — psycopg2 needs postgresql://
        return url.replace("postgres://", "postgresql://", 1)
    return (
        f"host={os.getenv('DB_HOST','localhost')} "
        f"port={os.getenv('DB_PORT','5432')} "
        f"dbname={os.getenv('DB_NAME','water_monitor')} "
        f"user={os.getenv('DB_USER','postgres')} "
        f"password={os.getenv('DB_PASSWORD','')} "
        f"sslmode={os.getenv('DB_SSLMODE','prefer')}"
    )


def _get_pool() -> ThreadedConnectionPool:
    global _pool
    if _pool is None:
        dsn = _build_dsn()
        _pool = ThreadedConnectionPool(minconn=1, maxconn=10, dsn=dsn)
        logger.info("PostgreSQL connection pool created.")
    return _pool


def get_connection():
    """Borrow a connection from the pool. Caller must call release_connection()."""
    return _get_pool().getconn()


def release_connection(conn):
    """Return connection to pool (resets it; does NOT close the socket)."""
    _get_pool().putconn(conn)


# ---------------------------------------------------------------------------
# Context manager for clean usage
# ---------------------------------------------------------------------------
class db_conn:
    """
    Usage:
        with db_conn() as (conn, cur):
            cur.execute(...)
            conn.commit()
    """
    def __enter__(self):
        self.conn = get_connection()
        self.cur  = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        return self.conn, self.cur

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.conn.rollback()
        self.cur.close()
        release_connection(self.conn)
        return False   # re-raise exceptions


# ---------------------------------------------------------------------------
# Schema init — idempotent CREATE TABLE IF NOT EXISTS
# ---------------------------------------------------------------------------
_SCHEMA = """
CREATE TABLE IF NOT EXISTS sensor_data (
    id          SERIAL PRIMARY KEY,
    timestamp   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    flow_rate   NUMERIC(8,3) NOT NULL,
    tank_level  NUMERIC(6,2) NOT NULL
);

CREATE TABLE IF NOT EXISTS leak_logs (
    id          SERIAL PRIMARY KEY,
    timestamp   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status      VARCHAR(10)  NOT NULL CHECK (status IN ('Leak','No Leak')),
    confidence  NUMERIC(5,2) NOT NULL
);

CREATE TABLE IF NOT EXISTS cost_logs (
    id             SERIAL PRIMARY KEY,
    timestamp      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    estimated_cost NUMERIC(10,6) NOT NULL
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_sensor_ts   ON sensor_data (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_leak_ts     ON leak_logs   (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_cost_ts     ON cost_logs   (timestamp DESC);
"""


def init_db():
    """Create tables and indexes if they don't already exist."""
    with db_conn() as (conn, cur):
        cur.execute(_SCHEMA)
        conn.commit()
    logger.info("PostgreSQL schema verified / created.")
