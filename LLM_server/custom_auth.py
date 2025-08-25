from urllib.request import Request
from litellm.proxy._types import UserAPIKeyAuth
import logging
import os
logger = logging.getLogger("custom_auth")
logger.setLevel(logging.INFO)

async def user_api_key_auth(request: Request, api_key: str) -> UserAPIKeyAuth: 
    
    logger.info(f"api_key: {api_key}")
    logger.info(f"request.headers: {getattr(request, 'headers', None)}")
    try: 
        modified_master_key = os.getenv("LITELLM_MASTER_KEY")
        logger.info(f"Received API Key: {api_key}")
        print(api_key)  
        if api_key == modified_master_key:
            logger.info("API Key 인증 성공")
            return UserAPIKeyAuth(api_key=api_key)
        logger.warning("인증 실패: 잘못된 API Key")
        raise Exception("Invalid API Key")
    except Exception as e: 
        logger.error(f"인증 중 예외 발생: {e}")
        raise
