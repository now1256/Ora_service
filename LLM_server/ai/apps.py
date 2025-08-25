from django.apps import AppConfig
import logging
from .models import qwen_model

# 로거 설정
logger = logging.getLogger(__name__)

class AiConfig(AppConfig):
    """AI 애플리케이션 설정 클래스."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ai'
    # def ready(self):
    #     """Django 앱이 준비되면 실행되는 메서드"""
    #     try:
    #         logger.info("Django 앱 준비 중 - Qwen 모델 로드 시작...")
            
    #         # Qwen 모델 사전 로드
    #         from .models.qwen_model import QwenModel
    #         qwen_model = QwenModel()
    #         qwen_model.initialize()
            
    #         logger.info("✅ Django 앱 준비 완료 - Qwen 모델 로드 성공!")
            
    #     except Exception as e:
    #         logger.error(f"❌ Django 앱 준비 중 오류: {str(e)}")
    #         # 필요에 따라 앱 시작을 중단하거나 계속 진행
    #         raise
