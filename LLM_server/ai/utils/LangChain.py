# ai/utils/LangChain.py
import datetime
import json
import os
import shutil
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from httpx import Response
from langchain_teddynote import logging
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
import logging as log
from .RAG.MultiUserRAGManager import MultiUserRAGManager
from .RAG.JSONChatManager import JSONChatManager
from .RAG.JSONToRAG import JSONToRAGWithHistory
import threading
from concurrent.futures import ThreadPoolExecutor
import faiss
from rest_framework.decorators import api_view
from rest_framework import status


logging.langsmith("CH05-Memory")


# 전역 캐시
_rag_manager = None
_user_systems_cache = {}
_json_managers_cache = {}

def get_or_create_rag_manager():
    """RAG 매니저 싱글톤"""
    global _rag_manager
    if _rag_manager is None:
        print("🔄 RAG 매니저 최초 생성")
        _rag_manager = MultiUserRAGManager()
    return _rag_manager

def get_or_create_user_system(phoneId: str):
    """사용자별 RAG 시스템 캐싱"""
    global _user_systems_cache
    
    if phoneId not in _user_systems_cache:
        print(f"🔄 사용자 {phoneId} RAG 시스템 최초 생성")
        rag_manager = get_or_create_rag_manager()
        user_system = rag_manager.get_user_rag_system(phoneId)
        _user_systems_cache[phoneId] = user_system
    else:
        print(f"✅ 사용자 {phoneId} RAG 시스템 캐시에서 로드")
    
    return _user_systems_cache[phoneId]

def get_or_create_json_manager(phoneId: str):
    """JSON 매니저 캐싱"""
    global _json_managers_cache
    
    if phoneId not in _json_managers_cache:
        print(f"🔄 사용자 {phoneId} JSON 매니저 최초 생성")
        _json_managers_cache[phoneId] = JSONChatManager(phoneId)
    else:
        print(f"✅ 사용자 {phoneId} JSON 매니저 캐시에서 로드")
    
    return _json_managers_cache[phoneId]
def start_chat(phoneId: str, question: str):
    try:
        json_manager = _json_managers_cache[phoneId]
        user_rag_system = _user_systems_cache[phoneId]

        if user_rag_system:
            print(f"✅ RAG 시스템 로드 성공")
            
            # 실제 질문 처리
            result = user_rag_system.query(question, phoneId, show_sources=False)
            print(f"RAG 결과: {str(result)[:100]}...")
            # # 실제 대화 저장
            conv_id = json_manager.add_conversation(question, result)
            #print(f"대화 저장 결과: {conv_id}")  
            return result
        else:
            return "RAG 시스템 로드 실패"
        
            
    except Exception as e:
        print(f"❌ start_chat 에러: {e}")
        import traceback
        traceback.print_exc()
        return f"에러: {str(e)}"

@csrf_exempt
def RAG_RELOAD(request):
    try:
        data = json.loads(request.body)
        phoneId = data.get('phoneId')
        
        if not phoneId:
            return JsonResponse({'success': False, 'message': 'phoneId 필수'}, status=400)
        
        log.info(f"RAG_RELOAD 호출: {phoneId}")
        
        get_or_create_json_manager(phoneId)
        get_or_create_user_system(phoneId)
        
        return JsonResponse({
            'success': True,
            'message': 'RAG 시스템 초기화 완료',
            'phoneId': phoneId
        })
        
    except Exception as e:
        log.error(f"RAG_RELOAD 에러: {e}")
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


@csrf_exempt
@api_view(['POST'])
def VECTORSTORE_DELETE(request):
    try:
        # POST 요청에서 phoneId 추출
        phoneId = request.data.get('phoneId')
        
        if not phoneId:
            return JsonResponse({
                'success': False,
                'message': 'phoneId가 필요합니다'
            }, status=400)
        
        print(f"VECTORSTORE_DELETE 호출: {phoneId}")
        
        # JSON 매니저 생성
        json_manager = get_or_create_json_manager(phoneId)
        
        # 사용자별 RAG 시스템 가져오기
        user_rag_system = get_or_create_user_system(phoneId)
        
        if not user_rag_system:
            return JsonResponse({
                'success': False,
                'message': f'사용자 {phoneId}의 RAG 시스템을 찾을 수 없습니다'
            }, status=404)
        
        # 대화 기록 저장 카운터
        saved_conversations = 0
        
        # 1. 세션의 대화 기록을 JSON 파일에 저장
        try:
            # RAG 시스템의 메모리에서 대화 기록 추출
            messages = []
            
            if hasattr(user_rag_system, 'memory') and user_rag_system.memory:
                # ChatMessageHistory에서 메시지 가져오기
                if hasattr(user_rag_system.memory, 'chat_memory'):
                    messages = user_rag_system.memory.chat_memory.messages
                elif hasattr(user_rag_system.memory, 'messages'):
                    messages = user_rag_system.memory.messages
                
                log.info(f"총 {len(messages)}개의 메시지를 찾았습니다")
                
                # 짝수 인덱스(사용자), 홀수 인덱스(AI) 순서로 저장
                for i in range(0, len(messages), 2):
                    if i + 1 < len(messages):  # AI 답변이 있는지 확인
                        user_message = messages[i]
                        ai_message = messages[i + 1]
                        
                        # 메시지 타입 확인 (HumanMessage, AIMessage 등)
                        if hasattr(user_message, 'content') and hasattr(ai_message, 'content'):
                            user_question = user_message.content
                            ai_answer = ai_message.content
                            
                            # JSON 파일에 대화 저장
                            conv_id = json_manager.add_conversation(user_question, ai_answer)
                            saved_conversations += 1
                            
                            log.info(f"대화 저장 완료 #{saved_conversations}: {conv_id}")
                
                log.info(f"총 {saved_conversations}개의 대화를 JSON 파일에 저장했습니다")
                
        except Exception as memory_error:
            log.error(f"메모리에서 대화 기록 추출 중 오류: {memory_error}")
            # 세션 저장 실패해도 벡터스토어 삭제는 계속 진행
        
        # 2. 벡터스토어 삭제
        deleted_components = []
        
        try:
            if hasattr(user_rag_system, 'vectorstore') and user_rag_system.vectorstore:
                vectorstore = user_rag_system.vectorstore
                
                # FAISS 벡터스토어인 경우
                if hasattr(vectorstore, 'index'):
                    # FAISS 인덱스 초기화
                    vectorstore.index.reset()
                    deleted_components.append("FAISS 인덱스")
                    log.info(f"FAISS 인덱스 초기화 완료: {phoneId}")
                
                # Chroma 벡터스토어인 경우
                if hasattr(vectorstore, 'delete_collection'):
                    try:
                        vectorstore.delete_collection()
                        deleted_components.append("Chroma 컬렉션")
                        log.info(f"Chroma 컬렉션 삭제 완료: {phoneId}")
                    except Exception as chroma_error:
                        log.warning(f"Chroma 컬렉션 삭제 실패: {chroma_error}")
                
                # 벡터스토어 파일 삭제 (저장된 파일이 있는 경우)
                if hasattr(vectorstore, 'persist_directory'):
                    persist_dir = vectorstore.persist_directory
                    if os.path.exists(persist_dir):
                        shutil.rmtree(persist_dir)
                        deleted_components.append(f"벡터스토어 디렉토리: {persist_dir}")
                        log.info(f"벡터스토어 디렉토리 삭제: {persist_dir}")
                
                # 메모리에서 벡터스토어 제거
                user_rag_system.vectorstore = None
                deleted_components.append("메모리의 벡터스토어 객체")
                
                log.info(f"사용자 {phoneId}의 벡터스토어 정리 완료")
                
        except Exception as vs_error:
            log.error(f"벡터스토어 삭제 중 오류: {vs_error}")
            # 벡터스토어 삭제 실패해도 계속 진행
        
        # 3. 대화 메모리 초기화
        try:
            if hasattr(user_rag_system, 'memory') and user_rag_system.memory:
                # ChatMessageHistory 초기화
                if hasattr(user_rag_system.memory, 'chat_memory'):
                    user_rag_system.memory.chat_memory.clear()
                    deleted_components.append("대화 메모리")
                elif hasattr(user_rag_system.memory, 'clear'):
                    user_rag_system.memory.clear()
                    deleted_components.append("메모리 기록")
                
                log.info(f"대화 메모리 초기화 완료: {phoneId}")
                
        except Exception as memory_clear_error:
            log.warning(f"메모리 초기화 중 오류 (무시됨): {memory_clear_error}")
        
        # # 4. 캐시에서 사용자 시스템 제거 (선택사항)
        # try:
        #     if '_user_systems_cache' in globals() and phoneId in _user_systems_cache:
        #         del _user_systems_cache[phoneId]
        #         deleted_components.append("사용자 시스템 캐시")
        #         log.info(f"사용자 시스템 캐시 삭제: {phoneId}")
        # except Exception as cache_error:
        #     log.warning(f"캐시 삭제 중 오류 (무시됨): {cache_error}")
        
        return JsonResponse({
            'success': True,
            'message': f'세션 기록 저장 및 벡터스토어 삭제 완료',
            'phoneId': phoneId,
            'saved_conversations': saved_conversations,
            'deleted_components': deleted_components,
            'details': {
                'total_messages_found': len(messages) if 'messages' in locals() else 0,
                'conversations_saved': saved_conversations,
                'components_deleted': len(deleted_components)
            }
        })
        
    except Exception as e:
        log.error(f"VECTORSTORE_DELETE 에러: {e}")
        import traceback
        traceback.print_exc()
        
        return JsonResponse({
            'success': False,
            'message': f'처리 중 오류 발생: {str(e)}',
            'phoneId': request.data.get('phoneId', 'unknown')
        }, status=500)

# def start_chat(phoneId: str, question: str):
#     json_manager = JSONChatManager(phoneId)
#     rag_manager = MultiUserRAGManager()
#     user_rag_system = rag_manager.get_user_rag_system(phoneId)
    
    
#     try:
#         if user_rag_system:  # RAG 시스템이 정상적으로 생성되었는지 확인
#             # 빠른 로드 후 바로 질문

#             result = user_rag_system.query(question, phoneId, show_sources=False)
            
#             # user_rag_system.get_chat_history(phoneId)
#             # json_manager = JSONChatManager(phoneId)
#             json_manager.add_conversation(question, result)
#             return result

#             #hisotry에 있는 모든 데이터 json에 저장
#             # json_manager = JSONChatManager("demo_user")
#             # # 세션의 대화 기록 가져오기
#             # if session_id in rag_system.store:
#             #     messages = rag_system.store[session_id].messages
            
#             #     # 짝수 인덱스(사용자), 홀수 인덱스(AI) 순서로 저장
#             #     for i in range(0, len(messages), 2):
#             #         if i + 1 < len(messages):  # AI 답변이 있는지 확인
#             #             user_question = messages[i].content  # 사용자 질문
#             #             ai_answer = messages[i + 1].content   # AI 답변
#             #             json_manager.add_conversation(user_question, ai_answer)
#         else:
#             print("❌ 벡터스토어 로드 실패")

#         #백터 스토어 삭제 (통화가 끝났을때 테스트)
#         # print("\n🔄 벡터스토어 업데이트를 위한 정리...")
#         # rag_manager.delete_user_vectorstore("demo_user")  # 특정 사용자만
#     except Exception as e:
#         import traceback
#         traceback.print_exc()
#         return f"에러 발생: {str(e)}"
