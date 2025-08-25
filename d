Starting with Uvicorn directly for faster reload...
🔧 TTS 디바이스 설정: cuda
🎤 TTS 엔진 로더 초기화...
🔧 디바이스: cuda
🔧 CUDA 사용 가능: True
🔧 선택된 TTS 엔진: coqui
🔧 지원되는 엔진: ['gtts', 'coqui']
🎤 TTS 엔진 초기화 중... (타입: coqui)
🎤 Coqui TTS 모델 초기화 중... (시간이 오래 걸릴 수 있습니다)
🔄 모델 시도: tts_models/multilingual/multi-dataset/xtts_v2
 > Downloading model to /root/.local/share/tts/tts_models--multilingual--multi-dataset--xtts_v2
 > Model's license - CPML
 > Check https://coqui.ai/cpml.txt for more info.
 > Using model: xtts
✅ GPU로 모델 이동 완료: cuda
✅ Coqui TTS 모델 초기화 성공: tts_models/multilingual/multi-dataset/xtts_v2
✅ TTS 엔진 초기화 성공: coqui
✅ Coqui TTS 초기화 성공!
🎤 TTS 서버 시작 - Kafka Consumer 초기화 중...
✅ TTS Kafka Consumer 스레드 시작됨
🚀 [TTS Kafka Consumer] 초기화
📡 Kafka 서버: ['kafka:9092']
📢 구독 토픽: TTSREQUEST
🔗 Channel Layer: ✅ 사용 가능
🔄 [Kafka Consumer] 시작 중...
📡 연결 대상: ['kafka:9092']
📢 토픽: TTSREQUEST
✅ [Kafka Consumer] 시작 완료
📊 Consumer 설정:
  - Group ID: tts-consumer-group
  - Auto Offset Reset: latest
  - Consumer Timeout: 1초
🔄 메시지 수신 대기 중...

================================================================================
📨 [LLM → TTS] 새 메시지 수신!
⏰ 수신 시간: 2025-07-25 13:59:35.161
📍 파티션: 8, 오프셋: 0
📏 메시지 크기: 382 chars
================================================================================
🔍 [메시지 구조 분석]
📋 원본 메시지 키들: ['id', 'timestamp', 'service', 'data']
📦 [LLM_server 메시지 감지] 'data' 필드에서 실제 메시지 추출
🆔 외부 메시지 ID: a4ac9e68-4ba2-457b-b3c3-e64e07e869c4
⏰ 외부 타임스탬프: 2025-07-25T13:59:35.144356
🏷️ 서비스: LLM_server
📋 내부 메시지 키들: ['text', 'source', 'phoneId', 'sessionId', 'requestId', 'timestamp', 'request_type']
📝 텍스트: '물론입니다! 다른 질문이나 궁금한 점이 있으시면 언제든지 말씀해 주세요. 도와드리겠습니다!' (길이: 50 문자)
🎙️ 음성 설정: {}
🆔 요청 ID: unknown
⏱️ LLM 생성 시간: 2025-07-25 13:59:33
🕐 처리 지연 시간: 1.94초

🎤 [TTS 처리 시작] 요청 ID: unknown
🎯 [TTS 처리] 메시지 처리 시작
📝 [TTS 처리] 입력 텍스트: '물론입니다! 다른 질문이나 궁금한 점이 있으시면 언제든지 말씀해 주세요. 도와드리겠습니다!'
🎙️ [TTS 처리] 음성 설정: {}
🆔 [TTS 처리] 요청 ID: kafka_1753451975
🎤 [TTS 처리] 실제 음성 변환 시작
text: 물론입니다! 다른 질문이나 궁금한 점이 있으시면 언제든지 말씀해 주세요. 도와드리겠습니다!
[coqui 음성 변환 실행!]
 > Text splitted to sentences.
['물론입니다!', '다른 질문이나 궁금한 점이 있으시면 언제든지 말씀해 주세요.', '도와드리겠습니다!']
❌ Coqui TTS 변환 오류: Failed to open the input "/code/TTS_server/ai/utils/speaker.wav" (No such file or directory).
Exception raised from get_input_format_context at /__w/audio/audio/pytorch/audio/src/libtorio/ffmpeg/stream_reader/stream_reader.cpp:42 (most recent call first):
frame #0: c10::Error::Error(c10::SourceLocation, std::string) + 0x96 (0x763f0136c446 in /root/.local/lib/python3.11/site-packages/torch/lib/libc10.so)
frame #1: c10::detail::torchCheckFail(char const*, char const*, unsigned int, std::string const&) + 0x64 (0x763f013166e4 in /root/.local/lib/python3.11/site-packages/torch/lib/libc10.so)
frame #2: <unknown function> + 0x42134 (0x763df39fd134 in /root/.local/lib/python3.11/site-packages/torio/lib/libtorio_ffmpeg5.so)
frame #3: torio::io::StreamingMediaDecoder::StreamingMediaDecoder(std::string const&, std::optional<std::string> const&, std::optional<std::map<std::string, std::string, std::less<std::string>, std::allocator<std::pair<std::string const, std::string> > > > const&) + 0x14 (0x763df39ffb34 in /root/.local/lib/python3.11/site-packages/torio/lib/libtorio_ffmpeg5.so)
frame #4: <unknown function> + 0x3a8de (0x763de57998de in /root/.local/lib/python3.11/site-packages/torio/lib/_torio_ffmpeg5.so)
frame #5: <unknown function> + 0x323ee (0x763de57913ee in /root/.local/lib/python3.11/site-packages/torio/lib/_torio_ffmpeg5.so)
<omitting python frames>
frame #11: <unknown function> + 0xfc8b (0x763df3a42c8b in /root/.local/lib/python3.11/site-packages/torchaudio/lib/_torchaudio.so)
frame #48: <unknown function> + 0x891f5 (0x763f03e311f5 in /usr/lib/x86_64-linux-gnu/libc.so.6)
frame #49: __clone + 0x40 (0x763f03eb0b00 in /usr/lib/x86_64-linux-gnu/libc.so.6)

🎤 [TTS 처리] 파일이름  kafka_tts_ko_1753451975.mp3
⏱️ [TTS 처리] 음성 생성 시간: 0.01초
✅ [TTS 파일] MP3 파일 생성 완료: kafka_tts_ko_1753451975.mp3
❌ [TTS 처리] 음성 변환 실패: 생성된 MP3 파일을 찾을 수 없음: kafka_tts_ko_1753451975.mp3
✅ [LLM → TTS] 메시지 처리 완료
================================================================================

🔧 TTS 디바이스 설정: cuda
🎤 TTS 엔진 로더 초기화...
🔧 디바이스: cuda
🔧 CUDA 사용 가능: True
🔧 선택된 TTS 엔진: coqui
🔧 지원되는 엔진: ['gtts', 'coqui']
🎤 TTS 엔진 초기화 중... (타입: coqui)
🎤 Coqui TTS 모델 초기화 중... (시간이 오래 걸릴 수 있습니다)
🔄 모델 시도: tts_models/multilingual/multi-dataset/xtts_v2
 > tts_models/multilingual/multi-dataset/xtts_v2 is already downloaded.
 > Using model: xtts
✅ GPU로 모델 이동 완료: cuda
✅ Coqui TTS 모델 초기화 성공: tts_models/multilingual/multi-dataset/xtts_v2
✅ TTS 엔진 초기화 성공: coqui
✅ Coqui TTS 초기화 성공!
🎤 TTS 서버 시작 - Kafka Consumer 초기화 중...
✅ TTS Kafka Consumer 스레드 시작됨
🚀 [TTS Kafka Consumer] 초기화
📡 Kafka 서버: ['kafka:9092']
📢 구독 토픽: TTSREQUEST
🔗 Channel Layer: ✅ 사용 가능
🔄 [Kafka Consumer] 시작 중...
📡 연결 대상: ['kafka:9092']
📢 토픽: TTSREQUEST
✅ [Kafka Consumer] 시작 완료
📊 Consumer 설정:
  - Group ID: tts-consumer-group
  - Auto Offset Reset: latest
  - Consumer Timeout: 1초
🔄 메시지 수신 대기 중...

================================================================================
📨 [LLM → TTS] 새 메시지 수신!
⏰ 수신 시간: 2025-07-25 14:24:59.337
📍 파티션: 7, 오프셋: 0
📏 메시지 크기: 382 chars
================================================================================
🔍 [메시지 구조 분석]
📋 원본 메시지 키들: ['id', 'timestamp', 'service', 'data']
📦 [LLM_server 메시지 감지] 'data' 필드에서 실제 메시지 추출
🆔 외부 메시지 ID: 76d60949-db76-405b-98d1-17fe5d360f3d
⏰ 외부 타임스탬프: 2025-07-25T14:24:59.324636
🏷️ 서비스: LLM_server
📋 내부 메시지 키들: ['text', 'source', 'phoneId', 'sessionId', 'requestId', 'timestamp', 'request_type']
📝 텍스트: '알겠습니다! 다른 질문이나 궁금한 점이 있으시면 언제든지 말씀해 주세요. 도와드리겠습니다!' (길이: 50 문자)
🎙️ 음성 설정: {}
🆔 요청 ID: unknown
⏱️ LLM 생성 시간: 2025-07-25 14:24:58
🕐 처리 지연 시간: 1.27초

🎤 [TTS 처리 시작] 요청 ID: unknown
🎯 [TTS 처리] 메시지 처리 시작
📝 [TTS 처리] 입력 텍스트: '알겠습니다! 다른 질문이나 궁금한 점이 있으시면 언제든지 말씀해 주세요. 도와드리겠습니다!'
🎙️ [TTS 처리] 음성 설정: {}
🆔 [TTS 처리] 요청 ID: kafka_1753453499
🎤 [TTS 처리] 실제 음성 변환 시작
text: 알겠습니다! 다른 질문이나 궁금한 점이 있으시면 언제든지 말씀해 주세요. 도와드리겠습니다!
[coqui 음성 변환 실행!]
 > Text splitted to sentences.
['알겠습니다!', '다른 질문이나 궁금한 점이 있으시면 언제든지 말씀해 주세요.', '도와드리겠습니다!']
 > Processing time: 8.896602392196655
 > Real-time factor: 0.4266199301209512
🎤 [TTS 처리] 파일이름  kafka_tts_ko_1753453499.mp3
⏱️ [TTS 처리] 음성 생성 시간: 8.96초
✅ [TTS 파일] MP3 파일 생성 완료: kafka_tts_ko_1753453499.mp3
❌ [TTS 처리] 음성 변환 실패: Decoding failed. ffmpeg returned error code: 1

Output from ffmpeg/avlib:

ffmpeg version 5.1.6-0+deb12u1 Copyright (c) 2000-2024 the FFmpeg developers
  built with gcc 12 (Debian 12.2.0-14)
  configuration: --prefix=/usr --extra-version=0+deb12u1 --toolchain=hardened --libdir=/usr/lib/x86_64-linux-gnu --incdir=/usr/include/x86_64-linux-gnu --arch=amd64 --enable-gpl --disable-stripping --enable-gnutls --enable-ladspa --enable-libaom --enable-libass --enable-libbluray --enable-libbs2b --enable-libcaca --enable-libcdio --enable-libcodec2 --enable-libdav1d --enable-libflite --enable-libfontconfig --enable-libfreetype --enable-libfribidi --enable-libglslang --enable-libgme --enable-libgsm --enable-libjack --enable-libmp3lame --enable-libmysofa --enable-libopenjpeg --enable-libopenmpt --enable-libopus --enable-libpulse --enable-librabbitmq --enable-librist --enable-librubberband --enable-libshine --enable-libsnappy --enable-libsoxr --enable-libspeex --enable-libsrt --enable-libssh --enable-libsvtav1 --enable-libtheora --enable-libtwolame --enable-libvidstab --enable-libvorbis --enable-libvpx --enable-libwebp --enable-libx265 --enable-libxml2 --enable-libxvid --enable-libzimg --enable-libzmq --enable-libzvbi --enable-lv2 --enable-omx --enable-openal --enable-opencl --enable-opengl --enable-sdl2 --disable-sndio --enable-libjxl --enable-pocketsphinx --enable-librsvg --enable-libmfx --enable-libdc1394 --enable-libdrm --enable-libiec61883 --enable-chromaprint --enable-frei0r --enable-libx264 --enable-libplacebo --enable-librav1e --enable-shared
  libavutil      57. 28.100 / 57. 28.100
  libavcodec     59. 37.100 / 59. 37.100
  libavformat    59. 27.100 / 59. 27.100
  libavdevice    59.  7.100 / 59.  7.100
  libavfilter     8. 44.100 /  8. 44.100
  libswscale      6.  7.100 /  6.  7.100
  libswresample   4.  7.100 /  4.  7.100
  libpostproc    56.  6.100 / 56.  6.100
[mp3float @ 0x5f079db50b80] Header missing
    Last message repeated 335 times
[mp3 @ 0x5f079db47840] Could not find codec parameters for stream 0 (Audio: mp3 (mp3float), 0 channels, fltp): unspecified frame size
Consider increasing the value for the 'analyzeduration' (0) and 'probesize' (5000000) options
Input #0, mp3, from 'kafka_tts_ko_1753453499.mp3':
  Duration: N/A, start: 0.000000, bitrate: N/A
  Stream #0:0: Audio: mp3, 0 channels, fltp
Stream mapping:
  Stream #0:0 -> #0:0 (mp3 (mp3float) -> pcm_s16le (native))
Press [q] to stop, [?] for help
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5f079db80c40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[abuffer @ 0x5f079db5d000] Value inf for parameter 'time_base' out of range [0 - 2.14748e+09]
    Last message repeated 1 times
[abuffer @ 0x5f079db5d000] Error setting option time_base to value 1/0.
[graph_0_in_0_0 @ 0x5f079db5ccc0] Error applying options to the filter.
Error reinitializing filters!
Error while filtering: Numerical result out of range
Finishing stream 0:0 without any data written to it.
[abuffer @ 0x5f079db5d000] Value inf for parameter 'time_base' out of range [0 - 2.14748e+09]
    Last message repeated 1 times
[abuffer @ 0x5f079db5d000] Error setting option time_base to value 1/0.
[graph_0_in_0_0 @ 0x5f079dbb6d00] Error applying options to the filter.
Error configuring filter graph
Conversion failed!

✅ [LLM → TTS] 메시지 처리 완료
================================================================================


================================================================================
📨 [LLM → TTS] 새 메시지 수신!
⏰ 수신 시간: 2025-07-25 14:31:30.618
📍 파티션: 6, 오프셋: 0
📏 메시지 크기: 397 chars
================================================================================
🔍 [메시지 구조 분석]
📋 원본 메시지 키들: ['id', 'timestamp', 'service', 'data']
📦 [LLM_server 메시지 감지] 'data' 필드에서 실제 메시지 추출
🆔 외부 메시지 ID: f3ca8c05-b4e3-4f12-8c32-e266c922deee
⏰ 외부 타임스탬프: 2025-07-25T14:31:30.605533
🏷️ 서비스: LLM_server
📋 내부 메시지 키들: ['text', 'source', 'phoneId', 'sessionId', 'requestId', 'timestamp', 'request_type']
📝 텍스트: '알겠습니다! 다른 궁금한 점이나 도움이 필요하신 부분이 있다면 언제든지 말씀해 주세요. 최선을 다해 도와드리겠습니다!' (길이: 65 문자)
🎙️ 음성 설정: {}
🆔 요청 ID: unknown
⏱️ LLM 생성 시간: 2025-07-25 14:31:28
🕐 처리 지연 시간: 2.11초

🎤 [TTS 처리 시작] 요청 ID: unknown
🎯 [TTS 처리] 메시지 처리 시작
📝 [TTS 처리] 입력 텍스트: '알겠습니다! 다른 궁금한 점이나 도움이 필요하신 부분이 있다면 언제든지 말씀해 주세요. 최선을 다해 도와드리겠습니다!'
🎙️ [TTS 처리] 음성 설정: {}
🆔 [TTS 처리] 요청 ID: kafka_1753453890
🎤 [TTS 처리] 실제 음성 변환 시작
text: 알겠습니다! 다른 궁금한 점이나 도움이 필요하신 부분이 있다면 언제든지 말씀해 주세요. 최선을 다해 도와드리겠습니다!
[coqui 음성 변환 실행!]
 > Text splitted to sentences.
['알겠습니다!', '다른 궁금한 점이나 도움이 필요하신 부분이 있다면 언제든지 말씀해 주세요.', '최선을 다해 도와드리겠습니다!']
 > Processing time: 7.675183534622192
 > Real-time factor: 0.36359569312334433
🎤 [TTS 처리] 파일이름  kafka_tts_ko_1753453890.mp3
⏱️ [TTS 처리] 음성 생성 시간: 7.73초
✅ [TTS 파일] MP3 파일 생성 완료: kafka_tts_ko_1753453890.mp3
❌ [TTS 처리] 음성 변환 실패: Decoding failed. ffmpeg returned error code: 1

Output from ffmpeg/avlib:

ffmpeg version 5.1.6-0+deb12u1 Copyright (c) 2000-2024 the FFmpeg developers
  built with gcc 12 (Debian 12.2.0-14)
  configuration: --prefix=/usr --extra-version=0+deb12u1 --toolchain=hardened --libdir=/usr/lib/x86_64-linux-gnu --incdir=/usr/include/x86_64-linux-gnu --arch=amd64 --enable-gpl --disable-stripping --enable-gnutls --enable-ladspa --enable-libaom --enable-libass --enable-libbluray --enable-libbs2b --enable-libcaca --enable-libcdio --enable-libcodec2 --enable-libdav1d --enable-libflite --enable-libfontconfig --enable-libfreetype --enable-libfribidi --enable-libglslang --enable-libgme --enable-libgsm --enable-libjack --enable-libmp3lame --enable-libmysofa --enable-libopenjpeg --enable-libopenmpt --enable-libopus --enable-libpulse --enable-librabbitmq --enable-librist --enable-librubberband --enable-libshine --enable-libsnappy --enable-libsoxr --enable-libspeex --enable-libsrt --enable-libssh --enable-libsvtav1 --enable-libtheora --enable-libtwolame --enable-libvidstab --enable-libvorbis --enable-libvpx --enable-libwebp --enable-libx265 --enable-libxml2 --enable-libxvid --enable-libzimg --enable-libzmq --enable-libzvbi --enable-lv2 --enable-omx --enable-openal --enable-opencl --enable-opengl --enable-sdl2 --disable-sndio --enable-libjxl --enable-pocketsphinx --enable-librsvg --enable-libmfx --enable-libdc1394 --enable-libdrm --enable-libiec61883 --enable-chromaprint --enable-frei0r --enable-libx264 --enable-libplacebo --enable-librav1e --enable-shared
  libavutil      57. 28.100 / 57. 28.100
  libavcodec     59. 37.100 / 59. 37.100
  libavformat    59. 27.100 / 59. 27.100
  libavdevice    59.  7.100 / 59.  7.100
  libavfilter     8. 44.100 /  8. 44.100
  libswscale      6.  7.100 /  6.  7.100
  libswresample   4.  7.100 /  4.  7.100
  libpostproc    56.  6.100 / 56.  6.100
[mp3float @ 0x5fd0195c9b80] Header missing
    Last message repeated 351 times
[mp3 @ 0x5fd0195c0840] Could not find codec parameters for stream 0 (Audio: mp3 (mp3float), 0 channels, fltp): unspecified frame size
Consider increasing the value for the 'analyzeduration' (0) and 'probesize' (5000000) options
Input #0, mp3, from 'kafka_tts_ko_1753453890.mp3':
  Duration: N/A, start: 0.000000, bitrate: N/A
  Stream #0:0: Audio: mp3, 0 channels, fltp
Stream mapping:
  Stream #0:0 -> #0:0 (mp3 (mp3float) -> pcm_s16le (native))
Press [q] to stop, [?] for help
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: Invalid data found when processing input
[mp3float @ 0x5fd0196ddc40] Header missing
Error while decoding stream #0:0: I