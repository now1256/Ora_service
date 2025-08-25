
# 수정재헌

"""
api_v2.py ― GPT-SoVITS TTS 엔진 (Django 버전)
FastAPI → Django HttpResponse/StreamingHttpResponse/JsonResponse 로 치환
"""
import time
import os
import sys
import json
import signal
import subprocess
import wave
from io import BytesIO
from typing import Generator, Iterable, Optional
import yaml
from scipy.signal import resample_poly
import math
from django.http import (
    JsonResponse,
    HttpResponse,
    StreamingHttpResponse,
)
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

import numpy as np
import soundfile as sf

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
TTS_MODULE_DIR = os.path.join(ROOT_DIR, "GPT_SoVITS")

sys.path.append(ROOT_DIR)
sys.path.append(TTS_MODULE_DIR)

config_path = os.path.join(ROOT_DIR, "GPT_SoVITS", "configs", "tts_infer.yaml")
print(config_path)

#이거 고쳐야할수도
with open(config_path, "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

for key in ["bert_base_path", "cnhuhbert_base_path", "t2s_weights_path","vits_weights_path"]:
    if key in config["custom"]:
        rel_path = config["custom"][key]
        abs_path = os.path.join(ROOT_DIR, rel_path)
        config["custom"][key] = os.path.abspath(abs_path)

# 다시 저장
with open(config_path, "w", encoding="utf-8") as f:
    yaml.dump(config, f, allow_unicode=True)
print("-------------------------------")
print(config_path)



from tools.i18n.i18n import I18nAuto
from GPT_SoVITS.TTS_infer_pack.TTS import TTS, TTS_Config
from GPT_SoVITS.TTS_infer_pack.text_segmentation_method import (
    get_method_names as get_cut_method_names,
)

i18n = I18nAuto()
CUT_METHOD_NAMES = get_cut_method_names()



# ----- Init pipeline (모듈 로드 시 1회) -----
tts_config = TTS_Config(config_path)
print("뭔가이상한데")
print(tts_config)
tts_pipeline = TTS(tts_config)


# =========================
# Audio packing helpers
# =========================
def pack_ogg(io_buffer: BytesIO, data: np.ndarray, rate: int) -> BytesIO:
    with sf.SoundFile(io_buffer, mode="w", samplerate=rate, channels=1, format="ogg"):
        io_buffer.write(data)
    return io_buffer


def pack_raw(io_buffer: BytesIO, data: np.ndarray, rate: int) -> BytesIO:
    io_buffer.write(data.tobytes())
    return io_buffer

def to_float32(x: np.ndarray) -> np.ndarray:
    if x.dtype == np.int16:
        x = x.astype(np.float32) / 32768.0
    elif x.dtype == np.int32:
        x = x.astype(np.float32) / 2147483648.0
    else:
        x = x.astype(np.float32)
    return np.nan_to_num(x, nan=0.0, posinf=0.0, neginf=0.0)

def resample_to(x: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
    if orig_sr == target_sr:
        return x
    # (N,) 또는 (N, C) 형태를 기대. (C, N)이면 전치 필요
    if x.ndim == 2 and x.shape[0] < x.shape[1]:
        pass
    elif x.ndim == 2:
        x = x.T
    g = math.gcd(orig_sr, target_sr)
    up, down = target_sr // g, orig_sr // g
    return resample_poly(x, up, down, axis=0)

def amplify_db(data: np.ndarray, gain_db: float = 0.0) -> np.ndarray:
    factor = 10 ** (gain_db / 20.0)
    y = to_float32(data) * factor
    return np.clip(y, -1.0, 1.0).astype(np.float32)

def pack_wav(io_buffer: BytesIO, data: np.ndarray, rate: int) -> BytesIO:
    # 1) 볼륨 원하는 만큼 (예: +3 dB)
    y = amplify_db(data, gain_db=10.0)

    # 2) 32k → 24k 리샘플
    out_sr = 8000
    y24 = resample_to(y, orig_sr=rate, target_sr=out_sr)

    # 3) 저장
    sf.write(io_buffer, y24, out_sr, format="wav")
    return io_buffer

def pack_aac(io_buffer: BytesIO, data: np.ndarray, rate: int) -> BytesIO:
    # ffmpeg 필요(시스템 PATH)
    process = subprocess.Popen(
        [
            "ffmpeg",
            "-f",
            "s16le",
            "-ar",
            str(rate),
            "-ac",
            "1",
            "-i",
            "pipe:0",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-vn",
            "-f",
            "adts",
            "pipe:1",
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    out, _ = process.communicate(input=data.tobytes())
    io_buffer.write(out)
    return io_buffer


def pack_audio(io_buffer: BytesIO, data: np.ndarray, rate: int, media_type: str) -> BytesIO:
    if media_type == "ogg":
        io_buffer = pack_ogg(io_buffer, data, rate)
    elif media_type == "aac":
        io_buffer = pack_aac(io_buffer, data, rate)
    elif media_type == "wav":
        io_buffer = pack_wav(io_buffer, data, rate)
    else:
        io_buffer = pack_raw(io_buffer, data, rate)
    io_buffer.seek(0)
    return io_buffer


def wave_header_chunk(frame_input=b"", channels=1, sample_width=2, sample_rate=32000) -> bytes:
    # 스트리밍 WAV의 첫 조각에만 헤더를 추가할 때 사용
    wav_buf = BytesIO()
    with wave.open(wav_buf, "wb") as vfout:
        vfout.setnchannels(channels)
        vfout.setsampwidth(sample_width)
        vfout.setframerate(sample_rate)
        vfout.writeframes(frame_input)
    wav_buf.seek(0)
    return wav_buf.read()


# =========================
# Utility
# =========================
def _lower_or_empty(s: Optional[str]) -> str:
    return "" if s in (None, "") else str(s).lower()


def check_params(req: dict) -> Optional[JsonResponse]:
    text: str = req.get("text", "")
    text_lang: str = req.get("text_lang", "")
    ref_audio_path: str = req.get("ref_audio_path", "")
    streaming_mode: bool = req.get("streaming_mode", False)
    media_type: str = req.get("media_type", "wav")
    prompt_lang: str = req.get("prompt_lang", "")
    text_split_method: str = req.get("text_split_method", "cut5")

    if ref_audio_path in (None, ""):
        return JsonResponse({"message": "ref_audio_path is required"}, status=400)
    if text in (None, ""):
        return JsonResponse({"message": "text is required"}, status=400)
    if text_lang in (None, ""):
        return JsonResponse({"message": "text_lang is required"}, status=400)
    elif text_lang.lower() not in tts_config.languages:
        return JsonResponse(
            {"message": f"text_lang: {text_lang} is not supported in version {tts_config.version}"},
            status=400,
        )
    if prompt_lang in (None, ""):
        return JsonResponse({"message": "prompt_lang is required"}, status=400)
    elif prompt_lang.lower() not in tts_config.languages:
        return JsonResponse(
            {"message": f"prompt_lang: {prompt_lang} is not supported in version {tts_config.version}"},
            status=400,
        )
    if media_type not in ["wav", "raw", "ogg", "aac"]:
        return JsonResponse({"message": f"media_type: {media_type} is not supported"}, status=400)
    elif media_type == "ogg" and not streaming_mode:
        return JsonResponse({"message": "ogg format is not supported in non-streaming mode"}, status=400)

    if text_split_method not in CUT_METHOD_NAMES:
        return JsonResponse({"message": f"text_split_method:{text_split_method} is not supported"}, status=400)

    return None


def tts_streaming_iter(tts_generator: Generator, media_type: str) -> Iterable[bytes]:
    """Django StreamingHttpResponse용 제너레이터"""
    first = True
    _media = media_type  # 로컬 변수로 유지
    for sr, chunk in tts_generator:
        # WAV의 첫 조각은 헤더부터
        if first and _media == "wav":
            yield wave_header_chunk(sample_rate=sr)
            _media = "raw"
            first = False
        buf = pack_audio(BytesIO(), chunk, sr, _media)
        yield buf.getvalue()


def tts_handle(req: dict):
    """
    FastAPI 버전의 tts_handle을 Django에 맞게 포팅
    - streaming_mode=True면 StreamingHttpResponse 반환
    - 아니면 단일 HttpResponse 반환
    - 오류는 JsonResponse로
    """
    streaming_mode = bool(req.get("streaming_mode", False))
    return_fragment = bool(req.get("return_fragment", False))
    media_type = req.get("media_type", "wav")
    print("여기는잘옴?4")
    start_time = time.time()
    processing_time = time.time() - start_time
    print(f"**************실제 모델 체크 ************* ({processing_time:.3f}초)")

    res = check_params(req)
    if isinstance(res, JsonResponse):
        return res

    if streaming_mode or return_fragment:
        req["return_fragment"] = True

    try:
        tts_generator = tts_pipeline.run(req)
        processing_time = time.time() - start_time
        print(f"**************실제 모델 들어감 ************* ({processing_time:.3f}초)")
        if streaming_mode:
            return StreamingHttpResponse(
                streaming_content=tts_streaming_iter(tts_generator, media_type),
                content_type=f"audio/{media_type}",
            )
        else:
            try:
                sr, audio_data = next(tts_generator)
                tts_generator = tts_pipeline.run(req)

                processing_time = time.time() - start_time
                print(f"**************실제 모델 들어갔을시간 ************* ({processing_time:.3f}초)")
                pay_load = audio_data
                payload = pack_audio(BytesIO(), audio_data, sr, media_type).getvalue()
                processing_time = time.time() - start_time
                print(f"**************pay_load 바꾸는 시간************* ({processing_time:.3f}초)")
            except Exception as e:
                import traceback
                print("GEN ERROR at first next():", repr(e), flush=True)
                print(traceback.format_exc(), flush=True)
                return JsonResponse({"message": "tts failed at first next()", "Exception": str(e)}, status=400)
            # 원래는 여기서 다 보내주는데 함수 분할을 위해 여기서는 payload만 반환하게 변경
            # return HttpResponse(payload, content_type=f"audio/{media_type}")
            return payload

    except Exception as e:
        return JsonResponse({"message": "tts failed", "Exception": str(e)}, status=400)


def handle_control(command: str):
    if command == "restart":
        # 관리 프로세스(PM2/gunicorn/uwsgi) 환경에 따라 동작 보장 X
        os.execl(sys.executable, sys.executable, *sys.argv)
    elif command == "exit":
        os.kill(os.getpid(), signal.SIGTERM)
        os._exit(0)

