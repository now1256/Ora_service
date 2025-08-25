# consumers.py
import json
import asyncio
import base64
import os
import time
import re
from channels.generic.websocket import AsyncWebsocketConsumer
from openai import AsyncOpenAI
import httpx
from django.conf import settings
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class StreamProcessor:
    """스트림 토큰을 모아서 처리하는 클래스 (중단 가능 + Pre-TTS)"""
    def __init__(self, session_id: str = "default_session"):
        self.session_id = session_id
        self.accumulated_text = ""  # 스트림 토큰들을 모아놓는 변수
        self.is_collecting = False
        self.start_time = None
        self.current_ai_task = None  # 현재 실행 중인 AI 태스크
        self.cancel_event = asyncio.Event()  # 중단 신호
        
        # Pre-TTS 관련 추가
        self.first_sentence_tts = None  # 첫 문장 TTS 결과 (base64)
        self.first_sentence_text = ""   # 첫 문장 텍스트
        self.is_first_sentence_ready = False
        self.pre_tts_task = None        # 미리 TTS 처리 태스크
        
    def add_token(self, token: str):
        """토큰을 누적 텍스트에 추가"""
        if not self.is_collecting:
            self.is_collecting = True
            self.start_time = time.time()
            logger.info(f"[{self.session_id}] 스트림 수집 시작")
        
        self.accumulated_text += token
        logger.info(f"[{self.session_id}] 토큰 추가: '{token}' (누적: {len(self.accumulated_text)}자)")
    
    def get_accumulated_text(self):
        """누적된 텍스트 반환"""
        return self.accumulated_text.strip()
    
    def reset(self):
        """상태 초기화"""
        elapsed = time.time() - self.start_time if self.start_time else 0
        logger.info(f"[{self.session_id}] 스트림 수집 완료: {len(self.accumulated_text)}자, {elapsed:.2f}초")
        
        text = self.accumulated_text.strip()
        self.accumulated_text = ""
        self.is_collecting = False
        self.start_time = None
        
        # Pre-TTS 관련 초기화
        self.first_sentence_tts = None
        self.first_sentence_text = ""
        self.is_first_sentence_ready = False
        if self.pre_tts_task and not self.pre_tts_task.done():
            self.pre_tts_task.cancel()
        self.pre_tts_task = None
        
        return text
    
    async def cancel_current_ai_task(self):
        """현재 진행 중인 AI 태스크 중단"""
        if self.current_ai_task and not self.current_ai_task.done():
            logger.info(f"[{self.session_id}] AI 태스크 중단 시작...")
            self.cancel_event.set()
            self.current_ai_task.cancel()
            
            try:
                await self.current_ai_task
            except asyncio.CancelledError:
                logger.info(f"[{self.session_id}] AI 태스크 중단 완료")
            
            self.current_ai_task = None
            self.cancel_event.clear()
        
        # Pre-TTS 태스크도 중단
        if self.pre_tts_task and not self.pre_tts_task.done():
            self.pre_tts_task.cancel()
            self.pre_tts_task = None
            self.first_sentence_tts = None
            self.first_sentence_text = ""
            self.is_first_sentence_ready = False

class VoiceChatConsumer(AsyncWebsocketConsumer):
    # 클래스 레벨에서 모든 클라이언트의 프로세서 관리
    stream_processors = {}
    
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

            # 스트림 프로세서 생성
            stream_processor = StreamProcessor(session_id=self.session_id)
            VoiceChatConsumer.stream_processors[self.phone_Id] = stream_processor

            await self.accept()
            logger.info(f"WebSocket 연결됨: phone_id={self.phone_Id}, session_id={self.session_id}")
            
            await self.send(text_data=json.dumps({
                'type': 'connection_established',
                'message': '음성 채팅 연결이 설정되었습니다.',
                'phone_Id': self.phone_Id,
                'session_id': self.session_id
            }))
        except Exception as e:
            logger.error(f"WebSocket 연결 오류: {str(e)}")
            self.is_connected = False
            await self.close()
        
    async def disconnect(self, close_code):
        self.is_connected = False
        logger.info(f"WebSocket 연결 해제: phone_id={getattr(self, 'phone_Id', 'unknown')}, close_code={close_code}")
        
        # 스트림 프로세서 정리
        if hasattr(self, 'phone_Id') and self.phone_Id in VoiceChatConsumer.stream_processors:
            processor = VoiceChatConsumer.stream_processors[self.phone_Id]
            
            # Pre-TTS 상태 로깅
            if processor.pre_tts_task:
                if processor.pre_tts_task.done():
                    logger.info(f"Pre-TTS 완료됨: ready={processor.is_first_sentence_ready}")
                else:
                    logger.info(f"Pre-TTS 진행 중이었음, 중단됨")
            else:
                logger.info(f"Pre-TTS 태스크 없음")
            
            await processor.cancel_current_ai_task()  # 진행 중인 AI 태스크 중단
            del VoiceChatConsumer.stream_processors[self.phone_Id]
            logger.info(f"스트림 프로세서 정리 완료: {self.phone_Id}")
        
    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            token = data.get("token", "")
            request_Id = data.get("request_id", "")
            
            logger.info(f"[{self.phone_Id}] 토큰 수신: '{token}', request_Id: '{request_Id}'")
            
            # 스트림 프로세서 가져오기
            processor = VoiceChatConsumer.stream_processors.get(self.phone_Id)
            if not processor:
                await self.send_error("스트림 프로세서를 찾을 수 없습니다.")
                return
            
            if token == '<eos>':
                # EOS 토큰 수신 - Pre-TTS 준비되었으면 즉시 전송, 그 후 AI 완료 대기
                accumulated_text = processor.get_accumulated_text()
                
                if accumulated_text:
                    logger.info(f"[{self.phone_Id}] EOS 수신, 즉시 처리 시작: '{accumulated_text[:50]}...'")
                    
                    await self.safe_send({
                        'type': 'eos_received',
                        'accumulated_text': accumulated_text,
                        'message': 'EOS 수신, 즉시 처리 시작...'
                    })
                    
                    # 1. Pre-TTS가 준비되어 있으면 즉시 전송 (AI 완료 전에!)
                    first_sentence_sent = False
                    if processor.is_first_sentence_ready and processor.first_sentence_tts:
                        logger.info(f"[{self.phone_Id}] Pre-TTS 준비됨, 즉시 전송 (AI 완료 대기 없음)")
                        await self.send_first_sentence_immediately(processor, request_Id)
                        first_sentence_sent = True
                    
                    # 2. 그 후에 AI 태스크 완료 대기
                    ai_response = None
                    if processor.current_ai_task:
                        if not processor.current_ai_task.done():
                            # 진행 중인 AI 태스크 완료 대기
                            logger.info(f"[{self.phone_Id}] 첫 문장 전송 완료, AI 응답 완료 대기...")
                            try:
                                ai_response = await processor.current_ai_task
                                logger.info(f"[{self.phone_Id}] AI 응답 완료: '{ai_response[:50]}...'")
                            except asyncio.CancelledError:
                                logger.warning(f"[{self.phone_Id}] AI 태스크가 중단되었습니다")
                            except Exception as e:
                                logger.error(f"[{self.phone_Id}] AI 태스크 처리 오류: {str(e)}")
                        else:
                            # 이미 완료된 AI 태스크 결과 가져오기
                            try:
                                ai_response = processor.current_ai_task.result()
                                logger.info(f"[{self.phone_Id}] 완료된 AI 응답 사용: '{ai_response[:50]}...'")
                            except Exception as e:
                                logger.error(f"[{self.phone_Id}] 완료된 AI 태스크 결과 오류: {str(e)}")
                    
                    # 3. AI 응답 처리
                    if ai_response:
                        if first_sentence_sent:
                            # 첫 문장은 이미 전송했으므로 나머지 부분만 처리
                            logger.info(f"[{self.phone_Id}] 첫 문장 이미 전송됨, 나머지 부분 TTS 처리")
                            await self.process_remaining_tts(ai_response, processor, request_Id)
                        else:
                            # Pre-TTS가 준비되지 않았으면 전체 TTS
                            logger.info(f"[{self.phone_Id}] Pre-TTS 미준비, 전체 TTS 처리")
                            await self.process_full_tts_fallback(ai_response, request_Id, accumulated_text)
                    else:
                        # AI 응답이 없으면 에러
                        if not first_sentence_sent:
                            logger.error(f"[{self.phone_Id}] AI 응답도 Pre-TTS도 없음")
                            await self.send_error("응답을 생성할 수 없습니다. 다시 시도해주세요.")
                        else:
                            logger.info(f"[{self.phone_Id}] 첫 문장만 전송됨, AI 응답 없음")
                    
                    # 상태 리셋
                    final_text = processor.reset()
                    processor.current_ai_task = None
                    
                else:
                    await self.send_error("누적된 텍스트가 없습니다.")
            else:
                # 일반 토큰 수신
                # 1. 기존 AI 태스크 중단
                await processor.cancel_current_ai_task()
                
                # 2. 토큰 추가
                processor.add_token(token)
                
                # 3. 새로운 AI 응답 시작
                accumulated_text = processor.get_accumulated_text()
                logger.info(f"[{self.phone_Id}] 새 토큰으로 AI 응답 재시작: '{accumulated_text[:50]}...'")
                
                processor.current_ai_task = asyncio.create_task(
                    self.get_ai_response_interruptible(accumulated_text, processor.cancel_event)
                )
                
                # 실시간 피드백 전송
                await self.safe_send({
                    'type': 'token_received',
                    'token': token,
                    'accumulated_text': accumulated_text,
                    'accumulated_length': len(accumulated_text),
                    'ai_restarted': True
                })
            
        except json.JSONDecodeError:
            await self.send_error("잘못된 JSON 형식입니다.")
        except Exception as e:
            logger.error(f"WebSocket 처리 오류: {str(e)}")
            await self.send_error(f"처리 중 오류가 발생했습니다: {str(e)}")
    
    def is_sentence_complete(self, text):
        """문장이 완성되었는지 체크"""
        sentence_endings = ['.', '!', '?', '다.', '요.', '니다.', '습니다.', '야.', '죠.', '네.', '어요.', '어.', '지.', '죠?', '까?', '나?']
        return any(text.rstrip().endswith(ending) for ending in sentence_endings)
    
    def extract_first_sentence(self, text):
        """첫 번째 문장 추출"""
        # 한국어 문장 끝 패턴
        sentence_pattern = r'[^.!?]*?[.!?다요니다습니다야죠네어지까나]\s*'
        match = re.search(sentence_pattern, text)
        if match:
            return match.group().strip()
        
        # 패턴 매치 실패 시 첫 20자 정도 반환
        if len(text) > 20:
            return text[:20].strip()
        return text.strip()
    
    async def prepare_first_sentence_tts(self, first_sentence, processor):
        """첫 문장 Pre-TTS 처리"""
        try:
            logger.info(f"[{self.phone_Id}] Pre-TTS 시작: '{first_sentence}'")
            
            start_time = time.time()
            audio_base64 = await self.text_to_speech_async(first_sentence)
            tts_time = time.time() - start_time
            
            if audio_base64:
                processor.first_sentence_tts = audio_base64
                processor.is_first_sentence_ready = True
                
                await self.safe_send({
                    'type': 'pre_tts_ready',
                    'first_sentence': first_sentence,
                    'audio_size': len(base64.b64decode(audio_base64)),
                    'tts_time': round(tts_time, 2),
                    'message': '첫 문장 음성 준비 완료'
                })
                
                logger.info(f"✅ [{self.phone_Id}] Pre-TTS 완료: {len(base64.b64decode(audio_base64))}B, {tts_time:.2f}초")
            else:
                logger.warning(f"❌ [{self.phone_Id}] Pre-TTS 실패")
            
        except asyncio.CancelledError:
            logger.info(f"[{self.phone_Id}] Pre-TTS 중단됨")
        except Exception as e:
            logger.error(f"❌ Pre-TTS 오류: {str(e)}")
            processor.is_first_sentence_ready = False
    
    async def send_first_sentence_immediately(self, processor, request_Id):
        """첫 문장 즉시 전송"""
        try:
            logger.info(f"[{self.phone_Id}] 첫 문장 즉시 전송 시작: '{processor.first_sentence_text}'")
            
            timestamp = str(int(time.time()))
            file_name = f"tts_first_{self.phone_Id}_{timestamp}.wav"
            file_size = len(base64.b64decode(processor.first_sentence_tts))
            
            first_payload = {
                "fileName": file_name,
                "audioDataBase64": processor.first_sentence_tts,
                "fileSize": file_size,
                "status": "first_part",
                "message": "첫 문장 즉시 재생",
                "metadata": {
                    "sessionId": self.session_id,
                    "requestId": request_Id,
                    "phoneId": self.phone_Id,
                    "part": "first_sentence",
                    "text": processor.first_sentence_text,
                    "engine": "OpenAI-TTS",
                    "language": "ko-KR"
                }
            }
            
            await self.safe_send({
                'type': 'first_sentence_ready',
                'fileName': file_name,
                'fileSize': file_size,
                'text': processor.first_sentence_text,
                'message': '첫 문장 즉시 재생 시작'
            })
            
            # 즉시 스트리밍 전송
            await self.send_audio_chunks_to_websocket(first_payload)
            
            logger.info(f"✅ [{self.phone_Id}] 첫 문장 즉시 전송 완료: {file_size}B")
            
        except Exception as e:
            logger.error(f"첫 문장 전송 오류: {str(e)}")
    
    async def process_remaining_tts(self, ai_response, processor, request_Id):
        """나머지 부분 TTS 처리"""
        try:
            # 첫 문장 제거한 나머지 부분 추출
            first_sentence = processor.first_sentence_text
            remaining_text = ai_response.replace(first_sentence, "", 1).strip()
            
            if remaining_text and len(remaining_text) > 3:  # 최소 길이 체크
                logger.info(f"[{self.phone_Id}] 나머지 부분 TTS 시작: '{remaining_text[:30]}...'")
                
                start_time = time.time()
                audio_base64 = await self.text_to_speech_async(remaining_text)
                tts_time = time.time() - start_time
                
                if audio_base64:
                    timestamp = str(int(time.time()))
                    file_name = f"tts_remaining_{self.phone_Id}_{timestamp}.wav"
                    file_size = len(base64.b64decode(audio_base64))
                    
                    remaining_payload = {
                        "fileName": file_name,
                        "audioDataBase64": audio_base64,
                        "fileSize": file_size,
                        "status": "remaining_part",
                        "message": "나머지 부분 TTS 완료",
                        "metadata": {
                            "sessionId": self.session_id,
                            "requestId": request_Id,
                            "phoneId": self.phone_Id,
                            "part": "remaining_text",
                            "text": remaining_text,
                            "full_response": ai_response,
                            "engine": "OpenAI-TTS",
                            "language": "ko-KR",
                            "tts_time": round(tts_time, 2)
                        }
                    }
                    
                    await self.safe_send({
                        'type': 'remaining_tts_ready',
                        'fileName': file_name,
                        'fileSize': file_size,
                        'text': remaining_text,
                        'tts_time': round(tts_time, 2),
                        'message': '나머지 부분 재생 시작'
                    })
                    
                    await self.send_audio_chunks_to_websocket(remaining_payload)
                    
                    logger.info(f"✅ [{self.phone_Id}] 나머지 부분 TTS 완료: {file_size}B, {tts_time:.2f}초")
                else:
                    logger.warning(f"[{self.phone_Id}] 나머지 부분 TTS 실패")
            else:
                logger.info(f"[{self.phone_Id}] 나머지 텍스트가 없거나 너무 짧음: '{remaining_text}'")
                
                await self.safe_send({
                    'type': 'no_remaining_text',
                    'message': '첫 문장으로 응답 완료'
                })
                
        except Exception as e:
            logger.error(f"나머지 TTS 처리 오류: {str(e)}")
    
    async def process_full_tts_fallback(self, ai_response, request_Id, original_input):
        """Pre-TTS가 없을 때 전체 TTS 처리 (통합 버전)"""
        start_time = time.time()
        
        try:
            logger.info(f"[{self.phone_Id}] 전체 TTS 처리 (fallback): '{ai_response[:50]}...'")
            
            await self.safe_send({
                'type': 'tts_processing_start',
                'ai_response': ai_response,
                'response_length': len(ai_response),
                'message': 'Pre-TTS 미준비로 전체 TTS 처리 중...'
            })
            
            audio_base64 = await self.text_to_speech_async(ai_response)
            
            if audio_base64:
                timestamp = str(int(time.time()))
                file_name = f"tts_full_{self.phone_Id}_{timestamp}.wav"
                file_size = len(base64.b64decode(audio_base64))
                
                tts_payload = {
                    "fileName": file_name,
                    "audioDataBase64": audio_base64,
                    "fileSize": file_size,
                    "status": "fallback_complete",
                    "message": "전체 TTS 변환 완료",
                    "metadata": {
                        "sessionId": self.session_id,
                        "requestId": request_Id,
                        "phoneId": self.phone_Id,
                        "input_text": original_input,
                        "ai_response": ai_response,
                        "engine": "OpenAI-TTS",
                        "language": "ko-KR",
                        "tts_time": round(time.time() - start_time, 2),
                        "pre_tts_used": False
                    }
                }
                
                await self.safe_send({
                    'type': 'tts_complete',
                    'fileName': file_name,
                    'fileSize': file_size,
                    'ai_response': ai_response,
                    'message': '전체 TTS 완료, 스트리밍 시작',
                    'metadata': tts_payload["metadata"]
                })
                
                await self.send_audio_chunks_to_websocket(tts_payload)
                
                logger.info(f"✅ [{self.phone_Id}] 전체 TTS 처리 완료: {file_size}B")
                
            else:
                await self.send_error("음성 생성에 실패했습니다.")
                
        except Exception as e:
            logger.error(f"전체 TTS 처리 오류: {str(e)}")
            await self.send_error(f"TTS 처리 중 오류가 발생했습니다: {str(e)}")
    
    async def get_ai_response_interruptible(self, user_input, cancel_event):
        """중단 가능한 AI 응답 생성 + 첫 문장 Pre-TTS"""
        try:
            logger.info(f"[{self.phone_Id}] AI 응답 생성 시작: '{user_input[:50]}...'")
            
            # 스트림 프로세서 가져오기
            processor = VoiceChatConsumer.stream_processors.get(self.phone_Id)
            
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system", 
                        "content": """당신은 실시간으로 답변을 해주는 AI 복지사 '오라'입니다. 당신은 도움이 되는 AI 어시스턴트입니다.

핵심 원칙: "빠르고 정확하게"

중요한 응답 규칙:
1. 신속하고 정확하게 20단어 이하로 답변해주세요 1초 이내로 답변을 해주도록 노력해주세요
2. 절대로 영어를 사용하지 마세요.
3. 오직 한글과 숫자, 기본 문장부호(.,?!) 만 사용하세요
4. 한자나 영어가 떠오르면 반드시 순수 한글로 바꿔서 말하세요
6. 이모지, 이모티콘 사용 금지
7. 친근하고 자연스럽게 말해
8. "세션", "코드", "에러" 같은 단어 사용 금지

응답 전에 한 번 더 체크하세요: 한자나 영어가 있으면 모두 한글로 바꾸세요."""
                    },
                    {"role": "user", "content": user_input}
                ],
                max_tokens=150,
                temperature=0.7,
                stream=True
            )
            
            full_response = ""
            chunk_count = 0
            first_sentence_completed = False
            
            async for chunk in response:
                # 중단 신호 확인
                if cancel_event.is_set():
                    logger.info(f"[{self.phone_Id}] AI 응답 중단됨")
                    raise asyncio.CancelledError("새로운 토큰으로 인해 중단됨")
                
                chunk_count += 1
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    
                    # 실시간으로 청크 전송
                    await self.safe_send({
                        'type': 'ai_text_chunk',
                        'chunk': content,
                        'chunk_number': chunk_count,
                        'current_response': full_response[:100] + "..." if len(full_response) > 100 else full_response
                    })
                    
                    # 첫 문장 완성 체크 및 Pre-TTS 시작 (즉시)
                    if not first_sentence_completed and processor and self.is_sentence_complete(full_response):
                        first_sentence = self.extract_first_sentence(full_response)
                        if len(first_sentence.strip()) > 5:  # 최소 길이 체크
                            first_sentence_completed = True
                            processor.first_sentence_text = first_sentence
                            
                            logger.info(f"[{self.phone_Id}] 첫 문장 감지: '{first_sentence}' - Pre-TTS 즉시 시작")
                            
                            # Pre-TTS 즉시 시작 (비동기로)
                            processor.pre_tts_task = asyncio.create_task(
                                self.prepare_first_sentence_tts(first_sentence, processor)
                            )
            
            # AI 응답 완료 후에도 Pre-TTS가 진행 중일 수 있음
            logger.info(f"[{self.phone_Id}] AI 응답 완료: {len(full_response)}자")
            
            # Pre-TTS가 아직 시작되지 않았다면 전체 응답으로 시작
            if not first_sentence_completed and processor and len(full_response.strip()) > 5:
                logger.info(f"[{self.phone_Id}] 문장 구분자 없음, 전체 응답으로 Pre-TTS 시작")
                processor.first_sentence_text = full_response.strip()
                processor.pre_tts_task = asyncio.create_task(
                    self.prepare_first_sentence_tts(full_response.strip(), processor)
                )
            
            return full_response
            
        except asyncio.CancelledError:
            logger.info(f"[{self.phone_Id}] AI 응답이 중단되었습니다")
            raise
        except Exception as e:
            logger.error(f"AI 응답 생성 오류: {str(e)}")
            return f"응답 생성 중 오류: {str(e)}"
    
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
    
    async def get_ai_response_final(self, user_input):
        """중단 불가능한 최종 AI 응답 생성 (EOS용)"""
        try:
            logger.info(f"[{self.phone_Id}] 최종 AI 응답 생성 시작: '{user_input[:50]}...'")
            
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system", 
                        "content": """당신은 실시간으로 답변을 해주는 AI 복지사 '오라'입니다. 당신은 도움이 되는 AI 어시스턴트입니다.

핵심 원칙: "빠르고 정확하게"

중요한 응답 규칙:
1. 신속하고 정확하게 20단어 이하로 답변해주세요 1초 이내로 답변을 해주도록 노력해주세요
2. 절대로 영어를 사용하지 마세요.
3. 오직 한글과 숫자, 기본 문장부호(.,?!) 만 사용하세요
4. 한자나 영어가 떠오르면 반드시 순수 한글로 바꿔서 말하세요
6. 이모지, 이모티콘 사용 금지
7. 친근하고 자연스럽게 말해
8. "세션", "코드", "에러" 같은 단어 사용 금지

응답 전에 한 번 더 체크하세요: 한자나 영어가 있으면 모두 한글로 바꾸세요."""
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
                    
                    # 실시간으로 청크 전송 (최종 응답)
                    await self.safe_send({
                        'type': 'ai_final_chunk',
                        'chunk': content,
                        'chunk_number': chunk_count,
                        'current_response': full_response[:100] + "..." if len(full_response) > 100 else full_response
                    })
            
            logger.info(f"[{self.phone_Id}] 최종 AI 응답 완료: {len(full_response)}자")
            
            await self.safe_send({
                'type': 'ai_response_complete',
                'input_text': user_input,
                'ai_response': full_response,
                'response_length': len(full_response)
            })
            
            return full_response
            
        except Exception as e:
            logger.error(f"최종 AI 응답 생성 오류: {str(e)}")
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
                from pydub.utils import which
                
                # ffmpeg 확인
                if not which("ffmpeg"):
                    raise Exception("ffmpeg가 설치되지 않음")
                
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
           
                
                # 크기 로깅
                logger.info(f"✅ WAV 변환 성공: MP3 {len(mp3_data)}B → WAV {len(wav_data)}B")
                return wav_base64
                
            except Exception as conv_error:
                # WAV 변환 실패 시 원본 MP3 사용
                logger.warning(f"WAV 변환 실패, MP3 사용: {conv_error}")
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