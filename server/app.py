# app.py (PostgreSQL / Supabase Version)
from __future__ import annotations
import os
import sys
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel, Field, ConfigDict, field_validator
import psycopg2
from psycopg2.extras import RealDictCursor

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("FrogJump")

# DATABASE_URL 확인 및 변환 (Heroku/Render/Supabase 호환용)
def get_db_url():
    url = os.getenv("DATABASE_URL")
    if url and url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url

DATABASE_URL = get_db_url()

def connect_db():
    if not DATABASE_URL:
        logger.error("DATABASE_URL is not set.")
        raise ConnectionError("DATABASE_URL is missing.")
    
    try:
        # Supabase 연결 최적화: sslmode='require' 및 타임아웃 설정
        return psycopg2.connect(
            DATABASE_URL, 
            cursor_factory=RealDictCursor, 
            connect_timeout=10,
            sslmode='require'
        )
    except Exception as e:
        logger.error(f"Failed to connect to Database: {e}")
        raise

def init_db():
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                # public 스키마 명시 (Supabase 기본값)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS public.user_best (
                        nickname TEXT PRIMARY KEY,
                        score INTEGER NOT NULL DEFAULT 0,
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                cur.execute("CREATE INDEX IF NOT EXISTS idx_user_best_score_updated ON public.user_best (score DESC, updated_at ASC)")
            conn.commit()
            logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error(f"Database init failed: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    if DATABASE_URL:
        init_db()
    else:
        logger.warning("Starting without DATABASE_URL.")
    yield

app = FastAPI(title="FrogJump API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"]
)

class ScoreIn(BaseModel):
    nickname: str = Field(min_length=1, max_length=16)
    score: int = Field(ge=0, le=999999)

    @field_validator('nickname')
    @classmethod
    def nickname_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError('Nickname cannot be empty')
        return v.strip()

    model_config = ConfigDict(populate_by_name=True)

@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")

@app.post("/scores")
def post_score(payload: ScoreIn):
    now = datetime.now(timezone.utc)
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                # public 스키마 명시 및 UPSERT 로직
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
def get_leaderboard(limit: int = 50):
    limit = max(1, min(limit, 100))
    try:
        with connect_db() as conn:
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
def health():
    try:
        if not DATABASE_URL:
            return JSONResponse(status_code=503, content={"status": "warning", "db": "not_configured"})
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        return {"status": "ok", "db": "connected"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "detail": str(e)})

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {exc}")
    return JSONResponse(status_code=500, content={"detail": str(exc)})
