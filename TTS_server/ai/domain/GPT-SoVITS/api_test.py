# client_play_raw.py
import requests, sounddevice as sd
import numpy as np

URL = "http://localhost:5002/tts"
params = {
    "text": "안녕하세요 오라서비스입니다 오늘 기분은 어떠셨나요?",
    "text_lang": "ko",
    "ref_audio_path": r"/home/pascal/Ora/jaeheon/OraAiServer/TTS_server/media/real_tts_1751820298.wav",
    "prompt_lang": "ko",
    "prompt_text": "안녕하세요 안녕히계세요.",
    "text_split_method": "cut0",
    "batch_size": 1,
    "streaming_mode": False,
    "media_type": "raw",  # 순수 PCM
}
SR = 24000  # v2면 32000. (v3=24000, v4=48000)

with requests.get(URL, params=params, stream=True) as r:
    r.raise_for_status()
    with sd.RawOutputStream(samplerate=SR, channels=1, dtype="int16") as stream:
        for chunk in r.iter_content(chunk_size=4096):
            if not chunk:
                continue
            arr = np.frombuffer(chunk, dtype=np.int16).astype(np.float32) / 32768.0
            arr *= 20.0  # 1.5~4.0 사이 테스트
            arr = np.clip(arr, -1.0, 1.0)
            stream.write((arr * 32768.0).astype(np.int16).tobytes())

# import requests

# params = {
#     "text": "이거 진짜 긴텍스트인데 뽑는데 얼마나 걸릴까요? 한번 알아맞춰보세요",
#     "text_lang": "ko",
#     "ref_audio_path": r"/code/media/my_voice_03.wav",
#     "prompt_lang": "ko",
#     "prompt_text": "안녕하세요 안녕히계세요.",
#     "text_split_method": "cut0"
# }
# r = requests.get("http://localhost:5002/tts", params=params)
# with open("output.wav", "wb") as f:
#     f.write(r.content)
# print("저장 완료!")
