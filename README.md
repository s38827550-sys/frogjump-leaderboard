# 🌐 Frog Jump Leaderboard (Server)

![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg)
![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL-336791.svg)
![Pydantic](https://img.shields.io/badge/Validation-Pydantic_v2-E92069.svg)

본 서버는 **Frog Jump Game**의 전 세계 사용자 점수를 실시간으로 수집하고 순위를 관리하는 **백엔드 API 시스템**입니다. 

## 🎯 주요 역할 및 기능
- **점수 실시간 수집 (`POST /scores`)**: 게임 클라이언트로부터 닉네임과 점수를 받아 안전하게 저장합니다.
- **최고 점수 자동 갱신 (UPSERT)**: 사용자가 기존보다 높은 점수를 달성했을 때만 데이터베이스를 갱신하여 최신 랭킹을 유지합니다.
- **글로벌 리더보드 제공 (`GET /leaderboard`)**: 상위 순위 목록을 정렬하여 게임 내 순위표와 외부 웹 대시보드에 실시간으로 제공합니다.
- **서버 상태 정밀 진단 (`GET /health`)**: 데이터베이스 연결 상태 및 서버의 생존 여부를 모니터링합니다.

## 🛠️ 최근 리팩토링 및 고도화 사항 (2026-03-18)
- **Supabase(PostgreSQL) 전환**: 로컬 SQLite의 한계를 넘어 클라우드 기반의 분산 데이터베이스로 전환하여 대규모 사용자 대응이 가능해졌습니다.
- **Pydantic v2 & Python 3.12+ 최적화**: 최신 파이썬 생태계에 맞춰 데이터 유효성 검사 로직을 전면 리팩토링하여 보안과 속도를 동시에 확보했습니다.
- **비동기(Async) 처리 도입**: 모든 API 엔드포인트를 비동기로 전환하여 동시 접속자가 많아도 멈춤 없는 빠른 응답을 보장합니다.
- **네트워크 안정성 강화**: SSL 보안 연결(`sslmode=require`)과 인덱싱 최적화를 통해 클라우드 환경에서의 데이터 전송 신뢰성을 극대화했습니다.

## 📦 시스템 구성 요소
- **Framework**: FastAPI (High-performance Async Web)
- **Database**: PostgreSQL (Managed by Supabase)
- **ORM/Driver**: Psycopg2-binary (PostgreSQL Driver)
- **Infrastructure**: Render (Auto-deployment from GitHub)
