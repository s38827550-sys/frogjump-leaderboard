# 🌐 Frog Jump Leaderboard (Server)

![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg)
![SQLite](https://img.shields.io/badge/Database-SQLite-003B57.svg)

Frog Jump Game의 점수를 기록하고 순위를 관리하는 백엔드 API 서버입니다.

## 🚀 핵심 로직
> **Status**: **2026-03-18 Supabase(PostgreSQL) 전면 최적화.**
> - **SSL 보안 연결**: `sslmode=require` 강제로 Supabase 및 클라우드 DB와의 안전한 통신 보장.
> - **스키마 명시**: `public.user_best`와 같이 스키마를 명시하여 Supabase 환경에서의 쿼리 정확도 향상.
> - **연결 복원력**: `connect_timeout` 증가 및 상세 로깅으로 클라우드 환경의 일시적 지연에 대응.

- **최고 점수 갱신 (Upsert)**: 동일한 닉네임으로 점수 등록 시, 기존 기록보다 높은 점수일 때만 데이터베이스를 업데이트합니다.
- **동시성 최적화**: PostgreSQL의 견고한 트랜잭션과 인덱싱으로 다수 사용자의 점수 등록을 안전하게 처리합니다.

## 🔌 API Endpoints
- `POST /scores`: 점수 등록 (nickname, score) - 최고점일 때만 갱신됨.
- `GET /leaderboard?limit=50`: 실시간 상위 순위 목록 조회 (public 스키마 참조).
- `GET /health`: 서버 및 Supabase DB 연결 상태 정밀 진단.

## 📦 설치 및 실행
```bash
# Supabase DATABASE_URL 설정 (반드시 sslmode=require 포함 권장)
export DATABASE_URL="postgresql://postgres:[PASSWORD]@[HOST]:5432/postgres?sslmode=require"

pip install -r requirements.txt
cd server
uvicorn app:app --host 0.0.0.0 --port 8000
```
