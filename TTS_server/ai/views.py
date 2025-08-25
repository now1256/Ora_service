import logging
import json
import os
import sys
import asyncio
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from django.utils.decorators import method_decorator
from django.conf import settings
from django.views import View
import base64
import numpy as np
import time
import requests

# 경로
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'domain', 'GPT-SoVITS'))
from api_v2 import tts_pipeline, tts_config, tts_handle  # tts_engine.py
from asgiref.sync import async_to_sync

# WebSocket 서버로 데이터 전송을 위한 임포트
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .consumers import TtsWebSocketConsumer

logger = logging.getLogger(__name__)
#통신과 관련한 함수
# LLM_server에서 오는 text받기
def send_to_external_server(filename: str, audio_data: bytes, text: str,
                          session_id: str, request_id: str, phone_id: str, engine: str, language: str = 'ko-KR') -> bool:
    """외부 서버로 오디오 파일 전송 - Java 컨트롤러 형식에 맞게 수정"""
    try:
        # 외부 서버 URL (Spring Boot 서버)
        # external_url = getattr(settings, 'EXTERNAL_SERVER_URL', 'http://100.72.196.9:8080/api/tts/receive')
        # 수정해야함
        external_url = 'http://100.72.196.9:8080/api/tts/receive'
        # Base64 인코딩
        audio_base64 = base64.b64encode(audio_data).decode('utf-8')

        # Java 컨트롤러가 요구하는 JSON 형식으로 데이터 구성
        json_data = {
            "fileName": filename,
            "audioDataBase64": audio_base64,
            "fileSize": len(audio_data),
            "status": "success",
            "message": "TTS 변환 완료",
            "metadata": {
                "sessionId": session_id,
                "requestId": request_id,
                "phoneId": phone_id,
                "text": text,
                "engine": engine,
                "language": language
            }
        }

        print(f"📤 [TTS] Java 컨트롤러로 데이터 전송 시작")
        print(f"   📞 세션 ID: {session_id}")
        print(f"   🆔 요청 ID: {request_id}")
        print(f"   📱 전화번호: {phone_id}")
        print(f"   📄 파일명: {filename}")
        print(f"   📊 파일 크기: {len(audio_data)} bytes")
        print(f"   🌐 URL: {external_url}")

        # JSON 형식으로 POST 요청
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        start_time = time.time()
        processing_time = time.time() - start_time
        print(f"✅  (진짜 보내기전 {processing_time:.3f}초)")
        response = requests.post(
            external_url,
            json=json_data,  # json 파라미터 사용
            headers=headers,
            timeout=30
        )
        processing_time = time.time() - start_time
        print(f"✅  (진짜 보내고나서 {processing_time:.3f}초)")

        if response.status_code == 200:
            print(f"✅ [TTS] Java 컨트롤러 전송 성공: {external_url}")
            print(f"   📨 응답: {response.text}")
            return True
        else:
            print(f"❌ [TTS] Java 컨트롤러 전송 실패")
            print(f"   📊 상태 코드: {response.status_code}")
            print(f"   📨 응답: {response.text}")
            return False

    except Exception as e:
        print(f"❌ [TTS] Java 컨트롤러 전송 오류: {e}")
        return False

def send_to_external_server_websocket(filename: str, audio_data: bytes, text: str,
                                     session_id: str, request_id: str, phone_id: str,
                                     engine: str, language: str = 'ko-KR',
                                     fire_and_forget: bool = False) -> bool:
    """연결된 WebSocket 클라이언트로 오디오 스트리밍 (동기 모드)"""
    print(f"🟢 [TTS] send_to_external_server_websocket 함수 시작!!!")
    try:
        print(f"🔌 [TTS] WebSocket 서버에서 클라이언트로 스트리밍")
        print(f"   📞 세션 ID: {session_id}")
        print(f"   🆔 요청 ID: {request_id}")
        print(f"   📱 전화번호: {phone_id}")
        print(f"   📄 파일명: {filename}")
        print(f"   📊 파일 크기: {len(audio_data)} bytes")

        start_time = time.time()

        print(f"🟡 [TTS] Django Channels 임포트 시도...")
        # Django Channels 사용
        from .consumers import TtsWebSocketConsumer
        print(f"🟡 [TTS] TtsWebSocketConsumer 임포트 성공")

        print(f"🟡 [TTS] 연결된 클라이언트 확인...")
        print(f"   현재 연결된 클라이언트: {TtsWebSocketConsumer.connected_clients}")

        # async_to_sync를 사용하여 비동기 함수를 동기적으로 실행
        from asgiref.sync import async_to_sync

        print(f"🔵 [TTS] async_to_sync로 send_to_client 호출...")
        print(f"🔵 [TTS] 전달할 request_id: '{request_id}'")
        try:
            # 비동기 함수를 동기적으로 실행
            result = async_to_sync(TtsWebSocketConsumer.send_to_client)(
                phone_id=phone_id,
                session_id=session_id,
                audio_data=audio_data,
                filename=filename,
                text=text,
                request_id=request_id
            )
            print(f"🔵 [TTS] send_to_client 결과: {result}")

            processing_time = time.time() - start_time

            if result:
                print(f"✅ [TTS] WebSocket 서버 스트리밍 완료 ({processing_time:.3f}초)")
            else:
                print(f"❌ [TTS] WebSocket 서버 스트리밍 실패 - 클라이언트 미연결 ({processing_time:.3f}초)")

            return result

        except Exception as e:
            print(f"❌ [TTS] send_to_client 실행 오류: {e}")
            import traceback
            traceback.print_exc()
            return False

    except Exception as e:
        import traceback
        print(f"❌ [TTS] WebSocket 서버 스트리밍 오류: {e}")
        print(f"   상세 오류:")
        traceback.print_exc()
        return False

@csrf_exempt
def convert_tts(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST 메소드만 허용'}, status=405)

    try:
        # 요청 데이터 파싱
        print("djklsfafjdsalkfjsdlkfsdaj------------------------------------------------------------", request.body)
        data = json.loads(request.body)
        text = data.get('text', '')
        phone_id = data.get('phoneId', 'unknown')
        session_id = data.get('sessionId', 'unknown')
        request_id = data.get('requestId', 'unknown')
        voice_config = data.get('voice_config', {})
        use_websocket = data.get('use_websocket', True)  # 기본값: WebSocket 사용
        fire_and_forget = data.get('fire_and_forget', True)  # 기본값: Fire-and-forget 모드

        if not text.strip():
            return JsonResponse({'error': '텍스트가 비어있습니다'}, status=400)
        try:
            body = json.loads(request.body.decode("utf-8")) if request.body else {}
        except json.JSONDecodeError:
            return JsonResponse({"message": "invalid json"}, status=400)

        def as_bool(v, default):
            if isinstance(v, bool):
                return v
            if v is None:
                return default
            return str(v).lower() == "true"

        print(f"🎵 [TTS] 음성 변환 시작: '{text}' (Phone: {phone_id})")
        print(f"📋 [TTS] 받은 request_id: '{request_id}' (타입: {type(request_id)})")
        if not request_id or request_id == 'unknown':
            print(f"⚠️ [TTS] 경고: request_id가 비어있거나 unknown입니다! 받은 전체 데이터: {data}")
        req = {
        # "text": data.get("text"),
        "text": text,
        "text_lang": "ko",
        "ref_audio_path": "/code/media/my_voice_03.wav",  # 컨테이너 경로
        "prompt_text": body.get("prompt_text", "저는 인공지능 모델 학습을 위한 음성 데이터를 녹음하고 있어요."),  # 고정/기본 프롬프트
        "prompt_lang": body.get("prompt_lang", "ko").lower(),            # ← 분리/추가
        "top_k": int(body.get("top_k", 5)),
        "top_p": float(body.get("top_p", 1)),
        "temperature": float(body.get("temperature", 1)),
        "text_split_method": body.get("text_split_method", "cut0"),
        "batch_size": int(body.get("batch_size", 1)),
        "batch_threshold": float(body.get("batch_threshold", 0.75)),
        "split_bucket": as_bool(body.get("split_bucket", True), True),
        "speed_factor": float(body.get("speed_factor", 1.0)),
        "fragment_interval": float(body.get("fragment_interval", 0.3)),
        "seed": int(body.get("seed", -1)),
        "media_type": body.get("media_type", "wav"),
        "streaming_mode": as_bool(body.get("streaming_mode", False), True),
        "parallel_infer": as_bool(body.get("parallel_infer", True), True),
        "repetition_penalty": float(body.get("repetition_penalty", 1.35)),
        "sample_steps": int(body.get("sample_steps", 32)),
        "super_sampling": as_bool(body.get("super_sampling", False), False),
        }

        start_time = time.time()
        processing_time = time.time() - start_time
        print(f"✅ 모델 들어가기전 시간 ({processing_time:.3f}초)")

        # TTS 모델에서 원본 WAV 생성 (변환 없이 사용)
        wav_data = tts_handle(req)

        # tts_handle이 JsonResponse 에러를 반환했는지 확인
        if isinstance(wav_data, JsonResponse):
            logger.error(f"❌ TTS 모델 에러: {wav_data.content}")
            return wav_data  # 에러 응답 반환

        processing_time = time.time() - start_time
        print(f"✅ TTS 모델 음성 생성 완료 ({processing_time:.3f}초)")
        print("-----------------------------------------------")

        # TTS 원본 WAV 정보 확인
        if isinstance(wav_data, bytes) and len(wav_data) > 0:
            print(f"🎵 TTS 원본 WAV 정보:")
            print(f"   파일 크기: {len(wav_data):,} bytes")
            print(f"   WAV 헤더: {wav_data[:4]} ... {wav_data[8:12] if len(wav_data) > 12 else 'N/A'}")
            print(f"   미디어 타입: {req.get('media_type')}")

            # WAV 헤더에서 샘플레이트 확인 (변휈하지 않음)
            if len(wav_data) > 44:
                sample_rate = int.from_bytes(wav_data[24:28], 'little')
                channels = int.from_bytes(wav_data[22:24], 'little')
                print(f"   샘플레이트: {sample_rate}Hz (TTS 원본 유지)")
                print(f"   채널: {channels}ch")
        else:
            logger.error(f"❌ TTS 결과가 비정상: type={type(wav_data)}")
            return JsonResponse({'error': 'TTS 음성 생성 실패'}, status=500)

        # # WAV 파일을 audio_outputs 폴더에 저장
        # audio_outputs_dir = '/code/media'
        # os.makedirs(audio_outputs_dir, exist_ok=True)

        # # 파일명 생성
        # timestamp = int(time.time() * 1000)
        # wav_filename = f"tts_{phone_id}_{timestamp}.wav"
        # wav_file_path = os.path.join(audio_outputs_dir, wav_filename)

        # # WAV 파일 저장
        # with open(wav_file_path, 'wb') as wav_file:
        #     wav_file.write(wav_data)

        # print(f"💾 [TTS] WAV 파일 저장 완료: {wav_file_path}")
        processing_time = time.time() - start_time


        print(f"✅ [TTS] wav파일 저장 시간 ({processing_time:.3f}초)")

        print("----------------------------------------------------")

        # 파일명 생성
        timestamp = int(time.time() * 1000)
        wav_filename = f"tts_{phone_id}_{timestamp}.wav"

        # 전송 방식 선택
        if use_websocket:
            print(f"🔌 [TTS] WebSocket 전송 모드 (TTS 원본 그대로)")
            print(f"   🎵 TTS 원본 WAV: {len(wav_data):,} bytes")
            print(f"   📦 4096 바이트 청크로 분할 예정")
            print(f"   🎯 Fire-and-forget: {fire_and_forget}")

            # WebSocket 전송 시작 시간 측정
            ws_start_time = time.time()
            
            # TTS 원본 WAV를 그대로 전송 (변환 없이)
            external_success = send_to_external_server_websocket(
                filename=wav_filename,
                audio_data=wav_data,  # TTS 원본 그대로
                text=text,
                session_id=session_id,
                request_id=request_id,
                phone_id=phone_id,
                engine="GPT-sovits",
                fire_and_forget=fire_and_forget
            )
            
            # WebSocket 전송 완료 시간 측정
            ws_time = time.time() - ws_start_time
            print(f"   ⏱️ WebSocket 전송 완료: {ws_time:.3f}초")
            print(f"   📊 전송 속도: {len(wav_data) / ws_time / 1024:.1f} KB/s")
            transfer_method = "websocket"
        else:
            print(f"📡 [TTS] HTTP 전송 모드 선택")
            external_success = send_to_external_server(
                filename=wav_filename,
                audio_data=wav_data,
                text=text,
                session_id=session_id,
                request_id=request_id,
                phone_id=phone_id,
                engine="GPT-sovits"
            )
            transfer_method = "http"

        # 전체 처리 시간 계산
        total_processing_time = time.time() - start_time
        
        # TTS 생성 시간 (wav_data 생성까지)
        tts_generation_time = processing_time  # 이미 계산되어 있음
        
        # 전송 시간 (WebSocket 또는 HTTP)
        transfer_time = ws_time if use_websocket and 'ws_time' in locals() else 0

        # TTS 변환은 성공했으므로 항상 성공으로 처리
        print("=" * 60)
        print(f"📊 [TTS] 전체 처리 시간 분석:")
        print(f"   ⏱️ TTS 음성 생성: {tts_generation_time:.3f}초")
        print(f"   ⏱️ 외부 서버 전송: {transfer_time:.3f}초")
        print(f"   ⏱️ 전체 처리 시간: {total_processing_time:.3f}초")
        print(f"   📦 전송된 데이터: {len(wav_data):,} bytes ({len(wav_data)/1024:.1f} KB)")
        print(f"   ✅ [TTS] 처리 완료!")
        print("=" * 60)

        return JsonResponse({
            'success': True,
            'message': 'TTS 변환 완료',
            'filename': wav_filename,
            'transfer_method': transfer_method,
            'processing_time': total_processing_time,
            'timing_details': {
                'tts_generation': round(tts_generation_time, 3),
                'transfer': round(transfer_time, 3),
                'total': round(total_processing_time, 3)
            },
            'data_size': len(wav_data),
            'engine': 'GPT-sovits',
            'external_transfer': 'success' if external_success else 'failed',
            'use_websocket': use_websocket,
            'fire_and_forget': fire_and_forget if use_websocket else None,
            'note': '외부 서버 전송 실패해도 TTS는 성공' if not external_success else None
        })

    except Exception as e:
        logger.error(f"❌ [TTS] 변환 오류: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e),
            'stage': 'tts_conversion'
        }, status=500)


@csrf_exempt
def tts(request):
    if request.method == "GET":
        req = {
            "text": request.GET.get("text"),
            "text_lang": request.GET.get(request.GET.get("text_lang")),
            "ref_audio_path": request.GET.get("ref_audio_path"),
            "aux_ref_audio_paths": request.GET.getlist("aux_ref_audio_paths") or None,
            "prompt_lang": (request.GET.get("prompt_lang") or "").lower(),
            "text_lang": (request.GET.get("text_lang") or "").lower(),
            "top_k": int(request.GET.get("top_k", 5)),
            "top_p": float(request.GET.get("top_p", 1)),
            "temperature": float(request.GET.get("temperature", 1)),
            "text_split_method": request.GET.get("text_split_method", "cut0"),
            "batch_size": int(request.GET.get("batch_size", 1)),
            "batch_threshold": float(request.GET.get("batch_threshold", 0.75)),
            "split_bucket": request.GET.get("split_bucket", "True").lower() == "true",
            "speed_factor": float(request.GET.get("speed_factor", 1.0)),
            "fragment_interval": float(request.GET.get("fragment_interval", 0.3)),
            "seed": int(request.GET.get("seed", -1)),
            "media_type": request.GET.get("media_type", "wav"),
            "streaming_mode": request.GET.get("streaming_mode", "False").lower() == "true",
            "parallel_infer": request.GET.get("parallel_infer", "True").lower() == "true",
            "repetition_penalty": float(request.GET.get("repetition_penalty", 1.35)),
            "sample_steps": int(request.GET.get("sample_steps", 32)),
            "super_sampling": request.GET.get("super_sampling", "False").lower() == "true",
        }
        return tts_handle(req)

    if request.method == "POST":
        try:
            body = json.loads(request.body.decode("utf-8")) if request.body else {}
        except json.JSONDecodeError:
            return JsonResponse({"message": "invalid json"}, status=400)

        # FastAPI의 pydantic 모델과 동일 키 사용
        req = {
            "text": body.get("text"),
            "text_lang": body.get("text_lang"),
            "ref_audio_path": body.get("ref_audio_path"),
            "aux_ref_audio_paths": body.get("aux_ref_audio_paths"),
            "prompt_text": body.get("prompt_text", ""),
            "prompt_text": body.get("prompt_lang", ""),
            "top_k": int(body.get("top_k", 5)),
            "top_p": float(body.get("top_p", 1)),
            "temperature": float(body.get("temperature", 1)),
            "text_split_method": body.get("text_split_method", "cut0"),
            "batch_size": int(body.get("batch_size", 1)),
            "batch_threshold": float(body.get("batch_threshold", 0.75)),
            "split_bucket": bool(body.get("split_bucket", True)),
            "speed_factor": float(body.get("speed_factor", 1.0)),
            "fragment_interval": float(body.get("fragment_interval", 0.3)),
            "seed": int(body.get("seed", -1)),
            "media_type": body.get("media_type", "wav"),
            "streaming_mode": bool(body.get("streaming_mode", False)),
            "parallel_infer": bool(body.get("parallel_infer", True)),
            "repetition_penalty": float(body.get("repetition_penalty", 1.35)),
            "sample_steps": int(body.get("sample_steps", 32)),
            "super_sampling": bool(body.get("super_sampling", False)),
        }

        return tts_handle(req)

    return JsonResponse({"message": "method not allowed"}, status=405)


def set_refer_audio(request):
    refer_audio_path = request.GET.get("refer_audio_path") or request.GET.get("refer_audio") or request.GET.get("path")
    try:
        tts_pipeline.set_ref_audio(refer_audio_path)
    except Exception as e:
        return JsonResponse({"message": "set refer audio failed", "Exception": str(e)}, status=400)
    return JsonResponse({"message": "success"}, status=200)


def set_gpt_weights(request):
    weights_path = request.GET.get("weights_path")
    try:
        if not weights_path:
            return JsonResponse({"message": "gpt weight path is required"}, status=400)
        tts_pipeline.init_t2s_weights(weights_path)
    except Exception as e:
        return JsonResponse({"message": "change gpt weight failed", "Exception": str(e)}, status=400)
    return JsonResponse({"message": "success"}, status=200)


def set_sovits_weights(request):
    weights_path = request.GET.get("weights_path")
    try:
        if not weights_path:
            return JsonResponse({"message": "sovits weight path is required"}, status=400)
        tts_pipeline.init_vits_weights(weights_path)
    except Exception as e:
        return JsonResponse({"message": "change sovits weight failed", "Exception": str(e)}, status=400)
    return JsonResponse({"message": "success"}, status=200)



# views.py
from django.http import JsonResponse
def health(request):
    """헬스체크 엔드포인트"""
    print(">>> HIT /health", flush=True)

    # WebSocket 클라이언트 상태 확인
    from .consumers import TtsWebSocketConsumer
    connected_clients = len(TtsWebSocketConsumer.connected_clients)

    return JsonResponse({
        "ok": True,
        "service": "TTS Server",
        "websocket_enabled": True,
        "websocket_endpoint": "/ws/tts/",
        "connected_clients": connected_clients,
        "port": 5002
    }, status=200)
