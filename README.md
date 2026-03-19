# 🌐 Frog Jump Leaderboard (Server)

![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg)
![SQLite](https://img.shields.io/badge/Database-SQLite-003B57.svg)

Frog Jump Game의 점수를 기록하고 순위를 관리하는 백엔드 API 서버입니다.

## 🚀 핵심 로직
> **Status**: **2026-03-18 최신 클린 리팩토링.**
> - **미사용 모듈 제거**: `sys`, `psycopg2.pool` 등을 제거하고 `with` 컨텍스트 매니저로 간결한 연결 관리.
> - **Supabase 최적화**: `sslmode=require`와 `public` 스키마 명시로 안정성 유지.

- **최고 점수 갱신 (Upsert)**: 동일한 닉네임으로 점수 등록 시, 기존 기록보다 높은 점수일 때만 데이터베이스를 업데이트합니다.

## 🔌 API Endpoints
- `POST /scores`: 점수 등록 (nickname, score) - 최고점일 때만 갱신됨.
- `GET /leaderboard?limit=50`: 실시간 상위 순위 목록 조회.
- `GET /health`: 서버 및 DB 연결 상태 진단.

## 📦 설치 및 실행
```bash
# DATABASE_URL 설정 (sslmode=require 권장)
export DATABASE_URL="postgresql://postgres:[PASSWORD]@[HOST]:5432/postgres?sslmode=require"

pip install -r requirements.txt
cd server
uvicorn app:app --host 0.0.0.0 --port 8000
```
