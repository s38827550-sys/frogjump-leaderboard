import os
import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.getenv("DATABASE_URL")

nickname_to_delete = "INIT"  # 삭제할 닉네임

def delete_one():
    if not DATABASE_URL:
        print("Error: DATABASE_URL environment variable is not set.")
        return

    try:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        with conn.cursor() as cur:
            cur.execute("DELETE FROM user_best WHERE nickname = %s", (nickname_to_delete,))
            print(f"삭제된 행 수: {cur.rowcount}")
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Deletion failed: {e}")

if __name__ == "__main__":
    delete_one()
