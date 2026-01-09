import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).with_name("leaderboard.db")  # app.py와 같은 폴더면 동일하게 맞춰주세요

nickname_to_delete = "INIT"  # 삭제할 닉네임

with sqlite3.connect(DB_PATH) as conn:
    cur = conn.execute("DELETE FROM user_best WHERE nickname = ?", (nickname_to_delete,))
    conn.commit()
    print("삭제된 행 수:", cur.rowcount)
