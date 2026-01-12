import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "leaderboard.db"

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cur.fetchall()

print("TABLES:", tables)

conn.close()
