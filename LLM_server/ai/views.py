import logging
from django.views.decorators.csrf import csrf_exempt
import httpx
import json
from django.conf import settings
# import weaviate.classes as wvc

from ai.utils.LangChain import start_chat

logger = logging.getLogger(__name__)

from django.http import JsonResponse, HttpResponse

def helloworld(request):
    """기본 루트 경로 처리"""
    return HttpResponse("Hello World from LLM_server!", content_type="text/plain")

def hello(request):
    """GET /hello 요청에 대해 "hello" 문자열 반환"""
    if request.method == "GET":
        return HttpResponse("hello", content_type="text/plain")
    return HttpResponse("Method not allowed", status=405)

def test_llm(request):
    """LLM 서버 테스트 엔드포인트"""
    return JsonResponse({
        "status": "success",
        "message": "LLM 서버가 정상적으로 실행 중입니다.",
        "server": "LLM_server",
        "port": 8001
    })

@csrf_exempt
async def process_text(request):
    """STT에서 텍스트를 받아 LangChain 처리 후 TTS로 전송하는 HTTP 엔드포인트"""
    if request.method != "POST":
        return JsonResponse({"error": "POST 메소드만 허용됩니다."}, status=405)

    try:
        # STT에서 전송된 데이터 파싱
        data = json.loads(request.body)

        print("🔥" * 20)
        print("📨 [LLM 서버] STT에서 텍스트 수신!")
        print("🔥" * 20)
        print(f"📝 텍스트: {data.get('text', '')}")
        print(f"📱 전화번호: {data.get('phoneId', 'N/A')}")
        print(f"🆔 세션 ID: {data.get('sessionId', 'N/A')}")
        print(f"🔑 요청 ID: {data.get('requestId', 'N/A')}")

        # 기존 LangChain 처리 로직 import
        from .utils.LangChain import start_chat
        from django.core.cache import cache
        # from .weaviate.weaviate_client import weaviate_client

        user_text = data.get('text', '')
        phone_id = data.get('phoneId', '')
        session_id = data.get('sessionId', '')
        request_id = data.get('requestId', '')

        if not user_text:
            return JsonResponse({"error": "텍스트가 필요합니다."}, status=400)

        # Weaviate에 대화 내용 저장
        try:
            client = weaviate_client.client

            # 1. Phone 객체가 존재하는지 확인하고, 없으면 생성
            phone_collection = client.collections.get("Phone")
            phone_response = phone_collection.query.fetch_objects(
                filters=wvc.query.Filter.by_property("phoneId").equal(phone_id),
                limit=1
            )

            if not phone_response.objects:
                # Phone 객체 생성
                phone_uuid = phone_collection.data.insert({
                    "phoneId": phone_id,
                    "created_at": data.get('timestamp', '')
                })
                print(f"📞 새로운 Phone 객체 생성: {phone_id} -> {phone_uuid}")
            else:
                phone_uuid = phone_response.objects[0].uuid
                print(f"📞 기존 Phone 객체 사용: {phone_id} -> {phone_uuid}")

            # 2. VoiceConversation 객체 저장 (reference 사용)
            conversation_collection = client.collections.get("VoiceConversation")
            conversation_collection.data.insert(
                properties={
                    "message_id": data.get('id', ''),
                    "message": user_text,
                    "speaker": "user"  # VoiceConversation 스키마에 맞춤
                },
                references={
                    "phoneId": phone_uuid  # Phone 객체의 UUID 참조
                }
            )
            print(f"💾 VoiceConversation 저장 완료: {user_text[:30]}...")
        except Exception as e:
            print(f"⚠️ Weaviate 저장 실패: {e}")

        # Redis에 사용자 메시지 임시 저장
        cache.set(phone_id, user_text)

        # LangChain 처리
        print("🤖 [LLM 서버] LangChain 처리 시작...")
        llm_response = start_chat(phone_id, user_text)
        print(f"✅ [LLM 서버] LangChain 처리 완료: {llm_response}")

        # TTS 서버로 HTTP POST 전송
        tts_payload = {
            "text": llm_response,
            "phoneId": phone_id,
            "sessionId": session_id,
            "requestId": request_id,
            "timestamp": data.get('timestamp', ''),
            "voice_config": {
                "language": "ko",
                "speed": 1.0
            }
        }

        print("📤 [LLM 서버] TTS 서버로 HTTP 전송 중...")

        # TTS 서버 URL (설정에서 가져오거나 기본값 사용)
        tts_url = getattr(settings, 'TTS_SERVER_URL', 'http://tts_server:5002') + '/api/convert-tts/'

        async with httpx.AsyncClient() as client:
            tts_response = await client.post(
                tts_url,
                json=tts_payload,
                timeout=30.0
            )

            if tts_response.status_code == 200:
                print("✅ [LLM 서버] TTS 서버로 전송 성공!")
                print("🔄 [워크플로우] LLM → TTS → 외부 스프링 부트 서버 워크플로우 진행 중...")
                return JsonResponse({
                    "status": "success",
                    "message": "텍스트 처리 및 TTS 전송 완료",
                    "llm_response": llm_response,
                    "tts_status": "sent",
                    "workflow_status": "LLM→TTS→외부서버 진행 중"
                })
            else:
                print(f"❌ [LLM 서버] TTS 서버 전송 실패: {tts_response.status_code}")
                return JsonResponse({
                    "status": "partial_success",
                    "message": "LLM 처리 완료, TTS 전송 실패",
                    "llm_response": llm_response,
                    "tts_error": f"Status: {tts_response.status_code}"
                }, status=500)

    except json.JSONDecodeError:
        return JsonResponse({"error": "잘못된 JSON 형식입니다."}, status=400)
    except Exception as e:
        print(f"❌ [LLM 서버] 처리 오류: {e}")
        logger.error(f"LLM 텍스트 처리 오류: {e}")
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
async def LangChain(request):
    if request.method == "POST":
        try:
           start_chat()
        except Exception as e:
            print(f"LLM 서버 오류: {e}")
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "허용되지 않은 메소드"}, status=405)


