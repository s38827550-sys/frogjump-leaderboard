# 🌐 Frog Jump Leaderboard (Server)

![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg)
![SQLite](https://img.shields.io/badge/Database-SQLite-003B57.svg)

Frog Jump Game의 점수를 기록하고 순위를 관리하는 백엔드 API 서버입니다.

## 🚀 핵심 로직
> **Status**: **2026-03-18 PostgreSQL 전면 리팩토링 및 안정화.**
> - **자동 URL 변환**: `postgres://` 형식을 `postgresql://`로 자동 인식하여 클라우드 환경(Heroku, Render) 오류 방지.
> - **Pydantic v2 & Python 3.12+ 지원**: 최신 라이브러리 환경에서도 경고 없이 안정적으로 작동.
> - **UPSERT & Indexing**: PostgreSQL 전용 구문(`ON CONFLICT`) 및 인덱스 추가로 리더보드 조회 성능 최적화.

- **최고 점수 갱신 (Upsert)**: 동일한 닉네임으로 점수 등록 시, 기존 기록보다 높은 점수일 때만 데이터베이스를 업데이트합니다.
- **동시성 최적화**: PostgreSQL의 견고한 트랜잭션과 인덱싱으로 다수 사용자의 점수 등록을 안전하게 처리합니다.
- **상세 로깅**: 서버 상태 및 오류 상황을 로그로 기록하여 유지보수성을 높였습니다.

## 🔌 API Endpoints
- `POST /scores`: 점수 등록 (nickname, score) - 최고점일 때만 갱신됨.
- `GET /leaderboard?limit=50`: 실시간 상위 순위 목록 조회.
- `GET /health`: 서버 및 DB 연결 상태 정밀 진단.

## 📦 설치 및 실행
```bash
# 환경 변수 설정 필수
export DATABASE_URL="postgresql://user:pass@host:port/db"

pip install -r requirements.txt
cd server
uvicorn app:app --host 0.0.0.0 --port 8000
```
