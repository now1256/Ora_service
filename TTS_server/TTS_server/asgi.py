import os
import logging
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "TTS_server.settings")

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Django 초기화를 먼저 해야 함
django_asgi_app = get_asgi_application()

# WebSocket 라우팅 import
from ai.routing import websocket_urlpatterns

logger.info(f"✅ ASGI 애플리케이션 초기화 - WebSocket 라우트: {websocket_urlpatterns}")

# HTTP와 WebSocket 모두 지원하는 ASGI 애플리케이션
application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})

logger.info("✅ ASGI 애플리케이션 설정 완료 - HTTP와 WebSocket 모두 지원")
