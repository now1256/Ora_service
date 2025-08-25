# models/qwen_model.py (별도 파일로 분리)
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
import logging

logger = logging.getLogger(__name__)

class QwenModel:
    """Qwen 모델 싱글톤 관리 클래스"""
    _instance = None
    _model = None
    _tokenizer = None
    _is_initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(QwenModel, cls).__new__(cls)
        return cls._instance
    
    def initialize(self):
        """Qwen 모델 초기화 (한 번만 실행)"""
        if self._is_initialized:
            logger.info("Qwen 모델이 이미 초기화되어 있습니다.")
            return
            
        if self._model is None:
            logger.info("🚀 Qwen/Qwen2.5-7B-Instruct 모델 로딩 시작...")
            
            try:
                self._model = AutoModelForCausalLM.from_pretrained(
                    "Qwen/Qwen2.5-7B-Instruct",
                    torch_dtype=torch.float16,
                    device_map="auto"
                )
                self._tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-7B-Instruct")
                self._is_initialized = True
                
                # GPU 메모리 사용량 확인
                if torch.cuda.is_available():
                    gpu_memory = torch.cuda.memory_allocated() / 1024**3
                    logger.info(f"✅ Qwen 모델 로딩 완료! (GPU 메모리: {gpu_memory:.1f}GB 사용)")
                else:
                    logger.info("✅ Qwen 모델 로딩 완료! (CPU 사용)")
                    
            except Exception as e:
                logger.error(f"❌ Qwen 모델 로딩 실패: {str(e)}")
                self._is_initialized = False
                raise
    
    @property
    def model(self):
        """모델 인스턴스 반환"""
        if not self._is_initialized:
            raise RuntimeError("Qwen 모델이 초기화되지 않았습니다. initialize()를 먼저 호출하세요.")
        return self._model
    
    @property
    def tokenizer(self):
        """토크나이저 인스턴스 반환"""
        if not self._is_initialized:
            raise RuntimeError("Qwen 모델이 초기화되지 않았습니다. initialize()를 먼저 호출하세요.")
        return self._tokenizer
    
    @property
    def is_ready(self):
        """모델이 사용 준비되었는지 확인"""
        return self._is_initialized and self._model is not None and self._tokenizer is not None


# 전역 인스턴스 생성
qwen_model = QwenModel()