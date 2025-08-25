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
        self.is_connected = False
        
    async def connect(self):
        try:
            headers = dict(self.scope['headers'])
            phone_Id = headers.get(b'phone-id', b'').decode()
            session_Id = headers.get(b'session-id', b'').decode()

            self.phone_Id = phone_Id
            self.session_id = session_Id
            self.is_connected = True

            await self.accept()
            logger.info(f"WebSocket 연결됨: phone_id={self.phone_Id}, session_id={self.session_id}")
            
            await self.send(text_data=json.dumps({
                'type': 'connection_established',
                'message': '음성 채팅 연결이 설정되었습니다.'
            }))
        except Exception as e:
            logger.error(f"WebSocket 연결 오류: {str(e)}")
            self.is_connected = False
            await self.close()
        
    async def disconnect(self, close_code):
        self.is_connected = False
        logger.info(f"WebSocket 연결 해제: phone_id={getattr(self, 'phone_Id', 'unknown')}, close_code={close_code}")
        
    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            token = data.get("token", "").strip()
            request_Id = data.get("request_Id", "")
            
            if not token:
                await self.send_error("메시지가 비어있습니다.")
                return
                
            # 처리 시작 알림
            await self.safe_send({
                'type': 'processing_start',
                'message': 'AI가 응답을 생성 중입니다...'
            })
            
            # AI 응답 및 음성 생성
            await self.process_voice_chat(token, request_Id)
            
        except json.JSONDecodeError:
            await self.send_error("잘못된 JSON 형식입니다.")
        except Exception as e:
            logger.error(f"WebSocket 처리 오류: {str(e)}")
            await self.send_error(f"처리 중 오류가 발생했습니다: {str(e)}")
    
    async def send_error(self, message):
        await self.safe_send({
            'type': 'error',
            'message': message
        })
    
    async def safe_send(self, data):
        """안전한 메시지 전송 - 연결 상태 확인"""
        if not self.is_connected:
            logger.warning("WebSocket 연결이 닫혀있어 메시지 전송을 건너뜁니다")
            return
            
        try:
            await self.send(text_data=json.dumps(data))
        except Exception as e:
            logger.error(f"메시지 전송 실패: {str(e)}")
            self.is_connected = False
    
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
                    
                    # 실시간으로 청크 전송
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
        """텍스트를 WAV 음성으로 변환하여 base64 반환"""
        try:
            # OpenAI TTS 생성 (MP3)
            response = await self.openai_client.audio.speech.create(
                model="tts-1",
                voice="alloy",
                input=text,
                speed=1.2,
                response_format="mp3"
            )
            
            mp3_data = response.content
            
            try:
                # MP3 → WAV 변환 (pydub 사용)
                import io
                from pydub import AudioSegment
                
                # MP3 로드
                mp3_buffer = io.BytesIO(mp3_data)
                audio = AudioSegment.from_mp3(mp3_buffer)
                
                # 8kHz 모노 WAV로 변환 (작은 크기 + 빠른 재생)
                audio_8khz = audio.set_frame_rate(8000).set_channels(1)
                
                # WAV로 내보내기
                wav_buffer = io.BytesIO()
                audio_8khz.export(wav_buffer, format="wav")
                wav_data = wav_buffer.getvalue()
                
                # Base64 인코딩
                wav_base64 = base64.b64encode(wav_data).decode('utf-8')
                return wav_base64
                
            except ImportError:
                return base64.b64encode(mp3_data).decode('utf-8')
                
        except Exception as e:
            logger.error(f"TTS 생성 오류: {str(e)}")
            return None
    
    async def send_audio_chunks_to_websocket(self, payload_data):
        """WebSocket으로 오디오를 청크 단위로 스트리밍 전송"""
        try:
            audio_base64 = payload_data["audioDataBase64"]
            file_name = payload_data["fileName"]
            file_size = payload_data["fileSize"]
            metadata = payload_data["metadata"]
            
            # 청크 크기 설정 (32KB 정도로 설정)
            chunk_size = 4 * 1024  # 32KB
            total_chunks = (len(audio_base64) + chunk_size - 1) // chunk_size
            
            logger.info(f"오디오 스트리밍 시작: {total_chunks}개 청크, 총 크기: {len(audio_base64)} bytes")
            
            # 1. 스트리밍 시작 알림
            await self.safe_send({
                'type': 'audio_streaming_start',
                'fileName': file_name,
                'fileSize': file_size,
                'totalChunks': total_chunks,
                'chunkSize': chunk_size,
                'metadata': metadata
            })
            
            # 2. 청크 단위로 전송
            for chunk_index in range(total_chunks):
                if not self.is_connected:
                    logger.warning("WebSocket 연결이 끊어져 스트리밍 중단")
                    break
                    
                start_idx = chunk_index * chunk_size
                end_idx = min((chunk_index + 1) * chunk_size, len(audio_base64))
                chunk_data = audio_base64[start_idx:end_idx]
                
                chunk_message = {
                    'type': 'audio_chunk',
                    'fileName': file_name,
                    'chunkIndex': chunk_index,
                    'totalChunks': total_chunks,
                    'chunkData': chunk_data,
                    'chunkSize': len(chunk_data),
                    'isLastChunk': chunk_index == total_chunks - 1
                }
                
                await self.safe_send(chunk_message)
                
                # 진행률 계산 및 알림 (10청크마다)
                if chunk_index % 10 == 0 or chunk_index == total_chunks - 1:
                    progress = ((chunk_index + 1) / total_chunks) * 100
                    await self.safe_send({
                        'type': 'audio_streaming_progress',
                        'fileName': file_name,
                        'progress': round(progress, 1),
                        'chunksCompleted': chunk_index + 1,
                        'totalChunks': total_chunks
                    })
                
            
            # 3. 스트리밍 완료 알림
            if self.is_connected:
                await self.safe_send({
                    'type': 'audio_streaming_complete',
                    'fileName': file_name,
                    'message': '오디오 스트리밍 완료',
                    'totalChunksSent': total_chunks
                })
                
                logger.info(f"오디오 스트리밍 완료: {file_name}, {total_chunks}개 청크 전송")
            
        except Exception as e:
            logger.error(f"오디오 스트리밍 오류: {str(e)}")
            await self.safe_send({
                'type': 'audio_streaming_error',
                'message': f'오디오 스트리밍 중 오류: {str(e)}'
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
                file_name = f"tts_{self.phone_Id}_{timestamp}.wav"
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
                
                # TTS 생성 완료 알림
                await self.safe_send({
                    'type': 'tts_complete',
                    'fileName': file_name,
                    'fileSize': file_size,
                    'message': 'TTS 변환 완료, 스트리밍 시작',
                    'metadata': tts_payload["metadata"]
                })
                
                # 3. WebSocket으로 오디오 청크 스트리밍
                await self.send_audio_chunks_to_websocket(tts_payload)
                
      
                
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