# TTS WebSocket 스트리밍 구현 문서

## 개요
TTS 데이터 전송을 기존 HTTP base64 방식에서 WebSocket 스트리밍 방식으로 개선하여 전송 시간을 단축했습니다.

## 주요 변경사항

### 1. TTS 서버 (TTS_server)

#### 새로 추가된 파일들
- `ai/websocket_client.py`: WebSocket 클라이언트 구현
- `ai/websocket_config.py`: WebSocket 설정 관리
- `test_websocket_tts.py`: 테스트 스크립트

#### 수정된 파일
- `ai/views.py`: WebSocket 전송 옵션 추가

### 2. LLM 서버 (LLM_server)

#### 수정된 파일
- `ai/utils/tts_client.py`: use_websocket 파라미터 추가

## 사용 방법

### API 파라미터

TTS API (`/api/convert-tts/`)에 다음 파라미터들이 추가되었습니다:

```json
{
  "text": "변환할 텍스트",
  "phoneId": "전화 ID",
  "sessionId": "세션 ID",
  "requestId": "요청 ID",
  "use_websocket": true,    // WebSocket 사용 여부 (기본값: true)
  "fire_and_forget": true    // Fire-and-forget 모드 (기본값: true)
}
```

### 전송 모드

1. **HTTP 모드** (`use_websocket: false`)
   - 기존 방식: base64로 인코딩된 전체 오디오를 HTTP POST로 전송
   - 전송 시간: 약 1.x초

2. **WebSocket Fire-and-forget 모드** (`use_websocket: true, fire_and_forget: true`)
   - 백그라운드에서 청크 단위로 스트리밍
   - 응답 즉시 반환 (전송 완료 대기 안함)
   - 가장 빠른 응답 시간

3. **WebSocket 동기 모드** (`use_websocket: true, fire_and_forget: false`)
   - 청크 단위로 스트리밍
   - 전송 완료까지 대기
   - 전송 성공/실패 확인 가능

## 설정

### 환경 변수

```bash
# OraServer WebSocket 엔드포인트
ORASERVER_WEBSOCKET_URL=ws://100.72.196.9:8080/ws/tts

# WebSocket 청크 크기 (바이트, 기본값: 32768)
WEBSOCKET_CHUNK_SIZE=32768

# 재연결 시도 횟수 (기본값: 3)
WEBSOCKET_MAX_RETRIES=3

# 기본 전송 방식 (websocket 또는 http)
DEFAULT_TRANSFER_METHOD=websocket

# Fire-and-forget 모드 기본값
DEFAULT_FIRE_AND_FORGET=true
```

### Django Settings

```python
# settings.py에 추가 가능한 설정들
ORASERVER_WEBSOCKET_URL = 'ws://100.72.196.9:8080/ws/tts'
WEBSOCKET_CHUNK_SIZE = 32768  # 32KB
WEBSOCKET_MAX_RETRIES = 3
DEFAULT_TRANSFER_METHOD = 'websocket'
DEFAULT_FIRE_AND_FORGET = True
```

## 테스트

### 테스트 스크립트 실행

```bash
cd TTS_server
python test_websocket_tts.py
```

### 테스트 항목
1. HTTP 전송 모드 테스트
2. WebSocket Fire-and-forget 모드 테스트
3. WebSocket 동기 모드 테스트
4. 성능 비교 테스트

## WebSocket 프로토콜

### 1. 연결 수립
```
WebSocket URL: ws://100.72.196.9:8080/ws/tts
Headers:
  - phone-id: 전화 ID
  - session-id: 세션 ID
```

### 2. 초기화 메시지
```json
{
  "type": "init",
  "session_id": "세션 ID",
  "phone_id": "전화 ID"
}
```

### 3. 데이터 청크 전송
```json
{
  "audioDataBase64": "base64 인코딩된 청크",
  "fileName": "파일명",
  "chunkIndex": 0,
  "isFirst": true,
  "metadata": {
    "sessionId": "세션 ID",
    "requestId": "요청 ID",
    "phoneId": "전화 ID",
    "text": "원본 텍스트",
    "engine": "GPT-sovits",
    "language": "ko-KR"
  }
}
```

### 4. 완료 메시지
```json
{
  "status": "complete",
  "totalChunks": 10,
  "metadata": { ... }
}
```

## 성능 개선

### 예상 개선 사항
- **전송 시간**: 1.x초 → 0.x초 (Fire-and-forget 모드)
- **청크 스트리밍**: 대용량 오디오도 메모리 효율적으로 전송
- **백그라운드 처리**: 응답 대기 없이 즉시 다음 작업 진행 가능

### 청크 크기 최적화
- 기본값: 32KB
- 네트워크 상황에 따라 조정 가능
- 작은 청크: 낮은 지연시간, 높은 오버헤드
- 큰 청크: 높은 처리량, 높은 지연시간

## 문제 해결

### WebSocket 연결 실패
1. OraServer의 WebSocket 엔드포인트 확인
2. 네트워크 방화벽 설정 확인
3. WebSocket 포트(8080) 개방 여부 확인

### 청크 전송 실패
1. 청크 크기 조정 (WEBSOCKET_CHUNK_SIZE)
2. 재연결 시도 횟수 증가 (WEBSOCKET_MAX_RETRIES)
3. 네트워크 안정성 확인

## 롤백 방법

WebSocket 사용을 비활성화하고 기존 HTTP 방식으로 전환:

1. 환경 변수 설정:
```bash
DEFAULT_TRANSFER_METHOD=http
```

2. 또는 API 호출 시 명시:
```json
{
  "use_websocket": false,
  ...
}
```

## 모니터링

### 로그 확인
```bash
# TTS 서버 로그
tail -f TTS_server/logs/tts.log | grep WebSocket

# 주요 로그 메시지
# 🔌 [TTS] WebSocket 스트리밍 시작
# ✅ [TTS] WebSocket 백그라운드 스트리밍 시작
# ✅ [TTS] WebSocket 스트리밍 완료
```

### 성능 메트릭
- 전송 시간
- 청크 개수
- 성공/실패율
- 재연결 횟수

## 향후 개선 사항

1. **압축 지원**: 청크 데이터 압축으로 추가 성능 개선
2. **적응형 청크 크기**: 네트워크 상황에 따른 동적 청크 크기 조정
3. **멀티플렉싱**: 단일 WebSocket 연결로 여러 세션 처리
4. **재전송 메커니즘**: 실패한 청크만 선택적 재전송
5. **실시간 진행률**: 청크 전송 진행률 실시간 피드백