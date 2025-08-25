from TTS import TTS, TTS_Config   # 방금 보낸 파일 이름이 TTS.py라면
# from g2pk import G2p
import soundfile as sf
# --- infer.py 상단부에 추가 ---
import numpy as np
import sounddevice as sd
import wave
from typing import Generator, Tuple
import os



import os
import time
import wave
import numpy as np

from TTS import TTS, TTS_Config
import sounddevice as sd


# ---------- 유틸 ----------
def _float_to_pcm16_bytes(x, volume: float = 1.0) -> bytes:
    """float32 [-1,1] -> int16 PCM bytes (mono 가정)"""
    arr = np.asarray(x, dtype=np.float32).squeeze()
    arr = np.clip(arr * float(volume), -1.0, 1.0)
    return (arr * 32767.0).astype(np.int16).tobytes()


def probe_stream_chunks(tts: TTS, params: dict) -> int:
    """
    TTS.run_stream_chunks(params)가 실제로 여러 청크를 내보내는지 확인.
    반환: total_yields (청크 개수)
    """
    print("\n[probe] run_stream_chunks 동작 확인...")
    t0 = time.perf_counter()
    n = 0
    total_sec = 0.0
    for sr, chunk in tts.run_stream_chunks(params):
        n += 1
        samples = np.asarray(chunk).shape[0]
        secs = samples / float(sr)
        total_sec += secs
        print(f"[{time.perf_counter()-t0:,.3f}s] chunk#{n}: ~{secs:.3f}s (누적={total_sec:.3f}s)")
    print(f"[probe] total_yields={n}, total_audio≈{total_sec:.3f}s\n")
    return n


def play_stream_chunks(
    tts: TTS,
    params: dict,
    *,
    chunk_ms: int = 80,
    volume: float = 1.0,
    save_wav_path: str | None = "output_stream.wav",
):
    """
    TTS.run_stream_chunks(params)를 이용해 즉시 재생(+선택 저장).
    run_stream_chunks가 실제로 여러 번 yield하면 '진짜 스트리밍'으로 바로 들림.
    한 번만 yield하면(완성본) → 그때부터 조각으로 나눠 재생(의사-스트리밍).
    """
    sr0: int | None = None
    stream: sd.RawOutputStream | None = None
    wf: wave.Wave_write | None = None
    bytes_per_frame = 2  # int16 mono
    total_frames = 0

    try:
        for sr, f32 in tts.run_stream_chunks(params):
            if sr0 is None:
                sr0 = int(sr)
                # (필요 시) 출력 장치 지정
                # print(sd.query_devices())
                # sd.default.device = (None, <출력장치인덱스>)
                stream = sd.RawOutputStream(samplerate=sr0, channels=1, dtype="int16")
                stream.start()
                if save_wav_path:
                    wf = wave.open(save_wav_path, "wb")
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(sr0)

            pcm = _float_to_pcm16_bytes(f32, volume=volume)
            step = max(bytes_per_frame, int(sr0 * (chunk_ms / 1000.0)) * bytes_per_frame)
            # 사운드카드가 선호하는 블록 크기로 잘라 write
            for i in range(0, len(pcm), step):
                stream.write(pcm[i : i + step])

            if wf:
                wf.writeframes(pcm)

            total_frames += len(pcm) // bytes_per_frame
    finally:
        if stream:
            stream.stop()
            stream.close()
        if wf:
            wf.close()

    dur = (total_frames / float(sr0)) if sr0 else 0.0
    return (sr0 or 0), dur


def save_stream_wav(tts: TTS, params: dict, out_path: str = "out_stream.wav"):
    """
    TTS.run_stream_bytes(params, media_type="wav")를 이용해
    서버 없이 바로 WAV 스트림(헤더+RAW)을 파일로 저장.
    """
    with open(out_path, "wb") as f:
        for b in tts.run_stream_bytes(params, media_type="wav"):
            f.write(b)
    return out_path

import numpy as np, soundfile as sf

def save_stream_wav_xfade(tts, params, out_path="xfade_stream.wav", xfade_ms=60):
    sr0 = None
    ov = None
    assembled = None  # float32 누적 버퍼

    for sr, f32 in tts.run_stream_chunks(params):
        f32 = np.asarray(f32, dtype=np.float32).squeeze()
        if sr0 is None:
            sr0 = int(sr)
            ov = int(sr0 * (xfade_ms/1000.0))
            assembled = f32.copy()
            continue

        if ov > 0 and f32.size > ov and assembled.size > ov:
            head = f32[:ov]
            tail = assembled[-ov:]
            w = np.hanning(ov*2)[ov:]  # 0..1
            mixed = tail*(1.0 - w) + head*w
            assembled = np.concatenate([assembled[:-ov], mixed, f32[ov:]], axis=0)
        else:
            assembled = np.concatenate([assembled, f32], axis=0)

    if assembled is None:
        raise RuntimeError("no audio produced")

    # 최종 한 번만 -1..1 클리핑 → int16
    assembled = np.clip(assembled, -1.0, 1.0)
    sf.write(out_path, assembled, sr0, subtype="PCM_16")
    return out_path

def iter_stream_chunks(
    tts: TTS,
    params: dict,
    *,
    frame_ms: int | None = 80,   # 재생 블록 크기. None이면 쪼개지 않고 그대로
    to_float32: bool = True,     # sounddevice 등과 맞추려면 True 권장
):
    """
    TTS.run(params)를 return_fragment=True로 호출해서
    (sr, chunk) 스트림을 만들어 (선택) frame_ms 단위로 쪼개서 yield.
    """
    p = dict(params)
    p["return_fragment"] = True
    # 스트리밍 지연/끊김 줄이기 위한 기본값
    p.setdefault("batch_size", 1)
    p.setdefault("split_bucket", False)
    p.setdefault("parallel_infer", False)
    # 이 코드 베이스는 fragment_interval<0.01이면 0.01로 강제됨(=최소 10ms 공백)
    p.setdefault("fragment_interval", 0.01)

    for sr, i16 in tts.run(p):              # i16: np.int16 (mono)
        if to_float32:
            buf = i16.astype(np.float32) / 32768.0
        else:
            buf = i16                       # 그대로 int16

        if frame_ms is None:
            yield sr, buf
        else:
            step = max(1, int(sr * (frame_ms / 1000.0)))
            for i in range(0, len(buf), step):
                yield sr, buf[i:i+step]

# ---------- 메인 ----------
def main():
    # (1) 환경/가중치 설정
    cfg = {
    "device": "cuda",
    "is_half": True,                         # 40~50 시리즈에서 속도↑. 문제 있으면 False
    "version": "v2ProPlus",                  # ← 대/소문자 중요
    "t2s_weights_path": r"C:\jaeheon\small_infer\sovits_models\s1bert25hz-5kh-longer-epoch=12-step=369668.ckpt",
    "vits_weights_path": r"C:\jaeheon\small_infer\sovits_models\v2pro\s2Gv2ProPlus.pth",
    "bert_base_path":  r"C:\jaeheon\small_infer\sovits_models\chinese-roberta-wwm-ext-large",
    "cnhuhbert_base_path": r"C:\jaeheon\small_infer\sovits_models\chinese-hubert-base",
}

    ref_wav = r"C:\jaeheon\small_infer\sovits_models\my_voice_03.wav"
      
# 2) 합성
    

    if not os.path.exists(ref_wav):
        raise FileNotFoundError(f"참조 음성 파일을 찾을 수 없습니다: {ref_wav}")
    print(">> cfg.version =", repr(cfg.get("version")))

    print("[1/3] TTS 모델/가중치 로드 중...")
    tts = TTS(TTS_Config({"custom": cfg}))
    print("[2/3] 참조 음성 등록:", ref_wav)
    tts.set_ref_audio(ref_wav)


    # 합성 파라미터 (probe/stream/save 공통)
    params = {
        "text": "안녕하세요 또 오셨군요 저희는 음성으로 대화하는 오라서비스 입니다. 오늘 하루는 어떠셨나요?",
        "text_split_method": "cut15",
        "text_lang": "ko",
        "ref_audio_path": ref_wav,  # set_ref_audio 했어도 유지
        "prompt_text": "안녕히계세요 좋은 하루되세요!",
        "prompt_lang": "ko",
        "top_k": 5,
        "top_p": 0.9,
        "return_fragment": False,  # 내부 스트리밍 유도(브랜치에 따라 무시될 수 있음)
    }

    # params.update({
    # "return_fragment": True,
    # "streaming_mode": True,       # 일부 브랜치는 이 키도 확인
    # "text_split_method": "cut5",  # 없으면 "cut0"
    # "batch_size": 1,              # 묶지 말고 1개씩
    # "parallel_infer": False,      # 직렬 추론
    # "split_bucket": False,        # return_fragment면 어차피 False
    # "fragment_interval": 0.0,     # 청크 사이 무음 제거
    # "text": "안녕하세요 좋은 하루입니다. 안녕하세요 좋은 하루입니다. 안녕하세요 좋은 하루입니다.",
    # })

#     params.update({
#     "return_fragment": True,
#     "streaming_mode": True,
#     "chunk_chars": 10,          # ★ 길이 분할 핵심
#     "batch_size": 1,
#     "parallel_infer": False,
#     "split_bucket": False,
#     "fragment_interval": 0.0,   # ★ 0ms 갭 (위 패치 적용했을 때만)
# })
    

    print("\n[대기] 모델 로드 완료. 무엇을 할까요?")
    print("  Enter : 스트리밍 재생 시작 (output_stream.wav 저장 포함)")
    print("  p + Enter : probe 실행(청크 개수/타이밍 확인) 후 계속")
    print("  w + Enter : 스트리밍 WAV만 파일로 저장(out_stream.wav), 재생 없음")
    print("  q + Enter : 종료")
    cmd = input("> ").strip().lower()

    if cmd == "q":
        sr, wav = next(tts.run({
        "text": "안녕하세요 또 오셨군요 저희는 음성으로 대화하는 오라서비스 입니다. 오늘 하루는 어떠셨나요??",
        "text_lang":    "ko",

        # 필수는 아님 ─ 음성을 이미 set_ref_audio() 로 넣었으니까
        "ref_audio_path": "C:\jaeheon\small_infer\sovits_models\my_voice_03.wav",

        # ↓ (참조 문장을 사용하고 싶을 때만) ↓
        "prompt_text":  "안녕히계세요 좋은 하루되세요!",
        "prompt_lang":  "ko",

        "top_k": 5,
        "top_p": 0.9
    }))

        sf.write("output2.wav", wav, sr)
        print("저장 완료 → output.wav")

    if cmd == "p":
        # total = probe_stream_chunks(tts, params)
        total = 0
        if total <= 1:
            print("⚠️ 내부 스트리밍이 비활성(혹은 무시)된 것으로 보입니다. (완성본 1회 반환)")
            print("   그래도 아래 스트리밍 재생은 의사-스트리밍으로 동작합니다.")
        input("\n계속하려면 Enter를 누르세요...")
        cmd = ""  # 이후 Enter 처리와 동일하게 진행

    # if cmd == "w":
    #     out_path = save_stream_wav_xfade(tts, params, out_path="xfade_stream.wav", xfade_ms=60)
    #     print(f"[저장 완료] {out_path}")
    #     return
    if cmd == "w":
            out_path = "out_stream.wav"

            # 실시간 스트리밍 저장 (재생 없음)
            sr0 = None
            wf = None
            try:
                # iter_stream_chunks: return_fragment=True 강제 + 프레임 단위로 청크 생성
                # 파일 저장은 청크 쪼갤 필요 없으니 frame_ms=None 권장
                for sr, chunk in iter_stream_chunks(tts, params, frame_ms=None, to_float32=True):
                    if wf is None:
                        sr0 = int(sr)
                        wf = wave.open(out_path, "wb")
                        wf.setnchannels(1)
                        wf.setsampwidth(2)   # int16
                        wf.setframerate(sr0)

                    wf.writeframes(_float_to_pcm16_bytes(chunk))

                    # (선택) 디스크에 바로 플러시하고 싶으면 아래 주석 해제
                    # try:
                    #     wf._file.flush(); os.fsync(wf._file.fileno())
                    # except Exception:
                    #     pass

            finally:
                if wf:
                    wf.close()

            print(f"[저장 완료] {out_path} ({sr0} Hz)")
            return
    
    # 기본(Enter 또는 p 이후): 스트리밍 재생(+저장)
    print("\n[3/3] 합성/재생 시작 (run_stream_chunks)...")
    # sr, dur = play_stream_chunks(
    #     tts,
    #     params,
    #     chunk_ms=80,
    #     volume=1.0,
    #     save_wav_path="output_stream.wav",  # 저장 원치 않으면 None
    # )
    print(f"완료: sr={sr},  저장=output_stream.wav")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n사용자 중단")

# cfg = {
#     "device": "cuda",
#     "is_half": True,
#     "version": "v2",
#     "t2s_weights_path": r"C:\jaeheon\small_infer\sovits_models\s1bert25hz-5kh-longer-epoch=12-step=369668.ckpt",
#     "vits_weights_path": r"C:\jaeheon\small_infer\sovits_models\s2G2333k.pth",
#     "bert_base_path":  r"C:\jaeheon\small_infer\sovits_models\chinese-roberta-wwm-ext-large",
#     "cnhuhbert_base_path": r"C:\jaeheon\small_infer\sovits_models\chinese-hubert-base",
# }

# print("여기까진잘감?")
# import soundfile as sf, os, subprocess, shutil, numpy as np, librosa, sys, traceback, ffmpeg

# wav = r"C:\jaeheon\small_infer\sovits_models\my_voice_03.wav"   # ← 절대경로 raw-string
# print("존재?", os.path.exists(wav))

# try:
#     data, sr = sf.read(wav, dtype="float32")
#     print("SoundFile OK → shape:", data.shape, "sr:", sr)
# except Exception as e:
#     print("SoundFile 실패:", e)

# print("FFmpeg PATH:", shutil.which("ffmpeg"))


# tts = TTS(TTS_Config({"custom": cfg}))

# # 1) (한 번) 3~10초짜리 참조 음성 등록
# tts.set_ref_audio("C:/jaeheon/small_infer/sovits_models/my_voice_03.wav")   # ← 파일만 넘깁니다.
# # 2) 합성
# sr, wav = next(tts.run({
#     "text":         "간장 공장 공장장은 강 공장장이고 된장 공장 공장장은 공 공장장이다.",
#     "text_lang":    "ko",

#     # 필수는 아님 ─ 음성을 이미 set_ref_audio() 로 넣었으니까
#     "ref_audio_path": "C:/jaeheon/small_infer/sovits_models/my_voice_03.wav",

#     # ↓ (참조 문장을 사용하고 싶을 때만) ↓
#     "prompt_text":  "안녕히계세요 좋은 하루되세요!",
#     "prompt_lang":  "ko",

#     "top_k": 5,
#     "top_p": 0.9
# }))

# sf.write("output2.wav", wav, sr)
# print("저장 완료 → output.wav")
