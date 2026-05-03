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
    """
    Creates all tables if they do not already exist.
    Called once on startup.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at TEXT NOT NULL,
            ended_at TEXT,
            task_completed TEXT
        )
    """)

    cursor.execute("""
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

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alias TEXT NOT NULL UNIQUE,
            official_name TEXT NOT NULL
        )
    """)

    cursor.execute("""
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
    """
    Populates the stations table from StationNameAndCode.csv.
    Skips rows that already exist (based on alias uniqueness).
    """
    csv_path = os.path.join(os.path.dirname(__file__), "StationNameAndCode.csv")

    if not os.path.exists(csv_path):
        print("Warning: StationNameAndCode.csv not found. Stations table not seeded.")
        return

    conn = get_connection()
    cursor = conn.cursor()

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            if len(row) < 2:
                continue
            station_name = row[0].strip()
            code = row[1].strip()

            if station_name:
                cursor.execute(
                    "INSERT OR IGNORE INTO stations (alias, official_name) VALUES (?, ?)",
                    (station_name.lower(), station_name)
                )
            if code:
                cursor.execute(
                    "INSERT OR IGNORE INTO stations (alias, official_name) VALUES (?, ?)",
                    (code.lower(), station_name)
                )

    conn.commit()
    conn.close()


def seed_knowledge():
    """
    Populates the knowledge table with default Q&As if not already present.
    Uses INSERT OR IGNORE so existing entries are never overwritten.
    """
    entries = [
        (
            "off peak",
            "off-peak,quiet time,cheaper time,avoid busy",
            "Off-peak tickets are valid for travel outside of busy commuter periods. "
            "They are usually cheaper than Anytime tickets. Exact off-peak hours vary "
            "by route and operator, but are typically outside 06:30-09:30 and 16:00-19:00 on weekdays."
        ),
        (
            "peak",
            "peak time,rush hour,busy time,commuter",
            "Peak tickets are valid at any time but are priced for busy commuter periods, "
            "typically weekday mornings and evenings. They are the most expensive ticket type."
        ),
        (
            "anytime",
            "anytime ticket,any time,flexible ticket",
            "Anytime tickets allow travel on any train on your chosen route on the date shown. "
            "They are the most flexible but usually the most expensive option."
        ),
        (
            "advance",
            "advance ticket,book ahead,cheap ticket,cheapest",
            "Advance tickets are the cheapest fares available but must be booked in advance and "
            "are only valid on the specific train shown on the ticket. They cannot be changed or refunded."
        ),
        (
            "single",
            "one way,one-way,single ticket",
            "A single ticket covers one-way travel from your departure station to your destination. "
            "It is valid only on the date and, for Advance tickets, the specific train shown."
        ),
        (
            "return",
            "return ticket,round trip,two way,both ways,coming back",
            "A return ticket covers travel to your destination and back again. "
            "Open returns allow you to come back on any train within a month. "
            "Day returns are valid only on the day of travel."
        ),
        (
            "railcard",
            "rail card,discount card,senior card,young persons card,16-25,two together,family card,network card",
            "Railcards give you a discount (usually 1/3 off) on most rail fares. "
            "Popular railcards include: 16-25 Railcard, Senior Railcard (60+), Two Together Railcard, "
            "Family & Friends Railcard, and Network Railcard. Some restrictions apply during peak hours."
        ),
        (
            "delay repay",
            "delay compensation,compensation,refund delay,late train refund,money back delay",
            "Delay Repay is a compensation scheme run by most UK train operators. "
            "You can usually claim: 25% back for 15-29 min delay, 50% for 30-59 mins, "
            "100% for 60-119 mins, and 100% plus the return fare for 120+ mins. "
            "Claim via the train operator's website within 28 days."
        ),
        (
            "refund",
            "cancel ticket,get money back,unused ticket,ticket refund",
            "Unused Anytime and Off-Peak tickets can usually be refunded before travel, "
            "minus an admin fee (typically £10). Advance tickets are non-refundable but "
            "can sometimes be exchanged for a fee before departure."
        ),
        (
            "split ticketing",
            "split ticket,split fare,cheaper route,two tickets",
            "Split ticketing means buying two or more tickets for different parts of your journey "
            "instead of one through ticket. This can be significantly cheaper on some routes. "
            "The train does not stop mid-journey — you stay on the same service."
        ),
        (
            "season ticket",
            "weekly ticket,monthly ticket,annual ticket,commuter pass",
            "Season tickets give unlimited travel between two stations for a set period — "
            "weekly, monthly, or annual. They are cost-effective for regular commuters "
            "and can be loaded onto a smartcard."
        ),
        (
            "oyster",
            "oyster card,contactless,tfl,london zones",
            "Within London, you can use an Oyster card or contactless payment for National Rail "
            "services in the TfL zones. This is often cheaper than buying a paper ticket for "
            "short journeys within the capital."
        ),
        (
            "e-ticket",
            "mobile ticket,digital ticket,paperless,phone ticket,barcode ticket",
            "E-tickets are digital tickets stored on your phone or email. "
            "They display a barcode scanned at the gate or by the conductor. "
            "Most UK train operators now accept e-tickets."
        ),
        (
            "first class",
            "first class ticket,upgrade,business class,premium",
            "First Class tickets offer more spacious seating and sometimes complimentary food and drink. "
            "They cost significantly more than Standard class. Some operators allow upgrades on the day "
            "for a small fee if seats are available."
        ),
        (
            "bike",
            "bicycle,cycle,take my bike,cycling",
            "Most UK trains allow bicycles, but some require advance reservations on busy routes. "
            "Folding bikes can usually be taken on any train for free without a reservation. "
            "Check with your specific train operator before travelling."
        ),
        (
            "wheelchair",
            "disabled,accessibility,wheelchair access,assistance,mobility",
            "All UK train stations must provide assistance for passengers with disabilities. "
            "You can book Passenger Assist via National Rail up to 2 hours before travel. "
            "Most modern trains have designated wheelchair spaces and accessible toilets."
        ),
        (
            "group",
            "group ticket,group travel,travelling together,friends,groupsave",
            "GroupSave offers discounts for groups of 3-9 people travelling together on certain routes. "
            "Discounts vary by operator — some offer up to 34% off. Children under 5 travel free, "
            "and 5-15 year olds pay half the adult fare."
        ),
        (
            "south western railway",
            "south western,swr,weymouth,waterloo,swt",
            "South Western Railway operates services between London Waterloo and destinations including "
            "Weymouth, Bournemouth, Portsmouth, Southampton, and Guildford. "
            "They participate in the Delay Repay scheme."
        ),
        (
            "national rail",
            "national rail enquiries,rail enquiries,train info,uk trains",
            "National Rail is the umbrella brand for Britain's rail network. "
            "You can plan journeys and check live departures at nationalrail.co.uk. "
            "Tickets can be bought through National Rail or individual train operators."
        ),
        (
            "lost property",
            "lost item,left on train,forgot,left behind",
            "If you leave something on a train, contact the train operator directly as soon as possible. "
            "Each operator has its own lost property office. Items found at stations are usually held "
            "for 24 hours before being sent to a central lost property office."
        ),
    ]

    conn = get_connection()
    cursor = conn.cursor()

    for keyword, synonyms, answer in entries:
        cursor.execute(
            "INSERT OR IGNORE INTO knowledge (keyword, synonyms, answer, created_at) VALUES (?, ?, ?, ?)",
            (keyword, synonyms, answer, datetime.now().isoformat())
        )

    conn.commit()
    conn.close()


def create_session() -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO sessions (started_at) VALUES (?)",
        (datetime.now().isoformat(),)
    )
    session_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return session_id


def close_session(session_id: int, task_completed: str = None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE sessions SET ended_at = ?, task_completed = ? WHERE id = ?",
        (datetime.now().isoformat(), task_completed, session_id)
    )
    conn.commit()
    conn.close()


def log_message(session_id: int, turn: int, role: str, message: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO conversations (session_id, turn, role, message, timestamp) VALUES (?, ?, ?, ?, ?)",
        (session_id, turn, role, message, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


def get_conversation_history(session_id: int) -> list:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT turn, role, message, timestamp FROM conversations WHERE session_id = ? ORDER BY turn ASC",
        (session_id,)
    )
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def get_all_sessions() -> list:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sessions ORDER BY started_at DESC")
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def get_all_knowledge() -> list:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, keyword, synonyms, answer, created_at FROM knowledge ORDER BY keyword ASC")
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def add_knowledge(keyword: str, synonyms: str, answer: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
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
    cursor = conn.cursor()
    cursor.execute("DELETE FROM knowledge WHERE id = ?", (entry_id,))
    conn.commit()
    conn.close()