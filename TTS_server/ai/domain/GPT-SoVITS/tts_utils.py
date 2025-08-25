"""
GPT-SoVITS TTS 유틸리티 함수들
다른 프로젝트에서 import하여 사용할 수 있습니다.
"""

import os
import sys
import subprocess
import wave
import numpy as np
import soundfile as sf
from io import BytesIO
from typing import Generator, Optional, Dict, Any


def setup_paths(gpt_sovits_root: str = None):
    """
    GPT-SoVITS 경로를 설정합니다.
    
    Args:
        gpt_sovits_root: GPT-SoVITS 프로젝트 루트 경로
    """
    if gpt_sovits_root is None:
        # 현재 파일의 위치를 기준으로 GPT-SoVITS 루트 찾기
        current_dir = os.path.dirname(os.path.abspath(__file__))
        gpt_sovits_root = current_dir
    
    if gpt_sovits_root not in sys.path:
        sys.path.append(gpt_sovits_root)
    
    gpt_sovits_path = os.path.join(gpt_sovits_root, "GPT_SoVITS")
    if gpt_sovits_path not in sys.path:
        sys.path.append(gpt_sovits_path)


class TTSProcessor:
    """TTS 처리를 위한 클래스"""
    
    def __init__(self, config_path: str = None, gpt_sovits_root: str = None):
        """
        TTS 프로세서 초기화
        
        Args:
            config_path: TTS 설정 파일 경로
            gpt_sovits_root: GPT-SoVITS 프로젝트 루트 경로
        """
        setup_paths(gpt_sovits_root)
        
        # GPT-SoVITS 모듈들을 여기서 import
        try:
            from GPT_SoVITS.TTS_infer_pack.TTS import TTS, TTS_Config
            from GPT_SoVITS.TTS_infer_pack.text_segmentation_method import get_method_names as get_cut_method_names
            from tools.i18n.i18n import I18nAuto
        except ImportError as e:
            raise ImportError(f"GPT-SoVITS 모듈을 import할 수 없습니다: {e}")
        
        # 설정 파일 경로 설정
        if config_path is None:
            if gpt_sovits_root:
                config_path = os.path.join(gpt_sovits_root, "GPT_SoVITS", "configs", "tts_infer.yaml")
            else:
                config_path = "GPT_SoVITS/configs/tts_infer.yaml"
        
        # 설정 파일 존재 확인
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"설정 파일을 찾을 수 없습니다: {config_path}")
        
        # TTS 초기화
        self.tts_config = TTS_Config(config_path)
        self.tts_pipeline = TTS(self.tts_config)
        self.cut_method_names = get_cut_method_names()
        self.i18n = I18nAuto()
        
        print(f"TTS 프로세서가 초기화되었습니다. 설정 파일: {config_path}")
    
    def pack_ogg(self, io_buffer: BytesIO, data: np.ndarray, rate: int):
        """OGG 형식으로 오디오 패킹"""
        with sf.SoundFile(io_buffer, mode="w", samplerate=rate, channels=1, format="ogg") as audio_file:
            audio_file.write(data)
        return io_buffer
    
    def pack_raw(self, io_buffer: BytesIO, data: np.ndarray, rate: int):
        """RAW 형식으로 오디오 패킹"""
        io_buffer.write(data.tobytes())
        return io_buffer
    
    def pack_wav(self, io_buffer: BytesIO, data: np.ndarray, rate: int):
        """WAV 형식으로 오디오 패킹"""
        io_buffer = BytesIO()
        sf.write(io_buffer, data, rate, format="wav")
        return io_buffer
    
    def pack_aac(self, io_buffer: BytesIO, data: np.ndarray, rate: int):
        """AAC 형식으로 오디오 패킹"""
        process = subprocess.Popen(
            [
                "ffmpeg",
                "-f", "s16le",
                "-ar", str(rate),
                "-ac", "1",
                "-i", "pipe:0",
                "-c:a", "aac",
                "-b:a", "192k",
                "-vn",
                "-f", "adts",
                "pipe:1",
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        out, _ = process.communicate(input=data.tobytes())
        io_buffer.write(out)
        return io_buffer
    
    def pack_audio(self, io_buffer: BytesIO, data: np.ndarray, rate: int, media_type: str):
        """지정된 형식으로 오디오 패킹"""
        if media_type == "ogg":
            io_buffer = self.pack_ogg(io_buffer, data, rate)
        elif media_type == "aac":
            io_buffer = self.pack_aac(io_buffer, data, rate)
        elif media_type == "wav":
            io_buffer = self.pack_wav(io_buffer, data, rate)
        else:
            io_buffer = self.pack_raw(io_buffer, data, rate)
        io_buffer.seek(0)
        return io_buffer
    
    def wave_header_chunk(self, frame_input=b"", channels=1, sample_width=2, sample_rate=32000):
        """WAV 헤더 청크 생성"""
        wav_buf = BytesIO()
        with wave.open(wav_buf, "wb") as vfout:
            vfout.setnchannels(channels)
            vfout.setsampwidth(sample_width)
            vfout.setframerate(sample_rate)
            vfout.writeframes(frame_input)
        wav_buf.seek(0)
        return wav_buf.read()
    
    def check_params(self, req: dict):
        """요청 파라미터 검증"""
        text: str = req.get("text", "")
        text_lang: str = req.get("text_lang", "")
        ref_audio_path: str = req.get("ref_audio_path", "")
        streaming_mode: bool = req.get("streaming_mode", False)
        media_type: str = req.get("media_type", "wav")
        prompt_lang: str = req.get("prompt_lang", "")
        text_split_method: str = req.get("text_split_method", "cut5")
        
        if ref_audio_path in [None, ""]:
            return {"error": "ref_audio_path is required"}
        if text in [None, ""]:
            return {"error": "text is required"}
        if text_lang in [None, ""]:
            return {"error": "text_lang is required"}
        elif text_lang.lower() not in self.tts_config.languages:
            return {"error": f"text_lang: {text_lang} is not supported in version {self.tts_config.version}"}
        if prompt_lang in [None, ""]:
            return {"error": "prompt_lang is required"}
        elif prompt_lang.lower() not in self.tts_config.languages:
            return {"error": f"prompt_lang: {prompt_lang} is not supported in version {self.tts_config.version}"}
        if media_type not in ["wav", "raw", "ogg", "aac"]:
            return {"error": f"media_type: {media_type} is not supported"}
        elif media_type == "ogg" and not streaming_mode:
            return {"error": "ogg format is not supported in non-streaming mode"}
        
        if text_split_method not in self.cut_method_names:
            return {"error": f"text_split_method:{text_split_method} is not supported"}
        
        return None
    
    def process_tts(self, req: dict):
        """
        TTS 처리 메인 함수
        
        Args:
            req: TTS 요청 딕셔너리
            
        Returns:
            (sample_rate, audio_data) 또는 에러 딕셔너리
        """
        # 파라미터 검증
        check_res = self.check_params(req)
        if check_res is not None:
            return check_res
        
        streaming_mode = req.get("streaming_mode", False)
        return_fragment = req.get("return_fragment", False)
        
        if streaming_mode or return_fragment:
            req["return_fragment"] = True
        
        try:
            tts_generator = self.tts_pipeline.run(req)
            
            if streaming_mode:
                # 스트리밍 모드
                return self._streaming_generator(tts_generator, req.get("media_type", "wav"))
            else:
                # 일반 모드
                sr, audio_data = next(tts_generator)
                return {"sample_rate": sr, "audio_data": audio_data}
                
        except Exception as e:
            return {"error": f"TTS 처리 실패: {str(e)}"}
    
    def _streaming_generator(self, tts_generator: Generator, media_type: str):
        """스트리밍 생성기"""
        if_first_chunk = True
        for sr, chunk in tts_generator:
            if if_first_chunk and media_type == "wav":
                yield self.wave_header_chunk(sample_rate=sr)
                media_type = "raw"
                if_first_chunk = False
            yield self.pack_audio(BytesIO(), chunk, sr, media_type).getvalue()
    
    def set_gpt_weights(self, weights_path: str):
        """GPT 모델 가중치 변경"""
        try:
            self.tts_pipeline.init_t2s_weights(weights_path)
            return {"success": True}
        except Exception as e:
            return {"error": f"GPT 가중치 변경 실패: {str(e)}"}
    
    def set_sovits_weights(self, weights_path: str):
        """SoVITS 모델 가중치 변경"""
        try:
            self.tts_pipeline.init_vits_weights(weights_path)
            return {"success": True}
        except Exception as e:
            return {"error": f"SoVITS 가중치 변경 실패: {str(e)}"}
    
    def set_ref_audio(self, ref_audio_path: str):
        """참조 오디오 설정"""
        try:
            self.tts_pipeline.set_ref_audio(ref_audio_path)
            return {"success": True}
        except Exception as e:
            return {"error": f"참조 오디오 설정 실패: {str(e)}"}


# 사용 예시
def create_tts_processor(config_path: str = None, gpt_sovits_root: str = None) -> TTSProcessor:
    """
    TTS 프로세서 생성 함수
    
    Args:
        config_path: 설정 파일 경로
        gpt_sovits_root: GPT-SoVITS 프로젝트 루트 경로
        
    Returns:
        TTSProcessor 인스턴스
    """
    return TTSProcessor(config_path, gpt_sovits_root) 