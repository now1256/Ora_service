# consumers.py
import json
import asyncio
import base64
import os
import time
import re
from channels.generic.websocket import AsyncWebsocketConsumer
import torch
import httpx
from django.conf import settings
import logging
from datetime import datetime

# 사전 로드된 모델 가져오기
from ..models.qwen_model import qwen_model

logger = logging.getLogger(__name__)

class StreamProcessor:
    """스트림 토큰을 모아서 처리하는 클래스 (Pre-TTS + 중복 감지)"""
    def __init__(self, session_id: str = "default_session"):
        self.session_id = session_id
        self.accumulated_text = ""
        self.is_collecting = False
        self.start_time = None
        self.current_ai_task = None
        self.cancel_event = asyncio.Event()
        
        # Pre-TTS 관련
        self.current_ai_response = ""
        self.previous_ai_response = ""
        self.current_pre_tts = None
        self.is_pre_tts_ready = False
        self.pre_tts_task = None
        
        # 중복 감지 관련
        self.common_prefix = ""
        self.remaining_text = ""
        
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
    
    def find_common_prefix(self, text1: str, text2: str) -> str:
        """두 텍스트의 공통 접두사 찾기 (단어 경계 고려)"""
        if not text1 or not text2:
            return ""
        
        words1 = text1.split()
        words2 = text2.split()
        
        logger.info(f"[{self.session_id}] 중복 감지 시작:")
        logger.info(f"  - 이전 단어들: {words1[:10]}")
        logger.info(f"  - 현재 단어들: {words2[:10]}")
        
        common_words = []
        for i, (w1, w2) in enumerate(zip(words1, words2)):
            logger.info(f"  - 비교 {i+1}: '{w1}' vs '{w2}' → {'일치' if w1 == w2 else '불일치'}")
            if w1 == w2:
                common_words.append(w1)
            else:
                break
        
        common_prefix = " ".join(common_words)
        if common_words and len(common_prefix) > 0:
            common_prefix += " "
            
        logger.info(f"[{self.session_id}] 중복 감지 결과: '{common_prefix}' ({len(common_words)}개 단어)")
        return common_prefix
    
    def update_ai_response(self, new_response: str):
        """새 AI 응답으로 업데이트하고 중복 부분 계산"""
        self.previous_ai_response = self.current_ai_response
        self.current_ai_response = new_response
        
        self.common_prefix = self.find_common_prefix(self.previous_ai_response, self.current_ai_response)
        
        if self.common_prefix:
            common_normalized = self.common_prefix.strip()
            current_normalized = self.current_ai_response.strip()
            
            if current_normalized.startswith(common_normalized):
                remaining_part = current_normalized[len(common_normalized):].strip()
                self.remaining_text = remaining_part
            else:
                self.remaining_text = self.current_ai_response.strip()
        else:
            self.remaining_text = self.current_ai_response.strip()
            
        logger.info(f"[{self.session_id}] AI 응답 업데이트:")
        logger.info(f"  - 중복 부분: '{self.common_prefix}'")
        logger.info(f"  - 나머지 부분: '{self.remaining_text}'")
        
        if self.common_prefix.strip() == self.current_ai_response.strip():
            logger.info(f"[{self.session_id}] 🎯 100% 중복 감지! Pre-TTS 재활용 가능")
        elif len(self.remaining_text) == 0:
            logger.info(f"[{self.session_id}] 🎯 나머지 부분 없음, Pre-TTS 재활용만으로 충분")
        elif len(self.common_prefix.strip()) > 5:
            logger.info(f"[{self.session_id}] 🔄 부분 중복 감지, 하이브리드 처리 필요")
    
    def reset(self):
        """상태 초기화"""
        elapsed = time.time() - self.start_time if self.start_time else 0
        logger.info(f"[{self.session_id}] 스트림 수집 완료: {len(self.accumulated_text)}자, {elapsed:.2f}초")
        
        text = self.accumulated_text.strip()
        self.accumulated_text = ""
        self.is_collecting = False
        self.start_time = None
        
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
        
        if self.pre_tts_task and not self.pre_tts_task.done():
            self.pre_tts_task.cancel()
            self.pre_tts_task = None

class VoiceChatConsumer(AsyncWebsocketConsumer):
    stream_processors = {}
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_connected = False
        
        # 모델 준비 상태 확인
        if not qwen_model.is_ready:
            logger.warning("⚠️ Qwen 모델이 아직 준비되지 않았습니다!")
        
    async def connect(self):
        try:
            # 모델 준비 상태 재확인
            if not qwen_model.is_ready:
                logger.error("❌ Qwen 모델이 초기화되지 않아 연결을 거부합니다.")
                await self.close(code=4000)
                return
            
            headers = dict(self.scope['headers'])
            phone_Id = headers.get(b'phone-id', b'').decode()
            session_Id = headers.get(b'session-id', b'').decode()

            self.phone_Id = phone_Id
            self.session_id = session_Id
            self.is_connected = True

            stream_processor = StreamProcessor(session_id=self.session_id)
            VoiceChatConsumer.stream_processors[self.phone_Id] = stream_processor

            await self.accept()
            logger.info(f"✅ WebSocket 연결됨: phone_id={self.phone_Id}, session_id={self.session_id}")
            
            await self.send(text_data=json.dumps({
                'type': 'connection_established',
                'message': '음성 채팅 연결이 설정되었습니다.',
                'phone_Id': self.phone_Id,
                'session_id': self.session_id,
                'model_ready': qwen_model.is_ready
            }, ensure_ascii=False))
            
        except Exception as e:
            logger.error(f"❌ WebSocket 연결 오류: {str(e)}")
            self.is_connected = False
            await self.close()
        
    async def disconnect(self, close_code):
        self.is_connected = False
        logger.info(f"WebSocket 연결 해제: phone_id={getattr(self, 'phone_Id', 'unknown')}, close_code={close_code}")
        
        if hasattr(self, 'phone_Id') and self.phone_Id in VoiceChatConsumer.stream_processors:
            processor = VoiceChatConsumer.stream_processors[self.phone_Id]
            await processor.cancel_current_ai_task()
            del VoiceChatConsumer.stream_processors[self.phone_Id]
            logger.info(f"스트림 프로세서 정리 완료: {self.phone_Id}")
        
    async def receive(self, text_data):
        try:
            # 모델 상태 재확인
            if not qwen_model.is_ready:
                await self.send_error("AI 모델이 준비되지 않았습니다. 잠시 후 다시 시도해주세요.")
                return
            
            logger.info(f"[{getattr(self, 'phone_Id', 'unknown')}] 원본 데이터 수신: {repr(text_data[:200])}")
            
            try:
                data = json.loads(text_data)
            except json.JSONDecodeError as json_error:
                logger.error(f"[{getattr(self, 'phone_Id', 'unknown')}] JSON 파싱 오류: {json_error}")
                await self.send_error(f"JSON 파싱 오류: {str(json_error)}")
                return
            
            token = data.get("token", "")
            request_Id = data.get("request_id", "")
                    
            processor = VoiceChatConsumer.stream_processors.get(self.phone_Id)
            if not processor:
                await self.send_error("스트림 프로세서를 찾을 수 없습니다.")
                return
            
            if token == '<eos>':
                # EOS 토큰 수신 - 중복 부분 즉시 전송 + AI 완료 대기
                accumulated_text = processor.get_accumulated_text()
                
                if accumulated_text:
                    logger.info(f"[{self.phone_Id}] EOS 수신, 즉시 처리 시작: '{accumulated_text[:50]}...'")
                    
                    await self.safe_send({
                        'type': 'eos_received',
                        'accumulated_text': accumulated_text,
                        'message': 'EOS 수신, 중복 부분 즉시 전송 중...'
                    })
                    
                    # 1단계: 중복 부분 즉시 전송 (Pre-TTS 있으면)
                    common_sent = False
                    if processor.common_prefix and processor.current_pre_tts:
                        logger.info(f"[{self.phone_Id}] 중복 부분 즉시 전송: '{processor.common_prefix}'")
                        await self.send_common_prefix_immediately(processor, request_Id)
                        common_sent = True
                    
                    # 2단계: AI 태스크 완료 대기
                    ai_response = None
                    if processor.current_ai_task:
                        if not processor.current_ai_task.done():
                            logger.info(f"[{self.phone_Id}] AI 응답 완료 대기...")
                            try:
                                ai_response = await processor.current_ai_task
                                logger.info(f"[{self.phone_Id}] AI 응답 완료: '{ai_response}' (총 {len(ai_response)}자)")
                            except asyncio.CancelledError:
                                logger.warning(f"[{self.phone_Id}] AI 태스크가 중단되었습니다")
                            except Exception as e:
                                logger.error(f"[{self.phone_Id}] AI 태스크 처리 오류: {str(e)}")
                        else:
                            # 이미 완료된 AI 태스크 결과 가져오기
                            try:
                                ai_response = processor.current_ai_task.result()
                                logger.info(f"[{self.phone_Id}] 완료된 AI 응답 사용: '{ai_response}' (총 {len(ai_response)}자)")
                            except Exception as e:
                                logger.error(f"[{self.phone_Id}] 완료된 AI 태스크 결과 오류: {str(e)}")
                    
                    # 3단계: 나머지 부분 TTS 처리
                    if ai_response and ai_response.strip():
                        # AI 응답 업데이트 (중복 계산)
                        processor.update_ai_response(ai_response)
                        
                        # 100% 중복 또는 나머지 부분이 없는 경우
                        if processor.common_prefix.strip() == ai_response.strip() or len(processor.remaining_text) == 0:
                            if common_sent:
                                logger.info(f"[{self.phone_Id}] 100% 중복, 추가 TTS 불필요")
                                await self.safe_send({
                                    'type': 'complete_match_detected',
                                    'message': '완전 일치로 추가 TTS 생성 없음'
                                })
                            else:
                                # 중복 부분을 전송하지 않았다면 전체 Pre-TTS 사용
                                logger.info(f"[{self.phone_Id}] 100% 중복, Pre-TTS 전체 사용")
                                await self.send_complete_pre_tts(processor, request_Id, accumulated_text)
                        elif common_sent:
                            # 중복 부분은 이미 전송했으므로 나머지만 처리
                            if processor.remaining_text:
                                logger.info(f"[{self.phone_Id}] 나머지 부분 TTS 처리: '{processor.remaining_text}'")
                                await self.process_remaining_tts(processor.remaining_text, request_Id, accumulated_text)
                            else:
                                logger.info(f"[{self.phone_Id}] 나머지 부분 없음, 중복 부분만으로 완료")
                        else:
                            # 중복 부분이 없었으면 전체 TTS
                            logger.info(f"[{self.phone_Id}] 중복 부분 없음, 전체 TTS 처리")
                            await self.process_complete_tts(ai_response, request_Id, accumulated_text)
                    else:
                        if not common_sent:
                            await self.send_error("AI 응답을 생성할 수 없습니다. 다시 시도해주세요.")
                    
                    # 상태 리셋
                    final_text = processor.reset()
                    processor.current_ai_task = None
                    
                else:
                    await self.send_error("누적된 텍스트가 없습니다.")
            else:
                # 일반 토큰 수신 + EOS와 동시 수신 가능성 처리
                # 1. 기존 AI 태스크 중단
                await processor.cancel_current_ai_task()
                
                # 2. 토큰 추가
                processor.add_token(token)
                
                # 3. 새로운 AI 응답 시작
                accumulated_text = processor.get_accumulated_text()
                logger.info(f"[{self.phone_Id}] 새 토큰으로 AI 응답 재시작: '{accumulated_text[:50]}...'")
                
                # 4. AI 응답과 Pre-TTS를 동시에 시작
                processor.current_ai_task = asyncio.create_task(
                    self.get_ai_response_with_pretts(accumulated_text, processor)
                )
                
                # 실시간 피드백 전송
                await self.safe_send({
                    'type': 'token_received',
                    'token': token,
                    'accumulated_text': accumulated_text,
                    'accumulated_length': len(accumulated_text),
                    'ai_restarted': True
                })
            
        except Exception as e:
            logger.error(f"[{getattr(self, 'phone_Id', 'unknown')}] WebSocket 처리 오류: {str(e)}")
            await self.send_error(f"처리 중 오류가 발생했습니다: {str(e)}")
    
    async def get_ai_response_with_pretts(self, user_input, processor):
        """Qwen으로 AI 응답 생성과 Pre-TTS를 동시에 처리"""
        try:
            logger.info(f"[{self.phone_Id}] Qwen AI 응답 + Pre-TTS 시작: '{user_input[:50]}...'")
            
            # Qwen 시스템 프롬프트
            system_prompt = """당신은 실시간으로 한국어로만 답변을 해주는 AI 복지사 '오라'입니다. 당신은 도움이 되는 AI 어시스턴트입니다..


핵심 원칙: "빠르고 정확하게"

중요한 응답 규칙:
0. 신속하고 정확하게 20단어 이하로 답변해주세요 1초 이내로 답변을 해주도록 노력해주세요
1. 절대로 한자를 사용하지 마세요. 
2. 절대로 영어를 사용하지 마세요.
3. 오직 한글과 숫자, 기본 문장부호(.,?!) 만 사용하세요
4. 한자나 영어가 떠오르면 반드시 순수 한글로 바꿔서 말하세요
6. 이모지, 이모티콘 사용 금지
7. 친근하고 자연스럽게 말해
8. "세션", "코드", "에러" 같은 단어 사용 금지

응답 전에 한 번 더 체크하세요: 한자나 영어가 있으면 모두 한글로 바꾸세요."""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ]
            
            # Qwen 모델로 응답 생성
            model = qwen_model.model
            tokenizer = qwen_model.tokenizer
            
            # 채팅 템플릿 적용
            text = tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True
            )
            
            # 토크나이징
            inputs = tokenizer(text, return_tensors="pt").to(model.device)
            
            chunk_count = 0
            full_response = ""
            
            # 스트리밍 생성
            with torch.no_grad():
                for _ in range(50):  # 최대 50개 토큰 생성 (20단어 정도)
                    # 중단 신호 확인
                    if processor.cancel_event.is_set():
                        logger.info(f"[{self.phone_Id}] Qwen 응답 중단됨")
                        raise asyncio.CancelledError("새로운 토큰으로 인해 중단됨")
                    
                    # 다음 토큰 생성
                    outputs = model.generate(
                        inputs.input_ids,
                        max_new_tokens=1,
                        do_sample=True,
                        temperature=0.3,
                        top_p=0.8,
                        use_cache=True,
                        pad_token_id=tokenizer.eos_token_id,
                        eos_token_id=tokenizer.eos_token_id
                    )
                    
                    # 새로 생성된 토큰 디코딩
                    new_token_ids = outputs[0][inputs.input_ids.shape[1]:]
                    if len(new_token_ids) == 0:
                        break
                        
                    new_token = tokenizer.decode(new_token_ids[-1:], skip_special_tokens=True)
                    
                    # EOS 토큰이면 종료
                    if new_token_ids[-1] == tokenizer.eos_token_id:
                        break
                    
                    full_response += new_token
                    chunk_count += 1
                    
                    # 다음 생성을 위해 입력 업데이트
                    inputs.input_ids = outputs[0:1]
                    
                    # 실시간으로 청크 전송
                    await self.safe_send({
                        'type': 'ai_text_chunk',
                        'chunk': new_token,
                        'chunk_number': chunk_count,
                        'current_response': full_response[:100] + "..." if len(full_response) > 100 else full_response
                    })
                    
                    # 완료 조건 체크 (문장부호로 끝나거나 20단어 초과)
                    if full_response.strip().endswith(('.', '!', '?')) and len(full_response.split()) >= 5:
                        break
                    if len(full_response.split()) >= 20:
                        break
                    
                    # 비동기 처리를 위한 짧은 대기
                    await asyncio.sleep(0.01)
            
            # AI 응답 완료 후 Pre-TTS 시작
            if full_response.strip():
                logger.info(f"[{self.phone_Id}] Qwen 응답 완료, Pre-TTS 시작: '{full_response}'")
                processor.pre_tts_task = asyncio.create_task(
                    self.prepare_pre_tts(full_response, processor)
                )
            
            logger.info(f"[{self.phone_Id}] Qwen 응답 완료: {len(full_response)}자 - '{full_response}'")
            return full_response.strip()
            
        except asyncio.CancelledError:
            logger.info(f"[{self.phone_Id}] Qwen 응답이 중단되었습니다")
            raise
        except Exception as e:
            logger.error(f"Qwen AI 응답 생성 오류: {str(e)}")
            return f"응답 생성 중 오류: {str(e)}"
    
    async def prepare_pre_tts(self, ai_response, processor):
        """Pre-TTS 준비 (중복 검사 포함)"""
        try:
            logger.info(f"[{self.phone_Id}] Pre-TTS 생성 시작: '{ai_response}'")
            
            # 중복 부분 미리 계산
            if processor.current_ai_response:
                # 이전 응답이 있으면 중복 검사
                common_prefix = processor.find_common_prefix(processor.current_ai_response, ai_response)
                logger.info(f"[{self.phone_Id}] Pre-TTS 중복 검사 결과: '{common_prefix}'")
                
                if common_prefix and len(common_prefix.strip()) > 5:
                    # 중복 부분이 있으면 기존 Pre-TTS 재활용 가능
                    logger.info(f"[{self.phone_Id}] 중복 부분 발견, 기존 Pre-TTS 일부 재활용 가능")
                    
                    # 나머지 부분만 TTS 생성
                    remaining_text = ai_response[len(common_prefix):].strip()
                    if remaining_text:
                        logger.info(f"[{self.phone_Id}] 나머지 부분만 Pre-TTS 생성: '{remaining_text}'")
                        start_time = time.time()
                        audio_base64 = await self.text_to_speech_async(remaining_text)
                        tts_time = time.time() - start_time
                        
                        if audio_base64:
                            # 임시로 나머지 부분만 저장 (실제로는 기존 + 새로운 부분 합쳐야 함)
                            processor.current_pre_tts = audio_base64
                            processor.is_pre_tts_ready = True
                            
                            # AI 응답 업데이트 (중요!)
                            processor.previous_ai_response = processor.current_ai_response
                            processor.current_ai_response = ai_response
                            
                            await self.safe_send({
                                'type': 'pre_tts_partial_ready',
                                'common_prefix': common_prefix,
                                'remaining_text': remaining_text,
                                'audio_size': len(base64.b64decode(audio_base64)),
                                'tts_time': round(tts_time, 2),
                                'message': 'Pre-TTS 부분 생성 완료'
                            })
                            
                            logger.info(f"✅ [{self.phone_Id}] Pre-TTS 부분 완료: {len(base64.b64decode(audio_base64))}B, {tts_time:.2f}초")
                            return
            
            # 중복 부분이 없거나 첫 번째 응답이면 전체 TTS 생성
            start_time = time.time()
            audio_base64 = await self.text_to_speech_async(ai_response)
            tts_time = time.time() - start_time
            
            if audio_base64:
                processor.current_pre_tts = audio_base64
                processor.is_pre_tts_ready = True
                
                # AI 응답 업데이트 (중요!)
                processor.previous_ai_response = processor.current_ai_response
                processor.current_ai_response = ai_response
                
                await self.safe_send({
                    'type': 'pre_tts_ready',
                    'ai_response': ai_response,
                    'audio_size': len(base64.b64decode(audio_base64)),
                    'tts_time': round(tts_time, 2),
                    'message': 'Pre-TTS 준비 완료'
                })
                
                logger.info(f"✅ [{self.phone_Id}] Pre-TTS 완료: {len(base64.b64decode(audio_base64))}B, {tts_time:.2f}초")
                logger.info(f"[{self.phone_Id}] AI 응답 저장: previous='{processor.previous_ai_response[:30]}...', current='{processor.current_ai_response[:30]}...'")
            else:
                logger.warning(f"❌ [{self.phone_Id}] Pre-TTS 실패")
                processor.is_pre_tts_ready = False
            
        except asyncio.CancelledError:
            logger.info(f"[{self.phone_Id}] Pre-TTS 중단됨")
        except Exception as e:
            logger.error(f"❌ Pre-TTS 오류: {str(e)}")
            processor.is_pre_tts_ready = False
    
    async def send_common_prefix_immediately(self, processor, request_Id):
        """중복 부분 즉시 전송"""
        try:
            if not processor.common_prefix or not processor.current_pre_tts:
                return
                
            logger.info(f"[{self.phone_Id}] 중복 부분 즉시 전송: '{processor.common_prefix}'")
            
            # 중복 부분에 해당하는 TTS 추출 (간단히 전체 TTS 사용)
            # 실제로는 음성을 잘라야 하지만, 우선 전체 TTS 사용
            timestamp = str(int(time.time()))
            file_name = f"tts_common_{self.phone_Id}_{timestamp}.wav"
            file_size = len(base64.b64decode(processor.current_pre_tts))
            
            common_payload = {
                "fileName": file_name,
                "audioDataBase64": processor.current_pre_tts,
                "fileSize": file_size,
                "status": "common_prefix",
                "message": "중복 부분 즉시 전송",
                "metadata": {
                    "sessionId": self.session_id,
                    "requestId": request_Id,
                    "phoneId": self.phone_Id,
                    "part": "common_prefix",
                    "text": processor.common_prefix,
                    "engine": "OpenAI-TTS",
                    "language": "ko-KR"
                }
            }
            
            await self.safe_send({
                'type': 'common_prefix_ready',
                'fileName': file_name,
                'fileSize': file_size,
                'text': processor.common_prefix,
                'message': '중복 부분 즉시 재생 시작'
            })
            
            # 즉시 스트리밍 전송
            await self.send_audio_chunks_to_websocket(common_payload)
            
            logger.info(f"✅ [{self.phone_Id}] 중복 부분 전송 완료: {file_size}B")
            
        except Exception as e:
            logger.error(f"중복 부분 전송 오류: {str(e)}")
    
    async def process_remaining_tts(self, remaining_text, request_Id, original_input):
        """나머지 부분 TTS 처리"""
        start_time = time.time()
        
        try:
            logger.info(f"[{self.phone_Id}] 나머지 TTS 처리: '{remaining_text}' (총 {len(remaining_text)}자)")
            
            await self.safe_send({
                'type': 'remaining_tts_start',
                'remaining_text': remaining_text,
                'message': '나머지 부분 TTS 생성 중...'
            })
            
            # TTS 생성
            audio_base64 = await self.text_to_speech_async(remaining_text)
            
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
                        "input_text": original_input,
                        "engine": "OpenAI-TTS",
                        "language": "ko-KR",
                        "tts_time": round(time.time() - start_time, 2)
                    }
                }
                
                await self.safe_send({
                    'type': 'remaining_tts_complete',
                    'fileName': file_name,
                    'fileSize': file_size,
                    'remaining_text': remaining_text,
                    'message': '나머지 부분 스트리밍 시작',
                    'metadata': remaining_payload["metadata"]
                })
                
                # 오디오 스트리밍 전송
                await self.send_audio_chunks_to_websocket(remaining_payload)
                
                logger.info(f"✅ [{self.phone_Id}] 나머지 TTS 완료: '{remaining_text}' → {file_size}B 오디오")
                
            else:
                await self.send_error("나머지 부분 음성 생성에 실패했습니다.")
                
        except Exception as e:
            logger.error(f"나머지 TTS 처리 오류: {str(e)}")
            await self.send_error(f"나머지 TTS 처리 중 오류가 발생했습니다: {str(e)}")
    
    async def send_complete_pre_tts(self, processor, request_Id, original_input):
        """Pre-TTS 전체를 그대로 전송 (100% 중복일 때)"""
        try:
            if not processor.current_pre_tts:
                logger.warning(f"[{self.phone_Id}] Pre-TTS가 준비되지 않음")
                return
                
            logger.info(f"[{self.phone_Id}] Pre-TTS 전체 전송: '{processor.current_ai_response}'")
            
            timestamp = str(int(time.time()))
            file_name = f"tts_complete_match_{self.phone_Id}_{timestamp}.wav"
            file_size = len(base64.b64decode(processor.current_pre_tts))
            
            complete_payload = {
                "fileName": file_name,
                "audioDataBase64": processor.current_pre_tts,
                "fileSize": file_size,
                "status": "complete_match",
                "message": "100% 일치, Pre-TTS 재활용",
                "metadata": {
                    "sessionId": self.session_id,
                    "requestId": request_Id,
                    "phoneId": self.phone_Id,
                    "input_text": original_input,
                    "ai_response": processor.current_ai_response,
                    "engine": "OpenAI-TTS",
                    "language": "ko-KR",
                    "reused_pre_tts": True
                }
            }
            
            await self.safe_send({
                'type': 'complete_match_tts',
                'fileName': file_name,
                'fileSize': file_size,
                'ai_response': processor.current_ai_response,
                'message': '100% 일치, Pre-TTS 재활용 재생',
                'metadata': complete_payload["metadata"]
            })
            
            # 즉시 스트리밍 전송
            await self.send_audio_chunks_to_websocket(complete_payload)
            
            logger.info(f"✅ [{self.phone_Id}] Pre-TTS 재활용 완료: {file_size}B")
            
        except Exception as e:
            logger.error(f"Pre-TTS 재활용 오류: {str(e)}")

    async def process_complete_tts(self, ai_response, request_Id, original_input):
        """완전한 TTS 처리 (중복 부분 없을 때)"""
        start_time = time.time()
        
        try:
            logger.info(f"[{self.phone_Id}] 전체 TTS 처리: '{ai_response}' (총 {len(ai_response)}자)")
            
            await self.safe_send({
                'type': 'tts_processing_start',
                'ai_response': ai_response,
                'response_length': len(ai_response),
                'message': 'TTS 처리 중...'
            })
            
            # TTS 생성
            audio_base64 = await self.text_to_speech_async(ai_response)
            
            if audio_base64:
                timestamp = str(int(time.time()))
                file_name = f"tts_{self.phone_Id}_{timestamp}.wav"
                file_size = len(base64.b64decode(audio_base64))
                
                tts_payload = {
                    "fileName": file_name,
                    "audioDataBase64": audio_base64,
                    "fileSize": file_size,
                    "status": "complete",
                    "message": "TTS 변환 완료",
                    "metadata": {
                        "sessionId": self.session_id,
                        "requestId": request_Id,
                        "phoneId": self.phone_Id,
                        "input_text": original_input,
                        "ai_response": ai_response,
                        "engine": "OpenAI-TTS",
                        "language": "ko-KR",
                        "tts_time": round(time.time() - start_time, 2)
                    }
                }
                
                await self.safe_send({
                    'type': 'tts_complete',
                    'fileName': file_name,
                    'fileSize': file_size,
                    'ai_response': ai_response,
                    'message': 'TTS 완료, 스트리밍 시작',
                    'metadata': tts_payload["metadata"]
                })
                
                # 오디오 스트리밍 전송
                await self.send_audio_chunks_to_websocket(tts_payload)
                
                logger.info(f"✅ [{self.phone_Id}] 전체 TTS 처리 완료: '{ai_response}' → {file_size}B 오디오")
                
            else:
                await self.send_error("음성 생성에 실패했습니다.")
                
        except Exception as e:
            logger.error(f"TTS 처리 오류: {str(e)}")
            await self.send_error(f"TTS 처리 중 오류가 발생했습니다: {str(e)}")
    
    async def send_error(self, message):
        error_response = {
            'type': 'error',
            'message': message,
            'timestamp': time.time()
        }
        await self.safe_send(error_response)
    
    async def safe_send(self, data):
        """안전한 메시지 전송 - 연결 상태 확인"""
        if not self.is_connected:
            logger.warning("WebSocket 연결이 닫혀있어 메시지 전송을 건너뜁니다")
            return
            
        try:
            await self.send(text_data=json.dumps(data, ensure_ascii=False))
        except Exception as e:
            logger.error(f"메시지 전송 실패: {str(e)}")
            self.is_connected = False
    
    async def text_to_speech_async(self, text):
        """텍스트를 WAV 음성으로 변환하여 base64 반환 (OpenAI TTS 사용)"""
        try:
            from openai import AsyncOpenAI
            
            # OpenAI 클라이언트 생성
            openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            
            # OpenAI TTS 생성 (MP3)
            response = await openai_client.audio.speech.create(
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