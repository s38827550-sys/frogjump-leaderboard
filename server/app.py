from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from datetime import datetime
import sqlite3
from pathlib import Path

app = FastAPI(title="FrogJumpGame Leaderboard")

# -------------------------
# CORS
# -------------------------
ALLOWED_ORIGINS = [
    "http://127.0.0.1:5500",
    "http://localhost:5500",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# -------------------------
# DB
# -------------------------
DB_PATH = Path(__file__).with_name("leaderboard.db")
print("[DB_PATH]", DB_PATH.resolve())
def init_db():
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS user_best (
                nickname TEXT PRIMARY KEY,
                score INTEGER NOT NULL,
                updated_at TEXT NOT NULL
            )
            """)

            # (선택) 기존 best_score 테이블이 있었다면 1회 마이그레이션
            # best_score가 없으면 그냥 넘어감
            try:
                row = conn.execute(
                    "SELECT nickname, score, created_at FROM best_score WHERE id=1"
                ).fetchone()
                if row:
                    conn.execute("""
                    INSERT OR IGNORE INTO user_best (nickname, score, updated_at)
                    VALUES (?, ?, ?)
                    """, (row[0], row[1], row[2]))
            except sqlite3.Error:
                pass

            conn.commit()
    except sqlite3.Error as e:
        # DB 초기화 실패는 서버가 정상 동작 못하므로 로그를 남기고 예외를 터뜨리는 편이 낫습니다.
        print("[init_db ERROR]", repr(e))
        raise
@app.on_event("startup")
def on_startup():
    print("=== FastAPI startup: init_db 실행 ===")
    print("DB_PATH =", DB_PATH.resolve())
    init_db()


# -------------------------
# Models
# -------------------------
class ScoreIn(BaseModel):
    nickname: str = Field(min_length=1, max_length=16)
    score: int = Field(ge=0, le=999999)

# -------------------------
# Routes
# -------------------------
@app.post("/scores")
def post_score(payload: ScoreIn):
    now = datetime.utcnow().isoformat()

    try:
        with sqlite3.connect(DB_PATH) as conn:
            # 원자적 업서트: nickname이 없으면 INSERT, 있으면 "더 큰 점수일 때만" UPDATE
            conn.execute("""
            INSERT INTO user_best (nickname, score, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(nickname) DO UPDATE SET
                score = CASE
                    WHEN excluded.score > user_best.score THEN excluded.score
                    ELSE user_best.score
                END,
                updated_at = CASE
                    WHEN excluded.score > user_best.score THEN excluded.updated_at
                    ELSE user_best.updated_at
                END
            """, (payload.nickname, payload.score, now))
            conn.commit()

            # 응답에 best를 정확히 내려주고 싶으면 마지막에 조회
            best = conn.execute(
                "SELECT score FROM user_best WHERE nickname = ?",
                (payload.nickname,),
            ).fetchone()[0]

        # saved 여부는 “이번 점수가 best가 되었는지”로 판단
        saved = (payload.score == best)
        return {"ok": True, "saved": saved, "best": best}

    except sqlite3.Error as e:
        print("[/scores SQLITE ERROR]", repr(e))
        raise HTTPException(status_code=500, detail="Database error")
    except Exception as e:
        print("[/scores ERROR]", repr(e))
        raise HTTPException(status_code=500, detail="Server error")

@app.get("/leaderboard")
def get_leaderboard(limit: int = 50):
    limit = max(1, min(limit, 200))

    try:
        with sqlite3.connect(DB_PATH) as conn:
            rows = conn.execute(
                "SELECT nickname, score, updated_at "
                "FROM user_best "
                "ORDER BY score DESC, updated_at ASC "
                "LIMIT ?",
                (limit,),
            ).fetchall()

        return [{"nickname": r[0], "score": r[1], "created_at": r[2]} for r in rows]

    except sqlite3.Error as e:
        print("[/leaderboard SQLITE ERROR]", repr(e))
        raise HTTPException(status_code=500, detail="Database error")
    except Exception as e:
        print("[/leaderboard ERROR]", repr(e))
        raise HTTPException(status_code=500, detail="Server error")

@app.delete("/scores/{nickname}")
def delete_score(nickname: str):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.execute("DELETE FROM user_best WHERE nickname = ?", (nickname,))
            conn.commit()
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Not found")
        return {"ok": True, "deleted": nickname}
    except sqlite3.Error:
        raise HTTPException(status_code=500, detail="Database error")
