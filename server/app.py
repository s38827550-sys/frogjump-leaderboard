# app.py (PostgreSQL / Supabase Version)
from __future__ import annotations
import os
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel, Field, ConfigDict, field_validator
import psycopg2
from psycopg2.extras import RealDictCursor

# .env 파일 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("FrogJump")

# DATABASE_URL 확인 및 변환
def get_db_url():
    url = os.getenv("DATABASE_URL") or os.getenv("DB_URL")
    if url and url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url

DATABASE_URL = get_db_url()

def get_db_conn():
    if not DATABASE_URL:
        raise ConnectionError("DATABASE_URL is missing.")
    return psycopg2.connect(
        DATABASE_URL, 
        cursor_factory=RealDictCursor, 
        connect_timeout=10, 
        sslmode='require'
    )

def init_db():
    try:
        with get_db_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS public.user_best (
                        nickname TEXT PRIMARY KEY,
                        score INTEGER NOT NULL DEFAULT 0,
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                cur.execute("CREATE INDEX IF NOT EXISTS idx_user_best_score_updated ON public.user_best (score DESC, updated_at ASC)")
            conn.commit()
        logger.info("Database schema verified.")
    except Exception as e:
        logger.error(f"Database init failed: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    if DATABASE_URL:
        init_db()
    yield

app = FastAPI(title="FrogJump API", lifespan=lifespan)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"]
)

class ScoreIn(BaseModel):
    nickname: str = Field(..., min_length=1, max_length=16)
    score: int = Field(..., ge=0, le=999999)

    @field_validator('nickname')
    @classmethod
    def nickname_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Nickname cannot be empty')
        return v.strip()

    model_config = ConfigDict(populate_by_name=True, str_strip_whitespace=True)

@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")

@app.post("/scores")
async def post_score(payload: ScoreIn):
    now = datetime.now(timezone.utc)
    try:
        with get_db_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO public.user_best (nickname, score, updated_at) 
                    VALUES (%s, %s, %s)
                    ON CONFLICT (nickname) DO UPDATE SET
                        score = CASE WHEN EXCLUDED.score > public.user_best.score THEN EXCLUDED.score ELSE public.user_best.score END,
                        updated_at = CASE WHEN EXCLUDED.score > public.user_best.score THEN EXCLUDED.updated_at ELSE public.user_best.updated_at END
                    RETURNING score;
                """, (payload.nickname, payload.score, now))
                row = cur.fetchone()
            conn.commit()
            
        best_score = row.get("score") if row else payload.score
        return {"ok": True, "best": int(best_score)}
    except Exception as e:
        logger.error(f"Post score error: {e}")
        raise HTTPException(status_code=500, detail="Database operation failed")

@app.get("/leaderboard")
async def get_leaderboard(limit: int = 50):
    limit = max(1, min(limit, 100))
    try:
        with get_db_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT nickname, score, updated_at
                    FROM public.user_best
                    ORDER BY score DESC, updated_at ASC
                    LIMIT %s
                """, (limit,))
                rows = cur.fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"Leaderboard query failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch leaderboard")

@app.get("/health")
async def health():
    try:
        if not DATABASE_URL:
            return JSONResponse(status_code=503, content={"status": "warning", "db": "not_configured"})
        with get_db_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        return {"status": "ok", "db": "connected"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "detail": str(e)})

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {exc}")
    return JSONResponse(status_code=500, content={"detail": str(exc)})
