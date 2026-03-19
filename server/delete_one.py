import os
import psycopg2
from psycopg2.extras import RealDictCursor

def get_db_url():
    url = os.getenv("DATABASE_URL")
    if url and url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url

DATABASE_URL = get_db_url()
nickname_to_delete = "INIT"

def delete_one():
    if not DATABASE_URL:
        print("❌ ERROR: DATABASE_URL is not set.")
        return

    try:
        # sslmode='require' 추가
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor, connect_timeout=10, sslmode='require')
        with conn.cursor() as cur:
            # public 스키마 명시
            cur.execute("DELETE FROM public.user_best WHERE nickname = %s", (nickname_to_delete,))
            print(f"삭제된 행 수: {cur.rowcount}")
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"❌ Deletion failed: {e}")

if __name__ == "__main__":
    delete_one()
