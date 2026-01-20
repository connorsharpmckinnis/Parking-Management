import sqlite3
import datetime
import os

DB_NAME = "parking_data.db"

def init_db():
    """Initializes the database with the required table."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS parking_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            occupied_count INTEGER,
            free_count INTEGER,
            total_slots INTEGER
        )
    ''')
    conn.commit()
    conn.close()

def log_data(occupied, free):
    """Logs the parking data to the database."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    timestamp = datetime.datetime.now().isoformat()
    total = occupied + free
    c.execute('''
        INSERT INTO parking_logs (timestamp, occupied_count, free_count, total_slots)
        VALUES (?, ?, ?, ?)
    ''', (timestamp, occupied, free, total))
    conn.commit()
    conn.close()
    print(f"[{timestamp}] Saved: Occupied={occupied}, Free={free}")

def get_recent_logs(limit=20):
    """Fetches recent logs for display."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT * FROM parking_logs ORDER BY id DESC LIMIT ?', (limit,))
    rows = c.fetchall()
    conn.close()
    return rows
