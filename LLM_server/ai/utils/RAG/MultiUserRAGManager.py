import os
import shutil
import json
from datetime import datetime
from django.conf import settings
from .JSONToRAG import JSONToRAGWithHistory

class MultiUserRAGManager:
    def __init__(self):
        self.user_rag_systems = {}
        self.store_dir = os.path.join(settings.BASE_DIR, 'Store')
        self._ensure_store_directory()
    
    def _ensure_store_directory(self):
        """Store 디렉토리 생성"""
        os.makedirs(self.store_dir, exist_ok=True)
    
    def create_empty_chat_file(self, user_id: str, json_path: str):
        """빈 채팅 파일 생성"""
        chat_logs_dir = os.path.join(settings.BASE_DIR, 'chat_logs')
        os.makedirs(chat_logs_dir, exist_ok=True)
        
        empty_data = {
            "user_id": user_id,
            "created_at": datetime.now().isoformat(),
            "total_conversations": 0,
            "conversations": []
        }
        
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(empty_data, f, ensure_ascii=False, indent=2)
        
        print(f"📝 새로운 채팅 파일 생성: {json_path}")
    
    def get_user_rag_system(self, user_id: str):
        """사용자별 RAG 시스템 가져오기 (없으면 생성)"""
        if user_id not in self.user_rag_systems:
            base_dir = settings.BASE_DIR
            json_path = os.path.join(base_dir, 'chat_logs', f'{user_id}_chat.json')
            vectorstore_path = os.path.join(self.store_dir, f'{user_id}_vectorstore')
            
            print(f"🔍 JSON 경로: {json_path}")
            print(f"🔍 벡터스토어 경로: {vectorstore_path}")
            
            # JSON 파일이 없으면 생성
            if not os.path.exists(json_path):
                self.create_empty_chat_file(user_id, json_path)
            
            # RAG 시스템 생성
            rag_system = JSONToRAGWithHistory(json_path)
            
            # 기존 벡터스토어가 있는지 확인
            if os.path.exists(vectorstore_path):
                print(f"🔄 [{user_id}] 기존 벡터스토어 로드 시도...")
                if rag_system.load_vectorstore(vectorstore_path):
                    print(f"✅ [{user_id}] 기존 벡터스토어 로드 성공")
                    self.user_rag_systems[user_id] = rag_system
                    return rag_system
                else:
                    print(f"❌ [{user_id}] 기존 벡터스토어 로드 실패, 새로 생성")
            
            # 새로 벡터스토어 생성
            print(f"🚀 [{user_id}] 새 벡터스토어 생성...")
            if rag_system.build_rag_system():
                print(f"🔍 [{user_id}] conversational_rag_chain 상태 확인...")
                print(f"    - conversational_rag_chain 속성 존재: {hasattr(rag_system, 'conversational_rag_chain')}")
                rag_system.save_vectorstore(vectorstore_path)
                self.user_rag_systems[user_id] = rag_system
            else:
                print(f"❌ [{user_id}] RAG 시스템 생성 실패")
                return None
        
        return self.user_rag_systems[user_id]
    
    def refresh_user_vectorstore(self, user_id: str):
        """사용자의 벡터스토어를 새 대화로 업데이트"""
        print(f"🔄 [{user_id}] 벡터스토어 새로고침 시작...")
        
        try:
            base_dir = settings.BASE_DIR
            json_path = os.path.join(base_dir, 'chat_logs', f'{user_id}_chat.json')
            vectorstore_path = os.path.join(self.store_dir, f'{user_id}_vectorstore')
            
            # JSON 파일 존재 확인
            if not os.path.exists(json_path):
                print(f"❌ [{user_id}] JSON 파일이 없음: {json_path}")
                return None
            
            # 새로운 RAG 시스템 생성 (기존 것을 덮어씀)
            print(f"🚀 [{user_id}] 새로운 RAG 시스템 생성...")
            rag_system = JSONToRAGWithHistory(json_path)
            
            if rag_system.build_rag_system():
                print(f"✅ [{user_id}] RAG 시스템 재생성 완료")
                
                # 기존 벡터스토어 삭제
                if os.path.exists(vectorstore_path):
                    shutil.rmtree(vectorstore_path)
                    print(f"🗑️ [{user_id}] 기존 벡터스토어 삭제")
                
                # 새 벡터스토어 저장
                rag_system.save_vectorstore(vectorstore_path)
                print(f"💾 [{user_id}] 새 벡터스토어 저장")
                
                # 캐시 업데이트
                self.user_rag_systems[user_id] = rag_system
                print(f"✅ [{user_id}] 벡터스토어 새로고침 완료")
                
                return rag_system
            else:
                print(f"❌ [{user_id}] RAG 시스템 재생성 실패")
                return None
                
        except Exception as e:
            print(f"❌ [{user_id}] 벡터스토어 새로고침 중 오류: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_vectorstore_info(self, user_id: str):
        """벡터스토어 정보 조회"""
        vectorstore_path = os.path.join(self.store_dir, f'{user_id}_vectorstore')
        json_path = os.path.join(settings.BASE_DIR, 'chat_logs', f'{user_id}_chat.json')
        
        info = {
            'user_id': user_id,
            'vectorstore_exists': os.path.exists(vectorstore_path),
            'vectorstore_path': vectorstore_path,
            'json_exists': os.path.exists(json_path),
            'json_path': json_path,
            'conversation_count': 0,
            'vectorstore_size': 0
        }
        
        # JSON 파일에서 대화 수 확인
        if info['json_exists']:
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                info['conversation_count'] = len(data.get('conversations', []))
            except:
                pass
        
        # 벡터스토어 크기 확인
        if info['vectorstore_exists']:
            try:
                info['vectorstore_size'] = sum(
                    os.path.getsize(os.path.join(vectorstore_path, f))
                    for f in os.listdir(vectorstore_path)
                    if os.path.isfile(os.path.join(vectorstore_path, f))
                )
            except:
                pass
        
        return info
    
    def delete_user_vectorstore(self, user_id: str):
        """특정 사용자의 벡터스토어 삭제"""
        vectorstore_path = os.path.join(self.store_dir, f'{user_id}_vectorstore')
        
        try:
            if os.path.exists(vectorstore_path):
                shutil.rmtree(vectorstore_path)
                print(f"🗑️ [{user_id}] 벡터스토어 삭제 완료: {vectorstore_path}")
                
                # 캐시에서도 제거
                if user_id in self.user_rag_systems:
                    del self.user_rag_systems[user_id]
                    print(f"🗑️ [{user_id}] 캐시에서도 제거됨")
                    
                return True
            else:
                print(f"❌ [{user_id}] 벡터스토어가 존재하지 않음: {vectorstore_path}")
                return False
        except Exception as e:
            print(f"❌ [{user_id}] 벡터스토어 삭제 실패: {e}")
            return False
    
    def list_all_users(self):
        """모든 사용자 목록과 상태 조회"""
        chat_logs_dir = os.path.join(settings.BASE_DIR, 'chat_logs')
        
        users = []
        if os.path.exists(chat_logs_dir):
            for filename in os.listdir(chat_logs_dir):
                if filename.endswith('_chat.json'):
                    user_id = filename.replace('_chat.json', '')
                    info = self.get_vectorstore_info(user_id)
                    users.append(info)
        
        return users