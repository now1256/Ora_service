"""
TTS WebSocket 서버 - 외부 클라이언트가 연결하여 오디오 데이터를 수신
"""
import json
import asyncio
import logging
import base64
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class TtsWebSocketConsumer(AsyncWebsocketConsumer):
    """TTS WebSocket 서버 - 외부 클라이언트로부터 연결을 받고 오디오 데이터 전송"""

    # 클래스 레벨 변수로 연결된 클라이언트 관리
    connected_clients: Dict[str, 'TtsWebSocketConsumer'] = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.phone_id = None
        self.session_id = None
        self.is_connected = False

    async def connect(self):
        """WebSocket 연결 수락"""
        try:
            logger.info(f"🔌 WebSocket 연결 시도 - 경로: {self.scope.get('path')}")
            logger.info(f"   스코프 정보: type={self.scope.get('type')}, scheme={self.scope.get('scheme')}")

            # URL 파라미터 또는 헤더에서 정보 추출
            headers = dict(self.scope['headers'])

            # 헤더 정보 로깅
            for key, value in headers.items():
                if key in [b'phone-id', b'session-id', b'host', b'user-agent']:
                    logger.info(f"   헤더: {key.decode()}: {value.decode()}")

            self.phone_id = headers.get(b'phone-id', b'').decode() or self.scope['url_route']['kwargs'].get('phone_id', 'unknown')
            self.session_id = headers.get(b'session-id', b'').decode() or self.scope['url_route']['kwargs'].get('session_id', 'unknown')

            logger.info(f"📱 클라이언트 정보 추출: phone_id={self.phone_id}, session_id={self.session_id}")

            # 연결 수락
            await self.accept()
            self.is_connected = True

            # 클라이언트 등록
            client_key = f"{self.phone_id}_{self.session_id}"
            TtsWebSocketConsumer.connected_clients[client_key] = self

            logger.info(f"✅ WebSocket 클라이언트 연결 성공: phone_id={self.phone_id}, session_id={self.session_id}")
            logger.info(f"   현재 연결된 클라이언트 수: {len(TtsWebSocketConsumer.connected_clients)}")

            # 연결 확인 메시지 전송
            await self.send(text_data=json.dumps({
                'type': 'connection_established',
                'message': 'TTS WebSocket 서버 연결 성공',
                'phone_id': self.phone_id,
                'session_id': self.session_id
            }))

        except Exception as e:
            logger.error(f"❌ WebSocket 연결 오류: {str(e)}", exc_info=True)
            await self.close()

    async def disconnect(self, close_code):
        """WebSocket 연결 해제"""
        self.is_connected = False

        # 클라이언트 등록 해제
        client_key = f"{self.phone_id}_{self.session_id}"
        if client_key in TtsWebSocketConsumer.connected_clients:
            del TtsWebSocketConsumer.connected_clients[client_key]

        logger.info(f"WebSocket 클라이언트 연결 해제: phone_id={self.phone_id}, close_code={close_code}")

    async def receive(self, text_data):
        """클라이언트로부터 메시지 수신"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')

            if message_type == 'ping':
                # Ping-Pong 처리
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'timestamp': data.get('timestamp')
                }))
            elif message_type == 'ready':
                # 클라이언트가 데이터 수신 준비 완료
                logger.info(f"클라이언트 준비 완료: {self.phone_id}")
            else:
                logger.info(f"메시지 수신: {message_type}")

        except json.JSONDecodeError:
            logger.error("잘못된 JSON 형식")
        except Exception as e:
            logger.error(f"메시지 처리 오류: {str(e)}")

    async def send_audio_data_binary(self, audio_data: bytes, filename: str, text: str,
                                    request_id: str, chunk_size: int = 3072):
        """WAV를 바이너리 청크로 직접 전송 (Spring Boot 명세 준수)"""
        import time
        from datetime import datetime
        import struct

        logger.info(f"🔵🔵🔵 send_audio_data_binary 메서드 시작!!!")
        logger.info(f"   self: {self}")
        logger.info(f"   self.is_connected: {self.is_connected}")
        logger.info(f"   self.phone_id: {self.phone_id}")
        logger.info(f"   self.session_id: {self.session_id}")
        logger.info(f"   📋 받은 request_id: '{request_id}'")

        try:
            if not self.is_connected:
                logger.warning(f"연결되지 않은 클라이언트: {self.phone_id}")
                return False

            # 전체 전송 시작 시간
            total_start_time = time.time()

            # WAV 파일 확인 로그
            if len(audio_data) > 44:  # WAV 헤더는 최소 44바이트
                riff = audio_data[:4]
                wave = audio_data[8:12]
                if riff == b'RIFF' and wave == b'WAVE':
                    logger.info(f"✅ WAV 파일 확인: RIFF/WAVE 헤더 정상")
                    logger.info(f"   WAV 크기: {len(audio_data):,} bytes")
                else:
                    logger.warning(f"⚠️ WAV 형식 확인 필요: {riff} / {wave}")

            # 청크 수 계산
            total_chunks = (len(audio_data) + chunk_size - 1) // chunk_size
            
            logger.info(f"📤 바이너리 청크 스트리밍 시작: {filename}")
            logger.info(f"   📊 원본 WAV: {len(audio_data):,} bytes")
            logger.info(f"   📦 청크 수: {total_chunks}개 ({chunk_size:,} bytes/청크 = {chunk_size/1024:.1f}KB)")

            # 1단계: 시작 메시지 전송 (JSON) - Spring Boot 명세에 맞게
            start_message = {
                'type': 'audio_start',
                'requestId': request_id,
                'fileName': filename,
                'totalChunks': total_chunks,
                'text': text,
                'sessionId': self.session_id,
                'phoneId': self.phone_id
            }
            
            logger.info(f"📨 시작 메시지 전송: {start_message}")
            await self.send(text_data=json.dumps(start_message, ensure_ascii=False))

            # 2단계: 오디오 데이터를 바이너리 청크로 전송
            chunks_start_time = time.time()
            bytes_sent = 0

            for chunk_index in range(total_chunks):
                if not self.is_connected:
                    logger.warning("연결이 끊어져 전송 중단")
                    return False

                # 청크 데이터 추출
                start_idx = chunk_index * chunk_size
                end_idx = min((chunk_index + 1) * chunk_size, len(audio_data))
                chunk_data = audio_data[start_idx:end_idx]

                # 바이너리 메시지 구조 (Spring Boot 명세):
                # [0-3 바이트]: 청크 인덱스 (Big-endian int32)
                # [4-7 바이트]: 전체 청크 수 (첫 번째 청크만)
                # [8~ 바이트]: 실제 오디오 데이터
                
                binary_message = bytearray()
                
                # 청크 인덱스 (4바이트, Big-endian)
                binary_message.extend(struct.pack('>I', chunk_index))
                
                # 첫 번째 청크인 경우 전체 청크 수 추가
                if chunk_index == 0:
                    # 전체 청크 수 (4바이트, Big-endian)
                    binary_message.extend(struct.pack('>I', total_chunks))
                
                # 실제 오디오 데이터 추가
                binary_message.extend(chunk_data)

                # 바이너리 전송
                await self.send(bytes_data=bytes(binary_message))
                
                bytes_sent += len(chunk_data)

                # 진행률 로깅
                if chunk_index == 0:
                    logger.info(f"🔹 첫 번째 청크 전송 (바이너리)")
                    logger.info(f"   청크 구조: [인덱스:{chunk_index}][전체수:{total_chunks}][데이터:{len(chunk_data)}bytes]")
                    logger.info(f"   바이너리 메시지 크기: {len(binary_message)} bytes")
                elif chunk_index == total_chunks - 1:
                    logger.info(f"🔹 마지막 청크 전송 (바이너리)")
                    logger.info(f"   청크 구조: [인덱스:{chunk_index}][데이터:{len(chunk_data)}bytes]")
                    logger.info(f"   바이너리 메시지 크기: {len(binary_message)} bytes")
                elif chunk_index % 10 == 0:
                    progress = (bytes_sent / len(audio_data)) * 100
                    elapsed = time.time() - chunks_start_time
                    speed = bytes_sent / elapsed / 1024 if elapsed > 0 else 0
                    logger.info(f"   📡 전송 진행: {progress:.1f}% ({chunk_index + 1}/{total_chunks} 청크)")
                    logger.info(f"      {bytes_sent:,}/{len(audio_data):,} bytes, 속도: {speed:.1f} KB/s")

                # 청크 간 짧은 지연 (네트워크 부하 방지)
                if chunk_index < total_chunks - 1:
                    await asyncio.sleep(0.001)  # 1ms 지연

            # 3단계: 완료 메시지 전송 (JSON) - Spring Boot 명세에 맞게
            complete_message = {
                'type': 'audio_complete',
                'requestId': request_id,
                'totalChunks': total_chunks,
                'fileName': filename
            }
            
            logger.info(f"📨 완료 메시지 전송: {complete_message}")
            await self.send(text_data=json.dumps(complete_message, ensure_ascii=False))

            # 전체 전송 시간 계산
            total_time = time.time() - total_start_time
            throughput = len(audio_data) / total_time / 1024  # KB/s

            logger.info(f"✅ WAV 바이너리 스트리밍 완료: {filename}")
            logger.info(f"   📊 원본 WAV: {len(audio_data):,} bytes")
            logger.info(f"   📦 전송 청크: {total_chunks}개")
            logger.info(f"   ⏱️ 전체 시간: {total_time:.3f}초")
            logger.info(f"   📈 전송 속도: {throughput:.1f} KB/s")
            logger.info(f"   💾 Base64 없이 직접 바이너리 전송 완료!")
            return True

            # 1단계: 전체 WAV를 Base64로 변환
            logger.info(f"🔄 WAV를 Base64로 변환 중...")
            encoding_start = time.time()
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            encoding_time = time.time() - encoding_start

            logger.info(f"   ✅ Base64 변환 완료: {len(audio_base64):,} bytes ({encoding_time:.3f}초)")

            # 2단계: Base64 문자열을 청크로 분할 (4KB 기본값)
            base64_length = len(audio_base64)
            total_chunks = (base64_length + chunk_size - 1) // chunk_size

            logger.info(f"📤 Base64 청크 스트리밍 시작: {filename}")
            logger.info(f"   📊 원본 WAV: {len(audio_data):,} bytes")
            logger.info(f"   🔄 Base64 크기: {base64_length:,} bytes")
            logger.info(f"   📦 청크 수: {total_chunks}개 ({chunk_size:,} bytes/청크 = {chunk_size/1024:.1f}KB)")

            # 파일명 생성 (TTS 서버 형식)
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"tts_{self.session_id}_{request_id}_{timestamp}.wav"

            # 3단계: Base64 문자열을 청크로 나누어 전송 (스프링부트 서버 형식)
            chunks_start_time = time.time()
            bytes_sent = 0

            for chunk_index in range(total_chunks):
                if not self.is_connected:
                    logger.warning("연결이 끊어져 전송 중단")
                    return False

                logger.info(f"   📦 청크 인덱스 번호 : {chunk_index + 1}/{total_chunks}")

                # Base64 문자열에서 청크 추출
                start_idx = chunk_index * chunk_size
                end_idx = min((chunk_index + 1) * chunk_size, base64_length)
                chunk_base64 = audio_base64[start_idx:end_idx]

                # 스프링부트 서버가 기대하는 형식으로 메시지 구성
                chunk_message = {
                    'audioDataBase64': chunk_base64,  # Base64로 인코딩된 WAV 청크
                    'fileName': filename,
                    'chunkIndex': chunk_index,
                    'isFirst': chunk_index == 0,
                    'metadata': {
                        'requestId': request_id,
                        'sessionId': self.session_id,
                        'phoneId': self.phone_id,
                        'text': text,
                        'engine': 'GPT-sovits',
                        'language': 'ko-KR'
                    }
                }

                # 마지막 청크인 경우 추가 정보
                if chunk_index == total_chunks - 1:
                    chunk_message['isLast'] = True
                    chunk_message['totalChunks'] = total_chunks

                # 첫 번째와 마지막 청크는 상세 로그
                if chunk_index == 0:
                    logger.info(f"🔹 첫 번째 청크 전송:")
                    logger.info(f"   fileName: {chunk_message['fileName']}")
                    logger.info(f"   chunkIndex: {chunk_message['chunkIndex']}")
                    logger.info(f"   isFirst: {chunk_message['isFirst']}")
                    logger.info(f"   audioDataBase64 길이: {len(chunk_message['audioDataBase64'])}")
                    logger.info(f"   metadata: {chunk_message['metadata']}")
                elif chunk_index == total_chunks - 1:
                    logger.info(f"🔹 마지막 청크 전송:")
                    logger.info(f"   isLast: {chunk_message.get('isLast')}")
                    logger.info(f"   totalChunks: {chunk_message.get('totalChunks')}")

                # JSON 문자열로 변환 (명확하게)
                json_str = json.dumps(chunk_message, ensure_ascii=False)

                # 디버깅: 실제 전송되는 데이터 확인
                if chunk_index == 0:
                    logger.info(f"🔍 전송할 JSON 메시지:")
                    logger.info(f"   타입: {type(json_str)}")
                    logger.info(f"   길이: {len(json_str)}")
                    logger.info(f"   앞 300자: {json_str[:300]}...")

                    # JSON 형식 검증
                    import json as json_module
                    try:
                        test_parse = json_module.loads(json_str)
                        logger.info(f"   ✅ JSON 유효성 검증 성공")
                    except Exception as e:
                        logger.error(f"   ❌ JSON 유효성 검증 실패: {e}")

                # WebSocket으로 JSON 텍스트 전송 - text_data 파라미터 명시적 사용
                await self.send(text_data=json_str)

                bytes_sent += len(chunk_base64)

                # 진행률 로깅 (10청크마다 또는 마지막)
                if chunk_index % 10 == 0 or chunk_index == total_chunks - 1:
                    progress = (bytes_sent / base64_length) * 100
                    elapsed = time.time() - chunks_start_time
                    speed = bytes_sent / elapsed / 1024 if elapsed > 0 else 0

                    logger.info(f"   📡 전송 진행: {progress:.1f}% ({chunk_index + 1}/{total_chunks} 청크)")
                    logger.info(f"      {bytes_sent:,}/{base64_length:,} bytes, 속도: {speed:.1f} KB/s")

                # 청크 간 짧은 지연 (네트워크 부하 방지)
                if chunk_index < total_chunks - 1:
                    await asyncio.sleep(0.001)  # 1ms 지연

            # 전송 완료 메시지 (별도로 전송)
            complete_message = {
                'status': 'complete',
                'totalChunks': total_chunks,
                'metadata': {
                    'requestId': request_id,
                    'sessionId': self.session_id,
                    'phoneId': self.phone_id,
                    'fileName': filename
                }
            }

            logger.info(f"🔹 완료 메시지 전송:")
            logger.info(f"   status: complete")
            logger.info(f"   totalChunks: {total_chunks}")
            logger.info(f"   metadata: {complete_message['metadata']}")

            # JSON 문자열로 변환
            complete_json = json.dumps(complete_message, ensure_ascii=False)
            logger.info(f"🔍 완료 메시지 JSON:")
            logger.info(f"   전체 내용: {complete_json}")

            # JSON 형식 검증
            try:
                test_parse = json.loads(complete_json)
                logger.info(f"   ✅ 완료 메시지 JSON 유효성 검증 성공")
            except Exception as e:
                logger.error(f"   ❌ 완료 메시지 JSON 유효성 검증 실패: {e}")

            # WebSocket으로 JSON 텍스트 전송 - text_data 파라미터 명시적 사용
            await self.send(text_data=complete_json)

            # 전체 전송 시간 계산
            total_time = time.time() - total_start_time
            throughput = base64_length / total_time / 1024  # KB/s

            logger.info(f"✅ WAV Base64 스트리밍 완료: {filename}")
            logger.info(f"   📊 원본 WAV: {len(audio_data):,} bytes")
            logger.info(f"   🔄 Base64: {base64_length:,} bytes")
            logger.info(f"   📦 전송 청크: {total_chunks}개")
            logger.info(f"   ⏱️ 전체 시간: {total_time:.3f}초 (Base64 변환 {encoding_time:.3f}초 포함)")
            logger.info(f"   📈 전송 속도: {throughput:.1f} KB/s")
            return True

        except Exception as e:
            logger.error(f"오디오 전송 오류: {str(e)}")

            # 에러 메시지 전송 (스프링부트 서버 형식)
            error_message = {
                'status': 'error',
                'message': str(e),
                'metadata': {
                    'requestId': request_id,
                    'sessionId': self.session_id,
                    'phoneId': self.phone_id
                }
            }
            await self.send(text_data=json.dumps(error_message))
            return False

    @classmethod
    async def send_to_client(cls, phone_id: str, session_id: str, audio_data: bytes,
                            filename: str, text: str, request_id: str, use_binary: bool = True):
        """특정 클라이언트에게 오디오 데이터 전송 (클래스 메서드)"""
        logger.info(f"🟢 send_to_client 호출됨!")
        logger.info(f"   phone_id: {phone_id}")
        logger.info(f"   session_id: {session_id}")
        logger.info(f"   filename: {filename}")
        logger.info(f"   request_id: {request_id}")
        logger.info(f"   audio_data 크기: {len(audio_data)} bytes")
        logger.info(f"   전송 방식: {'바이너리' if use_binary else 'Base64'}")

        client_key = f"{phone_id}_{session_id}"
        logger.info(f"   client_key: {client_key}")
        logger.info(f"   현재 연결된 클라이언트 목록: {list(cls.connected_clients.keys())}")

        consumer = cls.connected_clients.get(client_key)

        if consumer:
            logger.info(f"✅ 클라이언트 찾음: {client_key}")
            logger.info(f"   consumer 객체: {consumer}")
            logger.info(f"   is_connected: {consumer.is_connected}")

            if use_binary:
                logger.info(f"   📦 send_audio_data_binary 호출 시작...")
                result = await consumer.send_audio_data_binary(audio_data, filename, text, request_id)
            else:
                logger.info(f"   📦 send_audio_data 호출 시작...")
                result = await consumer.send_audio_data(audio_data, filename, text, request_id)

            logger.info(f"   📦 전송 결과: {result}")
            return result
        else:
            logger.warning(f"❌ 연결된 클라이언트를 찾을 수 없음: {client_key}")
            logger.warning(f"   현재 연결된 클라이언트: {list(cls.connected_clients.keys())}")
            return False
