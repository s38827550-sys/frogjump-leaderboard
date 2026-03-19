import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor

# app.py와 동일한 URL 로직 사용
def get_db_url():
    url = os.getenv("DATABASE_URL")
    if url and url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url

DATABASE_URL = get_db_url()

def check_db():
    if not DATABASE_URL:
        print("❌ ERROR: DATABASE_URL is not set.")
        return

    print(f"🔍 Connecting to DB (URL starts with: {DATABASE_URL[:20]}...)")
    try:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor, connect_timeout=5)
        with conn.cursor() as cur:
            # 1. 테이블 존재 여부 확인
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            tables = [r['table_name'] for r in cur.fetchall()]
            print(f"✅ TABLES: {tables}")

            if 'user_best' in tables:
                # 2. 레코드 수 확인
                cur.execute("SELECT COUNT(*) as count FROM user_best")
                count = cur.fetchone()['count']
                print(f"✅ TOTAL ROWS: {count}")

                # 3. 상위 5개 미리보기
                cur.execute("SELECT nickname, score FROM user_best ORDER BY score DESC LIMIT 5")
                rows = cur.fetchall()
                print("--- TOP 5 ---")
                for r in rows:
                    print(f"- {r['nickname']}: {r['score']}")
            else:
                print("⚠️ WARNING: 'user_best' table not found.")
            
        conn.close()
    except Exception as e:
        print(f"❌ DB Check Failed: {e}")

if __name__ == "__main__":
    check_db()
