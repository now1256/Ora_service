

import json
import os
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_text_splitters import RecursiveCharacterTextSplitter

from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from dotenv import load_dotenv
import time
import logging
from ..prompts import prompt

# 환경 변수 로드
load_dotenv()

class JSONToRAGWithHistory:
    def __init__(self, json_file_path: str, openai_api_key: str = None):
        self.json_file_path = json_file_path
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        
        if not self.openai_api_key:
            raise ValueError("OpenAI API 키가 필요합니다!")
        
        self.vectorstore = None
        self.rag_chain = None
        self.conversational_rag_chain = None
        self.store = {}  # 세션별 메시지 히스토리 저장소
        
    def load_json_data(self):
        """JSON 파일 로드"""
        try:
            with open(self.json_file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            print(f"✅ JSON 로드 완료: {len(data['conversations'])}개 대화")
            return data
        except FileNotFoundError:
            print(f"❌ 파일을 찾을 수 없습니다: {self.json_file_path}")
            return None
        except json.JSONDecodeError:
            print(f"❌ JSON 파싱 에러: {self.json_file_path}")
            return None
    
    def create_documents(self, data):
        """JSON을 LangChain Document로 변환"""
        documents = []
        
        for conv in data["conversations"]:
            # Q&A 형태로 content 구성
            content = f"""사용자 질문: {conv['user_question']}
                        AI 답변: {conv['ai_answer']}
                        날짜: {conv['date']}
                        시간: {conv['time']}"""
                                    
            # Document 생성
            doc = Document(
                page_content=content,
                metadata={
                    "conversation_id": conv["id"],
                    "timestamp": conv["timestamp"],
                    "date": conv["date"],
                    "time": conv["time"],
                    "user_id": data["user_id"],
                    "user_question": conv["user_question"],
                    "ai_answer": conv["ai_answer"]
                }
            )
            documents.append(doc)
        
        print(f"✅ Document 생성 완료: {len(documents)}개")
        return documents
    
    # create_vectorstore도 디버깅 강화
    def create_vectorstore(self, documents):
        """벡터 스토어 생성 (디버깅 강화)"""
        print("🔄 벡터스토어 생성 시작...")
        print(f"📊 입력 문서 개수: {len(documents)}")
        
        if not documents:
            print("⚠️ 문서가 없음 - 더미 문서 생성")
            # 더미 문서 생성
            dummy_doc = Document(
                page_content="초기 설정용 더미 문서입니다. 첫 대화 후 업데이트됩니다.",
                metadata={
                    "conversation_id": "dummy",
                    "timestamp": "2024-01-01T00:00:00",
                    "date": "2024-01-01",
                    "time": "00:00:00",
                    "user_id": "system",
                    "user_question": "초기 설정",
                    "ai_answer": "더미 데이터"
                }
            )
            documents = [dummy_doc]
            print(f"✅ 더미 문서 생성: {len(documents)}개")
        
        try:
            print("🔄 텍스트 분할 중...")
            # 텍스트 분할
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=300,
                chunk_overlap=50,
                separators=["\n\n", "\n", " ", ""]
            )
            
            split_docs = text_splitter.split_documents(documents)
            print(f"✅ 텍스트 분할 완료: {len(split_docs)}개 청크")
            
            if split_docs:
                print(f"📄 첫 번째 청크: {split_docs[0].page_content[:100]}...")
            
            print("🔄 임베딩 모델 초기화 중...")
            # 임베딩 생성
            embeddings = OpenAIEmbeddings(
                openai_api_key=self.openai_api_key,
                model="text-embedding-3-small"
            )
            print("✅ 임베딩 모델 초기화 완료")
            
            print("🔄 FAISS 벡터스토어 생성 중...")
            # FAISS 벡터스토어 생성
            vectorstore = FAISS.from_documents(split_docs, embeddings)
            print("✅ FAISS 벡터스토어 생성 완료")
            
            # 생성된 벡터스토어 정보 확인
            if hasattr(vectorstore, 'index'):
                print(f"📊 생성된 벡터 개수: {vectorstore.index.ntotal}")
                print(f"📊 벡터 차원: {vectorstore.index.d}")
            
            # 테스트 검색
            print("🔍 테스트 검색 수행...")
            test_results = vectorstore.similarity_search("안녕", k=1)
            print(f"🎯 테스트 검색 결과: {len(test_results)}개")
            if test_results:
                print(f"📄 검색된 문서: {test_results[0].page_content[:100]}...")
            
            return vectorstore
            
        except Exception as e:
            print(f"❌ 벡터스토어 생성 중 오류: {e}")
            import traceback
            traceback.print_exc()
            return None

    
    def format_docs(self, docs):
        """검색된 문서들을 포맷팅"""
        return "\n\n".join(doc.page_content for doc in docs)
    
    def create_rag_chain(self, vectorstore):
        """RAG 체인 생성 (RunnableWithMessageHistory 사용)"""
        print("🔄 RAG 체인 구성 중...")
        
        # LLM 설정
        llm = ChatOpenAI(
            openai_api_key=self.openai_api_key,
            model="gpt-4o-mini",
            temperature=0.1,
            base_url="https://api.openai.com/v1",
            timeout=30,
            max_retries=2
        )
        
        # 리트리버 
        retriever = vectorstore.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 5}  # k를 늘려서 더 많이 검색
        )
        
        # ✅ 수정: 디버깅이 강화된 컨텍스트 검색 함수
        def get_context(inputs):
            """컨텍스트 검색 함수 - 강화된 디버깅"""
            question = inputs["input"]
            print(f"\n🔍 === 컨텍스트 검색 시작 ===")
            print(f"📝 검색 질문: '{question}'")
            
            try:
                # 1. 기본 검색
                docs = retriever.invoke(question)
                print(f"📊 검색된 문서 수: {len(docs)}")
                
                # 2. 검색 결과 상세 출력
                if docs:
                    print(f"✅ 검색 성공! 문서 정보:")
                    for i, doc in enumerate(docs):
                        metadata = doc.metadata
                        conv_id = metadata.get('conversation_id', 'N/A')
                        user_q = metadata.get('user_question', 'N/A')[:50]
                     
                    
                    context = self.format_docs(docs)
                    return context
                else:
                    print("❌ 검색된 문서가 없음!")
                    
                    # 3. 유사도 점수와 함께 재검색
                    print("🔍 유사도 점수 포함 재검색...")
                    try:
                        docs_with_scores = vectorstore.similarity_search_with_score(question, k=5)
                        print(f"📊 점수 포함 검색 결과: {len(docs_with_scores)}개")
                        
                        if docs_with_scores:
                            print("📋 점수별 검색 결과:")
                            for i, (doc, score) in enumerate(docs_with_scores):
                                metadata = doc.metadata
                                conv_id = metadata.get('conversation_id', 'N/A')
                                user_q = metadata.get('user_question', 'N/A')[:30]
                                print(f"  {i+1}. [대화#{conv_id}] 점수:{score:.3f} {user_q}...")
                            
                            # 점수가 높은 문서들 반환 (점수가 낮을수록 유사함)
                            best_docs = [doc for doc, score in docs_with_scores if score < 1.0]
                            if best_docs:
                                context = self.format_docs(best_docs)
                                print(f"✅ 유사도 기반 컨텍스트 생성: {len(context)}자")
                                return context
                    except Exception as score_error:
                        print(f"❌ 점수 검색 오류: {score_error}")
                    
                    # 4. 벡터스토어 상태 확인
                    print("🔍 벡터스토어 상태 확인...")
                    if hasattr(vectorstore, 'index'):
                        print(f"📊 총 벡터 수: {vectorstore.index.ntotal}")
                        print(f"📊 벡터 차원: {vectorstore.index.d}")
                    
                    # 5. 다른 키워드로 검색 시도
                    print("🔍 다른 키워드로 검색 시도...")
                    test_keywords = ["안녕", "이름", "질문", "대화", question.split()[0] if question.split() else ""]
                    for keyword in test_keywords:
                        if keyword:
                            try:
                                test_docs = vectorstore.similarity_search(keyword, k=2)
                                if test_docs:
                                    print(f"  '{keyword}' 검색: {len(test_docs)}개 문서 발견")
                                    context = self.format_docs(test_docs)
                                    print(f"✅ 대체 키워드로 컨텍스트 생성")
                                    return context
                            except:
                                continue
                    
                    print("❌ 모든 검색 시도 실패")
                    return "검색된 이전 대화가 없습니다."
                    
            except Exception as e:
                print(f"❌ 컨텍스트 검색 중 오류: {e}")
                import traceback
                traceback.print_exc()
                return "검색 중 오류가 발생했습니다."
        
        # RAG 체인 구성
        rag_chain = (
            {
                "context": get_context,
                "input": lambda x: x["input"],
                "chat_history": lambda x: x.get("chat_history", [])
            }
            | prompt
            | llm
            | StrOutputParser()
        )
        
        print("✅ RAG 체인 생성 완료")
        return rag_chain
    
    def get_session_history(self, session_id: str):
        """세션별 메시지 히스토리 가져오기"""
        if session_id not in self.store:
            self.store[session_id] = ChatMessageHistory()
        return self.store[session_id]
    
    def create_conversational_rag_chain(self, rag_chain):
        """대화형 RAG 체인 생성"""
        print("🔄 대화형 RAG 체인 구성 중...")
        
        # RunnableWithMessageHistory로 래핑
        conversational_rag_chain = RunnableWithMessageHistory(
            rag_chain,
            self.get_session_history,
            input_messages_key="input",
            history_messages_key="chat_history",
        )
        
        print("✅ 대화형 RAG 체인 생성 완료")
        return conversational_rag_chain
    
    
    
    
    def build_rag_system(self):
        """전체 RAG 시스템 구축"""
        print("🚀 RAG 시스템 구축 시작...")
        
        # 1. JSON 데이터 로드
        data = self.load_json_data()
        print(data)
       
        if not data:
            return False
        
        # 2. Document 생성
        documents = self.create_documents(data)
        
        # 3. 벡터스토어 생성
        self.vectorstore = self.create_vectorstore(documents)
        
        # 4. RAG 체인 생성
        self.rag_chain = self.create_rag_chain(self.vectorstore)
        
        # 5. 대화형 RAG 체인 생성
        self.conversational_rag_chain = self.create_conversational_rag_chain(self.rag_chain)
        
        print("🎉 RAG 시스템 구축 완료!")
        return True
    
    def stream_query(self, question: str, session_id: str = "default", cancel_event=None, is_eos_received_func=None):
        """스트림 질문하기 (중단 이벤트 지원)"""
        try:
            config = {"configurable": {"session_id": session_id}}
            
            print(f"🔍 스트림 질의 시작: {question}")
            
            chunk_count = 0
            for chunk in self.conversational_rag_chain.stream({"input": question}, config=config):
                chunk_count += 1
                
                # 중단 이벤트 체크
                if cancel_event and is_eos_received_func:
                    if cancel_event.is_set() and not is_eos_received_func():
                        print(f"⚠️ 스트림 중단 감지 (청크 #{chunk_count})")
                        break
                
                if chunk:
                    yield chunk
            
        except Exception as e:
            print(f"❌ 스트림 질의 오류: {e}")
            yield f"오류: {str(e)}"
    
    def query(self, question: str, session_id: str = "default", show_sources: bool = True):
        """질문하기 (대화 기록 포함)"""
        
        print(f"\n🤔 질문: {question}")
        print("🔄 검색 중...")
        
        try:
            # 질의 실행 (세션 ID 포함)
            config = {"configurable": {"session_id": session_id}}
            result = self.conversational_rag_chain.stream(
                {"input": question},
                config=config
            )
            
            print(f"🤖 답변: {result}")
            
            if show_sources:
                # 관련 문서 검색해서 보여주기
                retriever = self.vectorstore.as_retriever(
                    search_type="similarity",
                    search_kwargs={"k": 3}
                )
                docs = retriever.invoke(question)
                
                if docs:
                    print(f"\n📚 참고한 대화 ({len(docs)}개):")
                    for i, doc in enumerate(docs, 1):
                        metadata = doc.metadata
                        print(f"  {i}. [대화 #{metadata['conversation_id']}] {metadata['date']}")
                        print(f"     👤 {metadata['user_question'][:50]}...")
                        print(f"     🤖 {metadata['ai_answer'][:50]}...")
                        print()
            
            return result
            
        except Exception as e:
            print(f"❌ 질의 실행 오류: {e}")
            return None
    
    def get_chat_history(self, session_id: str = "default"):
        """현재 세션의 대화 기록 조회"""
        if session_id in self.store:
            history = self.store[session_id]
            messages = history.messages
            print(f"\n💬 세션 '{session_id}'의 대화 기록:")
            for i, msg in enumerate(messages, 1):
                role = "👤 사용자" if msg.type == "human" else "🤖 AI"
                print(f"  {i}. {role}: {msg.content[:100]}...")
        else:
            print(f"❌ 세션 '{session_id}'의 대화 기록이 없습니다.")
    
    def clear_chat_history(self, session_id: str = "default"):
        """특정 세션의 대화 기록 삭제"""
        if session_id in self.store:
            del self.store[session_id]
            print(f"🗑️ 세션 '{session_id}'의 대화 기록이 삭제되었습니다.")
        else:
            print(f"❌ 세션 '{session_id}'의 대화 기록이 없습니다.")
    
    def save_vectorstore(self, save_path: str = "vectorstore"):
        """벡터스토어 저장"""
        if self.vectorstore:
            self.vectorstore.save_local(save_path)
            print(f"💾 벡터스토어 저장됨: {save_path}")
        else:
            print("❌ 저장할 벡터스토어가 없습니다.")
    
    def load_vectorstore(self, load_path: str = "vectorstore"):
        """저장된 벡터스토어 로드"""
        try:
            if not os.path.exists(load_path):
                print(f"❌ 벡터스토어 폴더가 없습니다: {load_path}")
                return False
            
            embeddings = OpenAIEmbeddings(
                openai_api_key=self.openai_api_key,
                model="text-embedding-3-small"
            )
            
            self.vectorstore = FAISS.load_local(
                load_path, 
                embeddings,
                allow_dangerous_deserialization=True
            )
            
            # RAG 체인 재생성
            self.rag_chain = self.create_rag_chain(self.vectorstore)
            self.conversational_rag_chain = self.create_conversational_rag_chain(self.rag_chain)
            
            print(f"✅ 벡터스토어 로드됨: {load_path}")
            return True
        except Exception as e:
            print(f"❌ 벡터스토어 로드 실패: {e}")
            return False