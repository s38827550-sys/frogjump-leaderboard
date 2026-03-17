# 🌐 Frog Jump Leaderboard (Server)

![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg)
![SQLite](https://img.shields.io/badge/Database-SQLite-003B57.svg)

Frog Jump Game의 점수를 기록하고 순위를 관리하는 백엔드 API 서버입니다.

## 🚀 핵심 로직
- **최고 점수 갱신 (Upsert)**: 동일한 닉네임으로 점수 등록 시, 기존 기록보다 높은 점수일 때만 데이터베이스를 업데이트합니다.
- **동시성 최적화**: SQLite의 `WAL(Write-Ahead Logging)` 모드를 사용하여 여러 사용자가 동시에 점수를 등록해도 안전하게 처리합니다.
- **CORS 완화**: 모든 도메인(`*`)에서의 접근을 허용하여 Vercel 등 외부 웹 서비스와 원활하게 통신합니다.

## 🔌 API Endpoints
- `POST /scores`: 점수 등록 (nickname, score) - 최고점일 때만 갱신됨.
- `GET /leaderboard?limit=50`: 실시간 상위 순위 목록 조회.
- `GET /health`: 서버 상태 및 DB 연결 확인.

## 📦 설치 및 실행
```bash
pip install -r requirements.txt
cd server
uvicorn app:app --host 0.0.0.0 --port 8000
```
