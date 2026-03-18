# app.py (Final Production Version)
from __future__ import annotations
import os, sqlite3
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

DB_DIR = Path(os.getenv("DB_DIR", Path(__file__).resolve().parent))
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DB_DIR / "leaderboard.db"

def connect_db():
    conn = sqlite3.connect(DB_PATH, timeout=10, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;"); conn.execute("PRAGMA synchronous=NORMAL;")
    return conn

def init_db():
    with connect_db() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS user_best (nickname TEXT PRIMARY KEY, score INTEGER NOT NULL, updated_at TEXT NOT NULL)")

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db(); yield

app = FastAPI(title="FrogJump API", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False, allow_methods=["*"], allow_headers=["*"])

class ScoreIn(BaseModel):
    nickname: str = Field(min_length=1, max_length=16)
    score: int = Field(ge=0, le=999999)

@app.get("/", include_in_schema=False)
def root(): return RedirectResponse(url="/docs")

@app.post("/scores")
def post_score(payload: ScoreIn):
    now = datetime.utcnow().isoformat()
    try:
        with connect_db() as conn:
            conn.execute("""
                INSERT INTO user_best (nickname, score, updated_at) VALUES (?, ?, ?)
                ON CONFLICT(nickname) DO UPDATE SET
                updated_at = CASE WHEN excluded.score > user_best.score THEN excluded.updated_at ELSE user_best.updated_at END,
                score = CASE WHEN excluded.score > user_best.score THEN excluded.score ELSE user_best.score END
            """, (payload.nickname, payload.score, now))
            conn.commit()
            row = conn.execute("SELECT score FROM user_best WHERE nickname = ?", (payload.nickname,)).fetchone()
        return {"ok": True, "best": int(row[0])}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.get("/leaderboard")
def get_leaderboard(limit: int = 50):
    try:
        with connect_db() as conn:
            rows = conn.execute("SELECT nickname, score, updated_at FROM user_best ORDER BY score DESC, updated_at ASC LIMIT ?", (limit,)).fetchall()
        return [{"nickname": r[0], "score": r[1], "updated_at": r[2]} for r in rows]
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))
