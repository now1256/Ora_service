# consumers.py
import json
import asyncio
import base64
import os
import time
from channels.generic.websocket import AsyncWebsocketConsumer
from openai import AsyncOpenAI
import httpx
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class VoiceChatConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
    async def connect(self):
        try:
            headers = dict(self.scope['headers'])
            phone_Id = headers.get(b'phone-id', b'').decode()
            session_Id = headers.get(b'session-id', b'').decode()

            self.phone_Id = phone_Id
            self.session_id = session_Id

            await self.accept()
            logger.info(f"WebSocket 연결됨: phone_id={self.phone_Id}, session_id={self.session_id}")
            
            await self.send(text_data=json.dumps({
                'type': 'connection_established',
                'message': '음성 채팅 연결이 설정되었습니다.'
            }))
        except Exception as e:
            logger.error(f"WebSocket 연결 오류: {str(e)}")
            await self.close()
        
    async def disconnect(self, close_code):
        logger.info(f"WebSocket 연결 해제: phone_id={self.phone_Id}, close_code={close_code}")
        
    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            token = data.get("token", "").strip()
            request_Id = data.get("request_Id", "")
            
            if not token:
                await self.send_error("메시지가 비어있습니다.")
                return
                
            # 처리 시작 알림
            await self.send(text_data=json.dumps({
                'type': 'processing_start',
                'message': 'AI가 응답을 생성 중입니다...'
            }))
            
            # AI 응답 및 음성 생성
            await self.process_voice_chat(token, request_Id)
            
        except json.JSONDecodeError:
            await self.send_error("잘못된 JSON 형식입니다.")
        except Exception as e:
            logger.error(f"WebSocket 처리 오류: {str(e)}")
            await self.send_error(f"처리 중 오류가 발생했습니다: {str(e)}")
    
    async def send_error(self, message):
        try:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': message
            }))
        except Exception as e:
            logger.error(f"에러 메시지 전송 실패: {str(e)}")
    
    async def safe_send(self, data):
        """안전한 메시지 전송"""
        try:
            await self.send(text_data=json.dumps(data))
        except Exception as e:
            logger.error(f"메시지 전송 실패: {str(e)}")
            # 연결이 끊어진 경우 재연결 시도하지 않고 로그만 남김
    
    async def get_ai_response_streaming(self, user_input):
        """AI 응답 스트리밍 생성"""
        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system", 
                        "content": "당신은 친근하고 도움이 되는 AI 어시스턴트입니다. 한국어로 자연스럽고 따뜻하게 대답해주세요. 간결하게 답변하세요. 신속하게 대답을 해주어야해"
                    },
                    {"role": "user", "content": user_input}
                ],
                max_tokens=150,
                temperature=0.7,
                stream=True
            )
            
            full_response = ""
            chunk_count = 0
            
            async for chunk in response:
                chunk_count += 1
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    
                    # 실시간으로 청크 전송 (안전한 전송 사용)
                    await self.safe_send({
                        'type': 'text_chunk',
                        'chunk': content,
                        'chunk_number': chunk_count
                    })
            
            return full_response
            
        except Exception as e:
            logger.error(f"AI 응답 생성 오류: {str(e)}")
            return f"응답 생성 중 오류: {str(e)}"
    
    async def text_to_speech_async(self, text):
        """텍스트를 음성으로 변환하여 base64 반환"""
        try:
            response = await self.openai_client.audio.speech.create(
                model="tts-1",
                voice="alloy",
                input=text,
                speed=1.2,
                response_format="mp3"
            )
            
            # 바이너리 데이터를 base64로 인코딩
            audio_data = response.content
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            
            return audio_base64
            
        except Exception as e:
            logger.error(f"TTS 생성 오류: {str(e)}")
            return None
    
    async def send_to_external_server(self, payload_data):
        """다른 서버로 HTTP 전송 - 비동기 백그라운드 처리"""
        try:
            # 즉시 큐잉 알림 전송
            await self.safe_send({
                'type': 'external_send_queued',
                'message': '외부 서버 전송 준비 중...'
            })
            
            # 백그라운드에서 실제 전송 (WebSocket 연결에 영향 주지 않음)
            asyncio.create_task(self._background_send(payload_data))
            
        except Exception as e:
            logger.error(f"외부 서버 전송 큐잉 오류: {str(e)}")
    
    async def _background_send(self, payload_data):
        """백그라운드에서 실제 외부 서버 전송"""
        try:
            # 연결 풀 재사용으로 성능 향상
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(30.0, connect=10.0),
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
            ) as client:
                response = await client.post(
                    "http://100.72.196.9:8080/api/tts/receive",
                    json=payload_data,
                    headers={ "Content-Type": "application/json","Accept": "application/json"}
                )
                
                logger.info(f"외부 서버 응답: {response.status_code}")
                
                if response.status_code == 200:
                    # 성공 시에만 클라이언트에 알림 (연결이 살아있는 경우에만)
                    await self.safe_send({
                        'type': 'external_send_success',
                        'message': '외부 서버로 전송 완료'
                    })
                else:
                    logger.error(f"외부 서버 전송 실패: {response.status_code}")
                    await self.safe_send({
                        'type': 'external_send_error',
                        'message': f'외부 서버 전송 실패: {response.status_code}'
                    })
                    
        except asyncio.CancelledError:
            logger.info("외부 서버 전송이 취소됨")
        except Exception as e:
            logger.error(f"백그라운드 외부 서버 전송 오류: {str(e)}")
            await self.safe_send({
                'type': 'external_send_error',
                'message': f'외부 서버 전송 중 오류: {str(e)}'
            })

    async def process_voice_chat(self, user_input, request_Id):
        """전체 음성 채팅 처리 파이프라인"""
        start_time = time.time()
        
        try:
            # 1. AI 응답 생성
            full_response = await self.get_ai_response_streaming(user_input)
            
            response_time = time.time()
            await self.safe_send({
                'type': 'text_complete',
                'text_response': full_response,
                'response_time': round(response_time - start_time, 2)
            })
            
            if not full_response.strip():
                return
            
            # 2. TTS 생성
            await self.safe_send({
                'type': 'tts_start',
                'message': '음성 생성 중...'
            })
            
            audio_base64 = await self.text_to_speech_async(full_response)
            
            if audio_base64:
                tts_time = time.time()
                
                # 실제 데이터로 fileName, audioDataBase64, fileSize 생성
                timestamp = str(int(time.time()))
                file_name = f"tts_{self.phone_Id}_{timestamp}.mp3"
                file_size = len(base64.b64decode(audio_base64))
                
                # TTS 완성 데이터 구조
                tts_payload = {
                    "fileName": file_name,
                    "audioDataBase64": audio_base64,
                    "fileSize": file_size,
                    "status": "success",
                    "message": "TTS 변환 완료",
                    "metadata": {
                        "sessionId": self.session_id,
                        "requestId": request_Id,
                        "phoneId": self.phone_Id,
                        "text": full_response,
                        "engine": "OpenAI-TTS",
                        "language": "ko-KR",
                        "tts_time": round(tts_time - response_time, 2)
                    }
                }
                
                # 클라이언트에게 전송
                await self.safe_send(tts_payload)
                
                # 3. 외부 서버로 비동기 전송 (WebSocket 블로킹하지 않음)
                await self.send_to_external_server(tts_payload)
                
                total_time = time.time()
                await self.safe_send({
                    'type': 'process_complete',
                    'total_time': round(total_time - start_time, 2)
                })
            else:
                await self.send_error("음성 생성에 실패했습니다.")
                
        except Exception as e:
            logger.error(f"process_voice_chat 오류: {str(e)}")
            await self.send_error(f"음성 채팅 처리 중 오류가 발생했습니다: {str(e)}")