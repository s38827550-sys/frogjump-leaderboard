# app.py (Pydantic v2.6+ & Supabase Optimized)
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

# .env 파일 로드 (로컬 테스트용)
load_dotenv()

# 로깅 설정 (Render 콘솔에서 확인 가능)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("FrogJump")

# DATABASE_URL 확인 및 변환 (postgres -> postgresql)
def get_db_url():
    url = os.getenv("DATABASE_URL") or os.getenv("DB_URL")
    if url and url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url

DATABASE_URL = get_db_url()

def get_db_conn():
    if not DATABASE_URL:
        logger.error("❌ DATABASE_URL is missing! Please set it in Render Environment.")
        raise ConnectionError("DATABASE_URL is missing.")
    
    # Supabase 안정성을 위해 sslmode=require 및 타임아웃 10초 설정
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
                # public 스키마 명시
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS public.user_best (
                        nickname TEXT PRIMARY KEY,
                        score INTEGER NOT NULL DEFAULT 0,
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                cur.execute("CREATE INDEX IF NOT EXISTS idx_user_best_score_updated ON public.user_best (score DESC, updated_at ASC)")
            conn.commit()
        logger.info("✅ Database connected and initialized.")
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    if DATABASE_URL:
        init_db()
    yield

app = FastAPI(title="FrogJump API", lifespan=lifespan)

# CORS 설정 (Vercel 웹 앱과의 통신 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Pydantic v2 전용 모델 정의
class ScoreIn(BaseModel):
    # Field(..., ...)를 사용하여 필수 필드임을 명시
    nickname: str = Field(..., min_length=1, max_length=16, description="User Nickname")
    score: int = Field(..., ge=0, le=999999, description="Game Score")

    # 닉네임 공백 검사 (Pydantic v2 최신 validator)
    @field_validator('nickname')
    @classmethod
    def clean_nickname(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError('Nickname cannot be empty')
        return cleaned

    # Pydantic v2 전용 설정
    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
        extra='ignore' # 예상치 못한 필드는 무시
    )

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
        logger.error(f"❌ Post score error: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

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
        logger.error(f"❌ Leaderboard query failed: {e}")
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
    logger.error(f"🚨 Unhandled system error: {exc}")
    return JSONResponse(status_code=500, content={"detail": "Critical server error"})
