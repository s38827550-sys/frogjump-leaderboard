# 🌐 Frog Jump Leaderboard (Server)

![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg)
![SQLite](https://img.shields.io/badge/Database-SQLite-003B57.svg)

Frog Jump Game의 점수를 기록하고 순위를 제공하는 백엔드 API 서버입니다.

## 🛠 기술 스택
- **Framework**: FastAPI (Python)
- **Database**: SQLite (WAL 모드 지원으로 동시성 향상)
- **Deployment**: OCI, Heroku, Local 등 지원

## 🚀 서버 실행 방법

### 1. 가상환경 설정 및 라이브러리 설치
```bash
python -m venv .venv
source .venv/Scripts/activate  # Windows
pip install -r requirements.txt
```

### 2. 서버 실행
```bash
cd server
uvicorn app:app --reload --host 0.0.0.1 --port 8000
```

## 🔌 API Endpoints

- `GET /leaderboard?limit=50`: 상위 순위 목록 조회
- `POST /scores`: 새로운 점수 등록 (nickname, score 필요)
- `GET /health`: 서버 상태 확인
- `GET /docs`: Swagger API 문서 확인

## 📦 데이터베이스 구조
- **Table**: `user_best`
  - `nickname` (TEXT, PK): 사용자 식별자
  - `score` (INTEGER): 최고 기록
  - `updated_at` (TEXT): 기록 갱신 시간
