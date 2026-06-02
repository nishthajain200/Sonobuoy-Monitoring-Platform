"""
LOFAR Signature Database
SQLite-backed vessel acoustic signature store pre-loaded with synthetic demonstration
signatures for Surface Merchant, Warship, Submarine, Patrol, and Biological contacts.
"""
import sqlite3
import os
import pandas as pd

_DB_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', 'outputs', 'lofar_signatures.db'
)

SEED_VESSELS = [
    {
        "vessel_id": "VES-001",
        "vessel_name": "Surface Merchant (Type-A)",
        "vessel_class": "Merchant",
        "shaft_rate_hz": 5.0,
        "blade_count": 4,
        "description": "Large surface merchant — 4-blade fixed-pitch propeller. Shaft: 5 Hz, Blade: 20 Hz.",
        "lines": [
            (5.0,   "shaft",     1, 0.8),
            (10.0,  "shaft",     2, 0.6),
            (15.0,  "shaft",     3, 0.4),
            (20.0,  "blade",     1, 1.0),
            (40.0,  "blade",     2, 0.7),
            (60.0,  "blade",     3, 0.5),
            (120.0, "machinery", 1, 0.6),
            (240.0, "machinery", 2, 0.4),
        ],
    },
    {
        "vessel_id": "VES-002",
        "vessel_name": "Surface Warship (Type-B)",
        "vessel_class": "Warship",
        "shaft_rate_hz": 8.0,
        "blade_count": 5,
        "description": "Surface combatant — 5-blade controllable-pitch propeller. Shaft: 8 Hz, Blade: 40 Hz.",
        "lines": [
            (8.0,   "shaft",     1, 0.9),
            (16.0,  "shaft",     2, 0.7),
            (24.0,  "shaft",     3, 0.5),
            (40.0,  "blade",     1, 1.0),
            (80.0,  "blade",     2, 0.8),
            (160.0, "blade",     3, 0.6),
            (400.0, "machinery", 1, 0.7),
            (800.0, "machinery", 2, 0.4),
        ],
    },
    {
        "vessel_id": "VES-003",
        "vessel_name": "Diesel Submarine (Type-C)",
        "vessel_class": "Submarine",
        "shaft_rate_hz": 3.0,
        "blade_count": 7,
        "description": "Diesel-electric submarine — 7-blade skewed propeller. Shaft: 3 Hz, Blade: 21 Hz.",
        "lines": [
            (3.0,   "shaft",     1, 0.7),
            (6.0,   "shaft",     2, 0.5),
            (9.0,   "shaft",     3, 0.3),
            (21.0,  "blade",     1, 1.0),
            (42.0,  "blade",     2, 0.6),
            (63.0,  "blade",     3, 0.4),
            (50.0,  "machinery", 1, 0.8),
            (100.0, "machinery", 2, 0.5),
            (200.0, "machinery", 3, 0.3),
        ],
    },
    {
        "vessel_id": "VES-004",
        "vessel_name": "Fast Patrol Vessel (Type-D)",
        "vessel_class": "Patrol",
        "shaft_rate_hz": 12.0,
        "blade_count": 4,
        "description": "High-speed gas-turbine patrol craft — 4-blade propeller. Shaft: 12 Hz, Blade: 48 Hz.",
        "lines": [
            (12.0,   "shaft",     1, 0.9),
            (24.0,   "shaft",     2, 0.7),
            (36.0,   "shaft",     3, 0.5),
            (48.0,   "blade",     1, 1.0),
            (96.0,   "blade",     2, 0.7),
            (192.0,  "blade",     3, 0.4),
            (1000.0, "machinery", 1, 0.6),
        ],
    },
    {
        "vessel_id": "BIO-001",
        "vessel_name": "Cetacean — Humpback Whale",
        "vessel_class": "Biological",
        "shaft_rate_hz": None,
        "blade_count": None,
        "description": "Humpback whale low-frequency song patterns (20–2000 Hz).",
        "lines": [
            (80.0,  "call", 1, 1.0),
            (160.0, "call", 2, 0.8),
            (320.0, "call", 3, 0.5),
            (640.0, "call", 4, 0.3),
        ],
    },
]

CLASS_COLOURS = {
    "Merchant":   "#2196F3",
    "Warship":    "#F44336",
    "Submarine":  "#9C27B0",
    "Patrol":     "#FF9800",
    "Biological": "#4CAF50",
}


def _get_db_path():
    path = os.path.abspath(_DB_PATH)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return path


def _connect():
    return sqlite3.connect(_get_db_path())


def init_db():
    """Create tables and seed with default vessel signatures if empty."""
    conn = _connect()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS vessels (
            vessel_id    TEXT PRIMARY KEY,
            vessel_name  TEXT NOT NULL,
            vessel_class TEXT,
            shaft_rate_hz REAL,
            blade_count  INTEGER,
            description  TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS frequency_lines (
            id                 INTEGER PRIMARY KEY AUTOINCREMENT,
            vessel_id          TEXT NOT NULL,
            freq_hz            REAL NOT NULL,
            line_type          TEXT,
            harmonic           INTEGER,
            relative_amplitude REAL,
            FOREIGN KEY (vessel_id) REFERENCES vessels (vessel_id)
        )
    """)
    c.execute("SELECT COUNT(*) FROM vessels")
    if c.fetchone()[0] == 0:
        for v in SEED_VESSELS:
            c.execute(
                "INSERT INTO vessels VALUES (?,?,?,?,?,?)",
                (v["vessel_id"], v["vessel_name"], v["vessel_class"],
                 v["shaft_rate_hz"], v["blade_count"], v["description"])
            )
            for (fhz, ltype, harm, amp) in v["lines"]:
                c.execute(
                    "INSERT INTO frequency_lines "
                    "(vessel_id,freq_hz,line_type,harmonic,relative_amplitude) VALUES (?,?,?,?,?)",
                    (v["vessel_id"], fhz, ltype, harm, amp)
                )
    conn.commit()
    conn.close()


def get_all_vessels():
    conn = _connect()
    df = pd.read_sql("SELECT * FROM vessels", conn)
    conn.close()
    return df


def get_vessel_lines(vessel_id=None):
    conn = _connect()
    if vessel_id:
        df = pd.read_sql(
            """SELECT fl.*, v.vessel_name, v.vessel_class
               FROM frequency_lines fl
               JOIN vessels v ON fl.vessel_id = v.vessel_id
               WHERE fl.vessel_id = ?
               ORDER BY fl.freq_hz""",
            conn, params=(vessel_id,)
        )
    else:
        df = pd.read_sql(
            """SELECT fl.*, v.vessel_name, v.vessel_class
               FROM frequency_lines fl
               JOIN vessels v ON fl.vessel_id = v.vessel_id
               ORDER BY fl.vessel_id, fl.freq_hz""",
            conn
        )
    conn.close()
    return df


def add_vessel(vessel_id, vessel_name, vessel_class, shaft_rate_hz,
               blade_count, description, frequency_lines):
    """Insert or replace a vessel and its frequency lines."""
    conn = _connect()
    c = conn.cursor()
    c.execute(
        "INSERT OR REPLACE INTO vessels VALUES (?,?,?,?,?,?)",
        (vessel_id, vessel_name, vessel_class, shaft_rate_hz, blade_count, description)
    )
    c.execute("DELETE FROM frequency_lines WHERE vessel_id=?", (vessel_id,))
    for line in frequency_lines:
        c.execute(
            "INSERT INTO frequency_lines "
            "(vessel_id,freq_hz,line_type,harmonic,relative_amplitude) VALUES (?,?,?,?,?)",
            (vessel_id, line['freq_hz'], line.get('line_type', 'unknown'),
             line.get('harmonic', 1), line.get('relative_amplitude', 1.0))
        )
    conn.commit()
    conn.close()


def delete_vessel(vessel_id):
    conn = _connect()
    c = conn.cursor()
    c.execute("DELETE FROM frequency_lines WHERE vessel_id=?", (vessel_id,))
    c.execute("DELETE FROM vessels WHERE vessel_id=?", (vessel_id,))
    conn.commit()
    conn.close()
