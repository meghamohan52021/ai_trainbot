import sqlite3
import csv
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "chatbot.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def initialise_db():
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at TEXT NOT NULL,
            ended_at TEXT,
            task_completed TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            turn INTEGER NOT NULL,
            role TEXT NOT NULL,
            message TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS stations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alias TEXT NOT NULL UNIQUE,
            official_name TEXT NOT NULL
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS knowledge (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword TEXT NOT NULL UNIQUE,
            synonyms TEXT NOT NULL DEFAULT '',
            answer TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


def seed_stations():
    csv_path = os.path.join(os.path.dirname(__file__), "StationNameAndCode.csv")
    if not os.path.exists(csv_path):
        print("Warning: StationNameAndCode.csv not found.")
        return

    conn = get_connection()
    c = conn.cursor()
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            if len(row) < 2:
                continue
            name = row[0].strip()
            code = row[1].strip()
            if name:
                c.execute(
                    "INSERT OR IGNORE INTO stations (alias, official_name) VALUES (?, ?)",
                    (name.lower(), name)
                )
            if code:
                c.execute(
                    "INSERT OR IGNORE INTO stations (alias, official_name) VALUES (?, ?)",
                    (code.lower(), name)
                )
    conn.commit()
    conn.close()


def seed_knowledge():
    entries = [
        (
            "off peak",
            "off-peak,quiet time,cheaper time",
            "Off-peak tickets are valid outside of busy commuter periods and are usually cheaper than Anytime tickets. "
            "Exact hours vary by route but are typically outside 06:30-09:30 and 16:00-19:00 on weekdays."
        ),
        (
            "peak",
            "peak time,rush hour,busy time,commuter",
            "Peak tickets cover travel during busy commuter times - usually weekday mornings and evenings. "
            "They are the most expensive ticket type."
        ),
        (
            "anytime",
            "anytime ticket,flexible ticket,any time",
            "Anytime tickets let you travel on any train on your chosen route on the date shown. "
            "Most flexible but usually the most expensive."
        ),
        (
            "advance",
            "advance ticket,book ahead,cheap ticket,cheapest",
            "Advance tickets are the cheapest fares but must be booked in advance and are only valid "
            "on the specific train shown. Non-changeable and non-refundable."
        ),
        (
            "single",
            "one way,one-way,single ticket",
            "A single ticket covers one-way travel from your departure to your destination on the date shown."
        ),
        (
            "return",
            "return ticket,round trip,two way,coming back",
            "A return ticket covers travel to your destination and back. "
            "Open returns are valid for a month on the return leg. Day returns must be used on the same day."
        ),
        (
            "railcard",
            "rail card,discount card,16-25,two together,family card,network card,senior card",
            "Railcards give you a third off most fares. Common ones include the 16-25 Railcard, "
            "Senior Railcard (60+), Two Together, Family & Friends, and Network Railcard. "
            "Some peak hour restrictions apply."
        ),
        (
            "delay repay",
            "delay compensation,compensation,late train refund,money back delay",
            "Delay Repay lets you claim compensation for delayed trains. Roughly: 25% back for 15-29 min, "
            "50% for 30-59 min, 100% for 60-119 min, and 100% plus return fare for 120+ min. "
            "Claim via the train operator's website within 28 days."
        ),
        (
            "refund",
            "cancel ticket,get money back,unused ticket",
            "Unused Anytime and Off-Peak tickets can usually be refunded before travel (minus an admin fee of around £10). "
            "Advance tickets are non-refundable but can sometimes be exchanged before departure."
        ),
        (
            "split ticketing",
            "split ticket,split fare,two tickets,cheaper route",
            "Split ticketing means buying two or more tickets covering different parts of your journey "
            "instead of one through ticket. It can be much cheaper on some routes - "
            "you stay on the same train throughout."
        ),
        (
            "season ticket",
            "weekly ticket,monthly ticket,annual ticket,commuter pass",
            "Season tickets give unlimited travel between two stations for a set period. "
            "They suit regular commuters and can be loaded onto a smartcard."
        ),
        (
            "e-ticket",
            "mobile ticket,digital ticket,phone ticket,barcode ticket",
            "E-tickets are digital and stored on your phone or in your email. "
            "They show a barcode scanned at the gate or by the conductor. Most operators now accept them."
        ),
        (
            "first class",
            "first class ticket,upgrade,premium",
            "First Class offers more spacious seating and sometimes food and drink. "
            "It costs significantly more than Standard class."
        ),
        (
            "south western railway",
            "south western,swr,weymouth,waterloo,swt",
            "South Western Railway runs services between London Waterloo and Weymouth, Bournemouth, "
            "Portsmouth, Southampton, and Guildford. They participate in Delay Repay."
        ),
        (
            "national rail",
            "national rail enquiries,rail enquiries,uk trains",
            "National Rail is the umbrella brand for Britain's rail network. "
            "You can plan journeys and check live departures at nationalrail.co.uk."
        ),
        (
            "wheelchair",
            "disabled,accessibility,assistance,mobility",
            "All UK train stations must provide assistance for disabled passengers. "
            "Book via Passenger Assist (nationalrail.co.uk) up to 2 hours before travel."
        ),
        (
            "lost property",
            "lost item,left on train,forgot,left behind",
            "Contact the train operator directly as soon as possible. "
            "Items found at stations are usually held for 24 hours before being sent to a central lost property office."
        ),
    ]

    conn = get_connection()
    c = conn.cursor()
    for keyword, synonyms, answer in entries:
        c.execute(
            "INSERT OR IGNORE INTO knowledge (keyword, synonyms, answer, created_at) VALUES (?, ?, ?, ?)",
            (keyword, synonyms, answer, datetime.now().isoformat())
        )
    conn.commit()
    conn.close()


def create_session() -> int:
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO sessions (started_at) VALUES (?)", (datetime.now().isoformat(),))
    sid = c.lastrowid
    conn.commit()
    conn.close()
    return sid


def close_session(session_id: int, task_completed: str = None):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "UPDATE sessions SET ended_at = ?, task_completed = ? WHERE id = ?",
        (datetime.now().isoformat(), task_completed, session_id)
    )
    conn.commit()
    conn.close()


def log_message(session_id: int, turn: int, role: str, message: str):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO conversations (session_id, turn, role, message, timestamp) VALUES (?, ?, ?, ?, ?)",
        (session_id, turn, role, message, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


def get_conversation_history(session_id: int) -> list:
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "SELECT turn, role, message, timestamp FROM conversations WHERE session_id = ? ORDER BY turn ASC",
        (session_id,)
    )
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def get_all_sessions() -> list:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM sessions ORDER BY started_at DESC")
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def get_all_knowledge() -> list:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, keyword, synonyms, answer, created_at FROM knowledge ORDER BY keyword ASC")
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def add_knowledge(keyword: str, synonyms: str, answer: str) -> bool:
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute(
            "INSERT INTO knowledge (keyword, synonyms, answer, created_at) VALUES (?, ?, ?, ?)",
            (keyword.strip().lower(), synonyms.strip().lower(), answer.strip(), datetime.now().isoformat())
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def delete_knowledge(entry_id: int):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM knowledge WHERE id = ?", (entry_id,))
    conn.commit()
    conn.close()
