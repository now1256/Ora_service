#jsonchatManager.py
import json
import os
from datetime import datetime
from typing import Dict
from django.conf import settings

class JSONChatManager:
    def __init__(self, user_id: str):
        self.user_id = user_id
        
        # Django 프로젝트 루트 기준으로 절대 경로 사용
        self.base_dir = settings.BASE_DIR
        self.chat_logs_dir = os.path.join(self.base_dir, "chat_logs")
        self.json_path = os.path.join(self.chat_logs_dir, f"{user_id}_chat.json")
        
        print(f"🔍 JSONChatManager 초기화:")
        print(f"   - 사용자 ID: {user_id}")
        print(f"   - BASE_DIR: {self.base_dir}")  
        print(f"   - Chat logs dir: {self.chat_logs_dir}")
        print(f"   - JSON path: {self.json_path}")
        
        # 강제로 폴더와 파일 생성
        self._force_create_structure()
        
        # 채팅 데이터 로드
        self.chat_data = self._load_or_create_data()
    def trigger_vectorstore_update(self, user_id: str):
        """새 대화 추가 시 벡터스토어 업데이트 트리거"""
        try:
            # MultiUserRAGManager 가져오기
            from .MultiUserRAGManager import MultiUserRAGManager
            
            # 전역 캐시에서 RAG 매니저 가져오기
            global _rag_manager
            if _rag_manager is None:
                _rag_manager = MultiUserRAGManager()
            
            # 해당 사용자의 벡터스토어 새로고침
            print(f"🔄 [{user_id}] 새 대화로 인한 벡터스토어 업데이트...")
            rag_system = _rag_manager.refresh_user_vectorstore(user_id)
            
            if rag_system and rag_system.conversational_rag_chain:
                print(f"✅ [{user_id}] 벡터스토어 업데이트 완료")
                return True
            else:
                print(f"❌ [{user_id}] 벡터스토어 업데이트 실패")
                return False
                
        except Exception as e:
            print(f"❌ [{user_id}] 벡터스토어 업데이트 중 오류: {e}")
            return False
    
    def _force_create_structure(self):
        """강제로 폴더와 파일 구조 생성"""
        try:
            # 1. 폴더 생성
            print(f"📁 폴더 생성 시도: {self.chat_logs_dir}")
            os.makedirs(self.chat_logs_dir, exist_ok=True)
            
            if os.path.exists(self.chat_logs_dir):
                print(f"✅ 폴더 존재 확인됨")
            else:
                print(f"❌ 폴더 생성 실패")
                return
            
            # 2. JSON 파일이 없으면 강제 생성
            if not os.path.exists(self.json_path):
                print(f"📄 JSON 파일 생성 시도: {self.json_path}")
                
                initial_data = {
                    "user_id": self.user_id,
                    "created_at": datetime.now().isoformat(),
                    "total_conversations": 0,
                    "conversations": []
                }
                
                # 파일 쓰기 시도
                with open(self.json_path, 'w', encoding='utf-8') as f:
                    json.dump(initial_data, f, ensure_ascii=False, indent=2)
                    f.flush()  # 강제로 플러시
                    os.fsync(f.fileno())  # 강제로 디스크에 쓰기
                
                # 생성 확인
                if os.path.exists(self.json_path):
                    file_size = os.path.getsize(self.json_path)
                    print(f"✅ JSON 파일 생성 성공: {file_size} bytes")
                    
                    # 내용 확인
                    with open(self.json_path, 'r', encoding='utf-8') as f:
                        test_data = json.load(f)
                    print(f"✅ JSON 내용 확인: {len(test_data.get('conversations', []))}개 대화")
                else:
                    print(f"❌ JSON 파일 생성 실패")
            else:
                file_size = os.path.getsize(self.json_path)
                print(f"✅ 기존 JSON 파일 발견: {file_size} bytes")
                
        except Exception as e:
            print(f"❌ 구조 생성 실패: {e}")
            import traceback
            traceback.print_exc()
    
    def _load_or_create_data(self) -> Dict:
        """데이터 로드 또는 기본 데이터 생성"""
        try:
            if os.path.exists(self.json_path):
                print(f"📖 JSON 파일 로드 시도: {self.json_path}")
                with open(self.json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                print(f"✅ JSON 로드 성공: {len(data.get('conversations', []))}개 대화")
                return data
            else:
                print(f"❌ JSON 파일이 존재하지 않음, 기본 데이터 생성")
                return self._get_default_data()
                
        except Exception as e:
            print(f"❌ JSON 로드 실패: {e}")
            return self._get_default_data()
    
    def _get_default_data(self) -> Dict:
        """기본 데이터 구조"""
        return {
            "user_id": self.user_id,
            "created_at": datetime.now().isoformat(),
            "total_conversations": 0,
            "conversations": []
        }
    
    def add_conversation(self, user_input: str, ai_response: str):
        """대화 추가 - 즉시 저장"""
        try:
            print(f"\n📝 === 대화 추가 시작 ===")
            print(f"사용자: {user_input[:50]}...")
            print(f"AI: {str(ai_response)[:50]}...")
            
            # 새 대화 생성
            new_id = len(self.chat_data["conversations"]) + 1
            conversation = {
                "id": new_id,
                "timestamp": datetime.now().isoformat(),
                "date": datetime.now().strftime("%Y-%m-%d"),
                "time": datetime.now().strftime("%H:%M:%S"),
                "user_question": str(user_input),
                "ai_answer": str(ai_response)
            }
            
            # 메모리에 추가
            self.chat_data["conversations"].append(conversation)
            self.chat_data["total_conversations"] = len(self.chat_data["conversations"])
            self.chat_data["last_updated"] = datetime.now().isoformat()
            
            print(f"📊 메모리 업데이트 완료: {self.chat_data['total_conversations']}개 대화")
            
            # 즉시 파일에 저장
            print(f"💾 파일 저장 시도: {self.json_path}")
            
            with open(self.json_path, 'w', encoding='utf-8') as f:
                json.dump(self.chat_data, f, ensure_ascii=False, indent=2)
                f.flush()  # 버퍼 비우기
                os.fsync(f.fileno())  # 강제 디스크 쓰기
            
            # 저장 검증
            if os.path.exists(self.json_path):
                file_size = os.path.getsize(self.json_path)
                print(f"✅ 파일 저장 성공: {file_size} bytes")
                
                # 실제 저장된 내용 확인
                with open(self.json_path, 'r', encoding='utf-8') as f:
                    saved_data = json.load(f)
                saved_count = len(saved_data.get('conversations', []))
                print(f"✅ 저장 검증 완료: {saved_count}개 대화")
                
                if saved_count != self.chat_data['total_conversations']:
                    print(f"⚠️  메모리({self.chat_data['total_conversations']})와 파일({saved_count}) 불일치")
                
            else:
                print(f"❌ 파일이 저장되지 않음")
                return None
            
            print(f"✅ === 대화 추가 완료 (#{new_id}) ===\n")
            return new_id
            
        except Exception as e:
            print(f"❌ 대화 추가 실패: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_conversation_count(self):
        """현재 대화 수 반환"""
        return len(self.chat_data.get("conversations", []))
    
    def print_status(self):
        """현재 상태 출력"""
        print(f"\n📊 === JSONChatManager 상태 ===")
        print(f"사용자 ID: {self.user_id}")
        print(f"JSON 경로: {self.json_path}")
        print(f"파일 존재: {os.path.exists(self.json_path)}")
        if os.path.exists(self.json_path):
            print(f"파일 크기: {os.path.getsize(self.json_path)} bytes")
        print(f"메모리 대화 수: {len(self.chat_data.get('conversations', []))}")
        print(f"=========================\n")