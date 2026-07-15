import json
import os
import psycopg2
import psycopg2.extras
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

DATABASE_URL = os.getenv("DATABASE_URL", "")


def get_connection():
    """Return a psycopg2 connection using DATABASE_URL."""
    conn = psycopg2.connect(DATABASE_URL)
    return conn


def _rows_to_dicts(cursor):
    """Convert psycopg2 cursor results to a list of dicts."""
    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # Create Orders table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            order_id TEXT PRIMARY KEY,
            customer_name TEXT,
            status TEXT,
            carrier TEXT,
            tracking_number TEXT,
            items TEXT,
            total_amount REAL,
            order_date TEXT
        )
    """)

    # Create FAQs table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS faqs (
            id SERIAL PRIMARY KEY,
            question TEXT,
            answer TEXT,
            category TEXT
        )
    """)

    # Create Calls table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS calls (
            call_id TEXT PRIMARY KEY,
            caller_number TEXT,
            start_time TEXT,
            end_time TEXT,
            status TEXT,
            sentiment TEXT,
            summary TEXT
        )
    """)

    # Create Call Transcripts table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS call_transcripts (
            id SERIAL PRIMARY KEY,
            call_id TEXT,
            speaker TEXT,
            text TEXT,
            timestamp TEXT
        )
    """)

    # Create Tool Logs table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tool_logs (
            id SERIAL PRIMARY KEY,
            call_id TEXT,
            tool_name TEXT,
            arguments TEXT,
            result TEXT,
            timestamp TEXT
        )
    """)

    conn.commit()

    # Check and seed initial data if empty
    cur.execute("SELECT COUNT(*) FROM orders")
    count = cur.fetchone()[0]
    if count == 0:
        seed_data(conn)

    conn.commit()
    cur.close()
    conn.close()


def seed_data(conn):
    cur = conn.cursor()

    sample_orders = [
        (
            "ORD-1001",
            "Alex Mercer",
            "Delivered",
            "FedEx",
            "FX9982347102",
            json.dumps([{"item": "Acme Noise-Canceling Wireless Headphones", "qty": 1, "price": 199.99}]),
            199.99,
            "2026-07-08"
        ),
        (
            "ORD-1002",
            "Samantha Chen",
            "In Transit",
            "UPS",
            "1Z9928374829102",
            json.dumps([
                {"item": "Acme Smart Fitness Watch Pro", "qty": 1, "price": 249.50},
                {"item": "Silicone Sport Band (Midnight Blue)", "qty": 1, "price": 25.00}
            ]),
            274.50,
            "2026-07-10"
        ),
        (
            "ORD-1003",
            "Marcus Vance",
            "Pending Return",
            "USPS",
            "9400111899560012345678",
            json.dumps([{"item": "Acme Mechanical RGB Keyboard (Brown Switches)", "qty": 1, "price": 129.00}]),
            129.00,
            "2026-07-05"
        )
    ]

    cur.executemany("""
        INSERT INTO orders (order_id, customer_name, status, carrier, tracking_number, items, total_amount, order_date)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (order_id) DO NOTHING
    """, sample_orders)

    sample_faqs = [
        (
            "What is your return policy?",
            "We offer a 30-day hassle-free return window on all items in original condition. Return shipping labels are generated automatically and are free for defective items or exchanges.",
            "Returns"
        ),
        (
            "How long does shipping take?",
            "Standard shipping takes 3-5 business days. Express shipping takes 1-2 business days. Tracking details are emailed as soon as your package leaves our warehouse.",
            "Shipping"
        ),
        (
            "Can I exchange an item instead of returning it?",
            "Yes! You can request an exchange within 30 days. We will ship out the replacement item immediately as soon as the carrier scans your return drop-off.",
            "Exchanges"
        ),
        (
            "What warranty covers Acme Electronics?",
            "All Acme Retail electronic products come with a full 2-year manufacturer warranty covering internal defects and hardware faults.",
            "Warranty"
        )
    ]

    cur.executemany("""
        INSERT INTO faqs (question, answer, category)
        VALUES (%s, %s, %s)
    """, sample_faqs)

    conn.commit()
    cur.close()


# ---------------------------------------------------------------------------
# Database query helpers
# ---------------------------------------------------------------------------

def get_order(order_id: str):
    conn = get_connection()
    cur = conn.cursor()
    # Support partial matches e.g. '1001' -> 'ORD-1001'
    clean_id = order_id.upper().strip()
    if not clean_id.startswith("ORD-") and clean_id.isdigit():
        clean_id = f"ORD-{clean_id}"

    cur.execute("SELECT * FROM orders WHERE order_id = %s", (clean_id,))
    row = cur.fetchone()
    columns = [desc[0] for desc in cur.description] if cur.description else []
    cur.close()
    conn.close()
    if not row:
        return None
    data = dict(zip(columns, row))
    data["items"] = json.loads(data["items"])
    return data


def update_order_status(order_id: str, new_status: str):
    conn = get_connection()
    cur = conn.cursor()
    clean_id = order_id.upper().strip()
    if not clean_id.startswith("ORD-") and clean_id.isdigit():
        clean_id = f"ORD-{clean_id}"

    cur.execute("UPDATE orders SET status = %s WHERE order_id = %s", (new_status, clean_id))
    affected = cur.rowcount
    conn.commit()
    cur.close()
    conn.close()
    return affected > 0


def search_faqs(query: str):
    conn = get_connection()
    cur = conn.cursor()
    terms = query.lower().split()
    cur.execute("SELECT * FROM faqs")
    rows = _rows_to_dicts(cur)
    cur.close()
    conn.close()

    results = []
    for row in rows:
        q_lower = row["question"].lower()
        a_lower = row["answer"].lower()
        cat_lower = row["category"].lower()
        score = sum(1 for term in terms if term in q_lower or term in a_lower or term in cat_lower)
        if score > 0 or not terms:
            results.append((score, row))

    results.sort(key=lambda x: x[0], reverse=True)
    return [item[1] for item in results[:3]]


def get_all_orders():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM orders ORDER BY order_id")
    rows = _rows_to_dicts(cur)
    cur.close()
    conn.close()
    for r in rows:
        r["items"] = json.loads(r["items"])
    return rows


def get_all_faqs():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM faqs")
    rows = _rows_to_dicts(cur)
    cur.close()
    conn.close()
    return rows


def create_or_update_call(call_id: str, caller_number: str, status: str = "active"):
    conn = get_connection()
    cur = conn.cursor()
    now = datetime.utcnow().isoformat()
    cur.execute("SELECT call_id FROM calls WHERE call_id = %s", (call_id,))
    if cur.fetchone():
        cur.execute(
            "UPDATE calls SET status = %s, end_time = %s WHERE call_id = %s",
            (status, now, call_id)
        )
    else:
        cur.execute("""
            INSERT INTO calls (call_id, caller_number, start_time, status, sentiment, summary)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (call_id, caller_number, now, status, "Neutral", "Call in progress"))
    conn.commit()
    cur.close()
    conn.close()


def log_transcript(call_id: str, speaker: str, text: str):
    conn = get_connection()
    cur = conn.cursor()
    now = datetime.utcnow().isoformat()
    cur.execute("""
        INSERT INTO call_transcripts (call_id, speaker, text, timestamp)
        VALUES (%s, %s, %s, %s)
    """, (call_id, speaker, text, now))
    conn.commit()
    cur.close()
    conn.close()


def log_tool_execution(call_id: str, tool_name: str, arguments: dict, result: dict):
    conn = get_connection()
    cur = conn.cursor()
    now = datetime.utcnow().isoformat()
    cur.execute("""
        INSERT INTO tool_logs (call_id, tool_name, arguments, result, timestamp)
        VALUES (%s, %s, %s, %s, %s)
    """, (call_id, tool_name, json.dumps(arguments), json.dumps(result), now))
    conn.commit()
    cur.close()
    conn.close()


def get_recent_transcripts(limit: int = 50):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM call_transcripts ORDER BY id DESC LIMIT %s", (limit,))
    rows = _rows_to_dicts(cur)
    cur.close()
    conn.close()
    rows.reverse()
    return rows


def get_recent_tool_logs(limit: int = 20):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM tool_logs ORDER BY id DESC LIMIT %s", (limit,))
    rows = _rows_to_dicts(cur)
    cur.close()
    conn.close()
    for r in rows:
        try:
            r["arguments"] = json.loads(r["arguments"])
        except Exception:
            pass
        try:
            r["result"] = json.loads(r["result"])
        except Exception:
            pass
    return rows


# Ensure database is initialized when imported
init_db()
