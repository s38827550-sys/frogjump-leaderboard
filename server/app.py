# app.py
from __future__ import annotations

import os
import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy import create_engine

DATABASE_URL = os.environ["DATABASE_URL"]

# Supabase에서 복사한 URL이 postgres:// 로 시작하면 교체
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)

app = FastAPI()



print("### LOADED app.py ###")

# =========================================================
# Configuration
# =========================================================
def _parse_allowed_origins() -> list[str]:
    """
    ALLOWED_ORIGINS env 예:
      - "*"  (기본)
      - "https://example.com,https://www.example.com"
    """
    raw = os.getenv("ALLOWED_ORIGINS", "*").strip()
    if not raw:
        return ["*"]
    if raw == "*":
        return ["*"]
    return [o.strip() for o in raw.split(",") if o.strip()]


ALLOWED_ORIGINS = _parse_allowed_origins()

# DB_DIR env 예:
#   - (미설정) : app.py가 있는 폴더에 leaderboard.db 생성
#   - "/var/data" : (OCI 등) 디스크 유지 경로에 DB 생성
DB_DIR = Path(os.getenv("DB_DIR", Path(__file__).resolve().parent))
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DB_DIR / "leaderboard.db"
print("[DB_PATH]", DB_PATH.resolve())

# SQLite 연결 옵션
SQLITE_TIMEOUT_SECONDS = int(os.getenv("SQLITE_TIMEOUT_SECONDS", "10"))


def connect_db() -> sqlite3.Connection:
    """
    요청마다 새 connection을 열고 with 블록으로 자동 close하는 방식.
    WAL 모드 + timeout으로 'database is locked' 완화.
    """
    conn = sqlite3.connect(
        DB_PATH,
        timeout=SQLITE_TIMEOUT_SECONDS,
        isolation_level=None,          # autocommit 제어를 명확히 하고 싶으면 None 유지
        check_same_thread=False,       # FastAPI 동기 엔드포인트에서 안전한 편
    )
    # 안정성/동시성 개선 (가벼운 리더보드에 적합)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def init_db() -> None:
    try:
        with connect_db() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_best (
                    nickname TEXT PRIMARY KEY,
                    score INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL
                );
            """)
    except sqlite3.Error as e:
        print("[/scores SQLITE ERROR]", repr(e))
        raise HTTPException(status_code=500, detail=repr(e))





# =========================================================
# FastAPI lifespan (startup/shutdown)
# =========================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("=== FastAPI startup: init_db 실행 ===")
    print("DB_PATH =", DB_PATH.resolve())
    init_db()
    yield
    print("=== FastAPI shutdown ===")


app = FastAPI(title="FrogJumpGame Leaderboard", lifespan=lifespan)

# =========================================================
# CORS
# =========================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# =========================================================
# Models
# =========================================================
class ScoreIn(BaseModel):
    nickname: str = Field(min_length=1, max_length=16)
    score: int = Field(ge=0, le=999_999)


# =========================================================
# Routes
# =========================================================
@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")


@app.get("/health")
def health() -> dict[str, Any]:
    return {"ok": True}

@app.get("/__whoami")
def __whoami():
    return {
        "loaded": "server/app.py",
        "db_path": str(DB_PATH.resolve()),
        "cwd": os.getcwd(),
    }

@app.post("/scores")
def post_score(payload: ScoreIn) -> dict[str, Any]:
    now = datetime.utcnow().isoformat()

    try:
        with connect_db() as conn:
            # 원자적 업서트: nickname이 없으면 INSERT, 있으면 더 큰 점수일 때만 UPDATE
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

            best_row = conn.execute(
                "SELECT score FROM user_best WHERE nickname = ?",
                (payload.nickname,),
            ).fetchone()

        best = int(best_row[0]) if best_row else payload.score
        saved = (payload.score == best)
        return {"ok": True, "saved": saved, "best": best}

    except sqlite3.Error as e:
        print("[/scores SQLITE ERROR]", repr(e))
        raise HTTPException(status_code=500, detail="Database error")

@app.get("/leaderboard")
def get_leaderboard(limit: int = 50) -> list[dict[str, Any]]:
    limit = max(1, min(limit, 200))

    try:
        with connect_db() as conn:
            rows = conn.execute(
                "SELECT nickname, score, updated_at "
                "FROM user_best "
                "ORDER BY score DESC, updated_at ASC "
                "LIMIT ?",
                (limit,),
            ).fetchall()

        # 기존 응답 키 호환 유지(created_at)
        return [{"nickname": r[0], "score": int(r[1]), "created_at": r[2]} for r in rows]

    except sqlite3.Error as e:
        print("[/leaderboard SQLITE ERROR]", repr(e))
        raise HTTPException(status_code=500, detail="Database error")
    except Exception as e:
        print("[/leaderboard ERROR]", repr(e))
        raise HTTPException(status_code=500, detail="Server error")


@app.delete("/scores/{nickname}")
def delete_score(nickname: str) -> dict[str, Any]:
    try:
        with connect_db() as conn:
            cur = conn.execute("DELETE FROM user_best WHERE nickname = ?", (nickname,))
            deleted = cur.rowcount

        if deleted == 0:
            raise HTTPException(status_code=404, detail="Not found")

        return {"ok": True, "deleted": nickname}

    except sqlite3.Error as e:
        print("[/scores/{nickname} SQLITE ERROR]", repr(e))
        raise HTTPException(status_code=500, detail="Database error")
    
@app.get("/__debug/db")
def debug_db() -> dict[str, Any]:
    try:
        with connect_db() as conn:
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
            ).fetchall()
        return {
            "db_path": str(DB_PATH.resolve()),
            "tables": [t[0] for t in tables],
            "cwd": os.getcwd(),
            "allowed_origins": ALLOWED_ORIGINS,
        }
    except Exception as e:
        return {"ok": False, "error": repr(e), "db_path": str(DB_PATH.resolve()), "cwd": os.getcwd()}


@app.get("/__debug/whoami")
def debug_whoami() -> dict[str, Any]:
    return {
        "loaded": "app.py",
        "db_path": str(DB_PATH.resolve()),
        "cwd": os.getcwd(),
    }

