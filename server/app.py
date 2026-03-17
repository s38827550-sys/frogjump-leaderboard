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

# =========================================================
# Configuration
# =========================================================

def _parse_allowed_origins() -> list[str]:
    raw = os.getenv("ALLOWED_ORIGINS", "*").strip()
    if not raw:
        return ["*"]
    if raw == "*":
        return ["*"]
    return [o.strip() for o in raw.split(",") if o.strip()]

ALLOWED_ORIGINS = _parse_allowed_origins()

# DB 경로 설정
DB_DIR = Path(os.getenv("DB_DIR", Path(__file__).resolve().parent))
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DB_DIR / "leaderboard.db"

# SQLite 연결 옵션
SQLITE_TIMEOUT_SECONDS = int(os.getenv("SQLITE_TIMEOUT_SECONDS", "10"))

def connect_db() -> sqlite3.Connection:
    conn = sqlite3.connect(
        DB_PATH,
        timeout=SQLITE_TIMEOUT_SECONDS,
        isolation_level=None,
        check_same_thread=False,
    )
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
        print("[DATABASE INIT ERROR]", repr(e))
        raise RuntimeError(f"Could not initialize database: {e}")

# =========================================================
# FastAPI lifespan (startup/shutdown)
# =========================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"=== Starting up: DB_PATH = {DB_PATH.resolve()} ===")
    init_db()
    yield
    print("=== Shutting down ===")

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
            conn.execute("""
                INSERT INTO user_best (nickname, score, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(nickname) DO UPDATE SET
                    updated_at = CASE WHEN excluded.score > user_best.score THEN excluded.updated_at ELSE user_best.updated_at END,
                    score = CASE WHEN excluded.score > user_best.score THEN excluded.score ELSE user_best.score END
            """, (payload.nickname, payload.score, now))

            row = conn.execute("SELECT score FROM user_best WHERE nickname = ?", (payload.nickname,)).fetchone()
            best = int(row[0]) if row else payload.score
            
        return {"ok": True, "saved": (payload.score == best), "best": best}
    except sqlite3.Error as e:
        print("[/scores SQLITE ERROR]", repr(e))
        raise HTTPException(status_code=500, detail="Database error")

@app.get("/leaderboard")
def get_leaderboard(limit: int = 50) -> list[dict[str, Any]]:
    limit = max(1, min(limit, 200))
    try:
        with connect_db() as conn:
            rows = conn.execute(
                "SELECT nickname, score, updated_at FROM user_best ORDER BY score DESC, updated_at ASC LIMIT ?",
                (limit,),
            ).fetchall()
        return [{"nickname": r[0], "score": int(r[1]), "created_at": r[2]} for r in rows]
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
