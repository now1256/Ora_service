import os
from datetime import datetime
from weaviate.classes.query import Filter
from dotenv import load_dotenv
from langchain_community.utilities import GoogleSearchAPIWrapper
from langchain_openai import OpenAIEmbeddings
# from langchain_weaviate import WeaviateVectorStore
# import weaviate.classes as wvc
# from ..weaviate.weaviate_client import weaviate_client
from langchain.tools import Tool
from django.core.cache import cache
import logging
import hashlib
current_date = datetime.now().strftime("%Y년 %m월 %d일")
logger = logging.getLogger(__name__)

# 환경 변수 로딩
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
google_api_key = os.getenv("GOOGLE_API_KEY")
google_cse_id = os.getenv("GOOGLE_CSE_ID")

# Weaviate 클라이언트 초기화
client = weaviate_client.client

# WeaviateVectorStore 초기화 (VoiceConversation 컬렉션용)
vectorstore = WeaviateVectorStore(
    client=client,
    index_name="VoiceConversation",
    text_key="message",
    embedding=OpenAIEmbeddings(openai_api_key=api_key),
)

def get_phone_uuid_by_phone_id(phone_id: str):
    """phoneId로 Phone 객체의 UUID를 조회 (캐싱 강화)"""
    try:
      
            
        phone_collection = client.collections.get("Phone")
        response = phone_collection.query.fetch_objects(
            filters=Filter.by_property("phoneId").equal(phone_id), limit=1
        )

        if response.objects:
            uuid = response.objects[0].uuid
            return uuid
        else:
            logger.warning(f"phoneId '{phone_id}'에 해당하는 Phone 객체를 찾을 수 없습니다.")
            return None
    except Exception as e:
        logger.error(f"Phone UUID 조회 중 오류: {e}")
        return None

def weaviate_search_tool(phone_id: str):
    """
    🚀 극도로 최적화된 Weaviate 검색 도구
    특정 phoneId에 해당하는 과거 대화 기록들을 초고속으로 검색합니다.
    """
    import time
    search_start = time.time()

    try:
        # 🔑 cache에서 query 가져오기
        query = cache.get(phone_id)
        
        if not query:
            logger.info(f"⚡ 캐시에서 query를 찾을 수 없음: phoneId='{phone_id}'")
            return "NO_QUERY_FOUND"

        # Phone UUID 조회 (강화된 캐싱)
        phone_uuid = get_phone_uuid_by_phone_id(phone_id)
        logger.info(f"⚡ 캐시된 검색 결과 사용: {phone_uuid}초")


        # 🚀 더욱 제한된 검색: k=2로 줄여서 속도 향상
        weaviate_filter = wvc.query.Filter.by_ref("phoneId").by_id().equal(phone_uuid)
        docs = vectorstore.similarity_search(
            query=query, k=5, filters=weaviate_filter  
        )

        if not docs:
            result = "NO_PERSONAL_DATA_FOUND"
            logger.info(f"weaviate db에 관련 기록이 없습니다")
            return result

        # 🚀 최소한의 결과 조합
        result_parts = [f"[{i}] {doc.page_content}" for i, doc in enumerate(docs, 1)]
        result_text = "\n".join(result_parts)

        search_time = time.time() - search_start
        logger.info(f"⚡ 벡터 검색 완료: {len(docs)}개 결과, {search_time:.3f}초")

        return result_text

    except Exception as e:
        logger.error(f"❌ Weaviate 검색 오류: {e}")
        return "SEARCH_ERROR"



# Google Search API 설정
search = GoogleSearchAPIWrapper(
    google_api_key=google_api_key, 
    google_cse_id=google_cse_id,
    k=3  # 검색 결과 수를 3개로 제한
)

# StructuredTool로 Google Search 정의
from langchain.tools import StructuredTool
from pydantic import BaseModel, Field

class GoogleSearchInput(BaseModel):
    """Google Search 입력 스키마"""
    query: str = Field(description="검색할 키워드나 질문")

def google_search_func(query: str) -> str:
    """Google 검색을 수행하는 함수 (캐싱 추가)"""
    try:
        result = search.run(str(query))
        return result
    except Exception as e:
        logger.error(f"Google 검색 오류: {e}")
        return f"검색 중 오류가 발생했습니다: {str(e)}"



# Tools 정의 (설명을 더욱 제한적으로 수정)
tools = [
     StructuredTool.from_function(
        func=google_search_func,
        name="GoogleSearch",
        description="실시간 최신 정보가 반드시 필요하고 일반 상식으로 답변할 수 없는 경우에만 사용하는 검색 도구입니다. 날씨, 주식, 최신 뉴스 등 실시간 데이터가 필요할 때만 사용하세요.",
        args_schema=GoogleSearchInput,
    ),
    Tool(
        name="weaviate_search",
        func=weaviate_search_tool,
        description=f"""
        사용자의 개인 정보나 과거 대화 내용을 검색하는 도구입니다.
        weaviate_search 도구 사용시 user_text가 아닌 phoneId를 전달하세요.
        
        **다음 경우에 사용하세요:**
        - 사용자가 자신의 이름, 나이, 취미, 선호도 등 개인 정보를 물어볼 때
        - "내 이름이 뭐야?", "내가 누구야?", "내 정보 알려줘" 등의 질문
        - "내가 전에 말한", "이전에 얘기한", "예전에 물어본" 등 과거 대화 언급
        - "내 취향", "내가 좋아하는", "내가 싫어하는" 등 개인 선호도 질문
        - 사용자가 이전에 공유한 개인적인 정보를 요청할 때
        
        **사용하지 마세요:**
        - 일반적인 정보 질문 (날씨, 뉴스, 상식 등)
        - 실시간 정보가 필요한 질문
        - 계산, 번역, 설명 등 개인 기록과 무관한 작업
        - 단순한 인사말
        """,
    ),
]