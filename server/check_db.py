import os
import psycopg2
from psycopg2.extras import RealDictCursor

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

    print(f"🔍 Connecting to Supabase/PostgreSQL...")
    try:
        # sslmode='require' 추가
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor, connect_timeout=10, sslmode='require')
        with conn.cursor() as cur:
            # public 스키마 명시
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            tables = [r['table_name'] for r in cur.fetchall()]
            print(f"✅ TABLES: {tables}")

            if 'user_best' in tables:
                cur.execute("SELECT COUNT(*) as count FROM public.user_best")
                count = cur.fetchone()['count']
                print(f"✅ TOTAL ROWS IN public.user_best: {count}")

                cur.execute("SELECT nickname, score FROM public.user_best ORDER BY score DESC LIMIT 5")
                rows = cur.fetchall()
                print("--- TOP 5 ---")
                for r in rows:
                    print(f"- {r['nickname']}: {r['score']}")
            else:
                print("⚠️ WARNING: 'user_best' table not found in public schema.")
            
        conn.close()
    except Exception as e:
        print(f"❌ DB Check Failed: {e}")

if __name__ == "__main__":
    check_db()
