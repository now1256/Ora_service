# Ora AI Server

AI 기반 음성 대화 시스템으로 STT(Speech-to-Text), LLM(Large Language Model), TTS(Text-to-Speech) 서비스가 연동된 마이크로서비스 아키텍처입니다.

## 🏗️ 프로젝트 구조

```
OraAiServer/
├── LLM_server/          # LLM 처리 서버 (포트: 8001)
├── STT_server/          # 음성 인식 서버 (포트: 8000)
├── TTS_server/          # 음성 합성 서버 (포트: 8002)
├── shared/              # 공통 모듈
└── docker-compose.yml   # Docker 서비스 설정
```

## 🎯 아키텍처 패턴

### Django MVT + 클린 아키텍처 + DDD
- **MVT (Model-View-Template)**: Django 기본 패턴
- **클린 아키텍처**: 레이어 분리 및 의존성 역전
- **DDD (Domain-Driven Design)**: 도메인 중심 설계

### 레이어 구조
```
Interface Layer    → 외부 요청/응답 처리
Application Layer → 유스케이스 및 워크플로우
Domain Layer      → 핵심 비즈니스 로직
Infrastructure    → 외부 시스템 연동
```

## 🚀 실행 방법

### 1. 전체 서비스 실행 (Docker Compose)
```bash
# 모든 서비스 시작
docker-compose up -d

# 특정 서비스만 시작
docker-compose up -d weaviate
docker-compose up -d redis
docker-compose up -d kafka
```

### 2. 개별 서버 실행
```bash
# LLM 서버 (포트: 8001)
cd LLM_server
python manage.py runserver 8001

# STT 서버 (포트: 8000)
cd STT_server
python manage.py runserver 8000

# TTS 서버 (포트: 8002)
cd TTS_server
python manage.py runserver 8002
```

### 3. Weaviate UI 실행
```bash
# Weaviate UI (포트: 8091)
docker run -e WEAVIATE_URL=http://localhost:8081 -e WEAVIATE_API_KEYS=secret -p 8091:3000 naaive/weaviate-ui:latest
```

## 📡 API 엔드포인트

### LLM 서버 (포트: 8001)
- `POST /api/process-text/` - 텍스트 처리 및 LLM 응답
- `POST /api/simple-llm/` - 간단한 LLM 처리
- `GET /api/weaviate-data/` - Weaviate 데이터 조회

### STT 서버 (포트: 8000)
- `POST /api/process-audio/` - 오디오 파일 처리
- `POST /api/test-text-to-llm/` - 텍스트 테스트

### TTS 서버 (포트: 8002)
- `POST /api/convert-tts/` - 텍스트를 음성으로 변환

## 🔧 주요 기술 스택

### 백엔드
- **Django**: 웹 프레임워크
- **Django REST Framework**: API 개발
- **LangChain**: LLM 처리
- **OpenAI**: GPT 모델 연동

### 데이터베이스 & 벡터 DB
- **SQLite**: 로컬 데이터베이스
- **Weaviate**: 벡터 데이터베이스
- **Redis**: 캐시 및 세션 관리

### 메시징 & 통신
- **Kafka**: 메시지 큐 (선택적)
- **HTTP**: 서비스 간 통신
- **WebSocket**: 실시간 통신

### 컨테이너 & 배포
- **Docker**: 컨테이너화
- **Docker Compose**: 멀티 서비스 관리

## 📊 서비스 포트 정보

| 서비스 | 포트 | 설명 |
|--------|------|------|
| LLM Server | 8001 | LLM 처리 및 워크플로우 |
| STT Server | 8000 | 음성 인식 서비스 |
| TTS Server | 8002 | 음성 합성 서비스 |
| Weaviate | 8081 | 벡터 데이터베이스 |
| Weaviate UI | 8091 | Weaviate 관리 인터페이스 |
| Redis | 6379 | 캐시 및 세션 |

## 🔄 데이터 흐름

```
음성 입력 → STT 서버 → 텍스트 변환 → LLM 서버 → AI 응답 → TTS 서버 → 음성 출력
    ↓           ↓           ↓           ↓           ↓           ↓
Weaviate ← 대화 기록 저장 ← 벡터 검색 ← 컨텍스트 분석 ← 개인화 응답
```

## 🛠️ 개발 환경 설정

### 필수 요구사항
- Python 3.8+
- Docker & Docker Compose
- Redis
- OpenAI API 키

### 환경 변수 설정
```bash
# .env 파일 생성
```

### 의존성 설치
```bash
# 각 서버별 requirements.txt 설치
pip install -r LLM_server/requirements.txt
pip install -r STT_server/requirements.txt
pip install -r TTS_server/requirements.txt
```

## 🧪 테스트 방법

### API 테스트
```bash
# LLM 서버 테스트
curl -X POST http://localhost:8001/api/process-text/ \
  -H "Content-Type: application/json" \
  -d '{"text": "안녕하세요", "phoneId": "test123", "sessionId": "session123", "requestId": "req123"}'

# Weaviate 데이터 확인
curl -X GET http://localhost:8001/api/weaviate-data/
```

## 📝 주요 기능

- **음성 인식**: 실시간 음성을 텍스트로 변환
- **AI 대화**: LangChain 기반 지능형 대화
- **음성 합성**: 텍스트를 자연스러운 음성으로 변환
- **대화 기록**: Weaviate를 통한 벡터 기반 대화 저장
- **개인화**: 사용자별 대화 컨텍스트 유지
- **확장성**: 마이크로서비스 아키텍처로 수평 확장 가능

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 📞 문의

프로젝트 관련 문의사항이 있으시면 이슈를 생성해주세요.

