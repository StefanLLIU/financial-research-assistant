import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).parent / "research.db"


def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS research_reports (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker      TEXT    NOT NULL,
                company     TEXT,
                sector      TEXT,
                price       REAL,
                currency    TEXT,
                market_cap  REAL,
                pe_ratio    REAL,
                week_52_high REAL,
                week_52_low  REAL,
                news_json   TEXT,
                ai_summary  TEXT,
                created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def save_report(data: dict) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO research_reports
                (ticker, company, sector, price, currency, market_cap,
                 pe_ratio, week_52_high, week_52_low, news_json, ai_summary)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["ticker"],
                data.get("company"),
                data.get("sector"),
                data.get("price"),
                data.get("currency"),
                data.get("market_cap"),
                data.get("pe_ratio"),
                data.get("week_52_high"),
                data.get("week_52_low"),
                data.get("news_json"),
                data.get("ai_summary"),
            ),
        )
        return cur.lastrowid


def get_reports(limit: int = 20) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM research_reports ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_report(report_id: int) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM research_reports WHERE id = ?", (report_id,)
        ).fetchone()
        return dict(row) if row else None
