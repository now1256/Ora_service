from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # WebSocket 엔드포인트: ws://서버주소/ws/tts/
    re_path(r'^ws/tts/$', consumers.TtsWebSocketConsumer.as_asgi()),
    # 선택적: phone_id와 session_id를 URL 파라미터로 받는 경우
    re_path(r'^ws/tts/(?P<phone_id>\w+)/(?P<session_id>\w+)/$', consumers.TtsWebSocketConsumer.as_asgi()),
]
