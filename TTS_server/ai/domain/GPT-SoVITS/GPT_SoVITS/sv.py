import sys
import os
import torch
from pathlib import Path

# sys.path.append(f"{os.getcwd()}/GPT_SoVITS/eres2net")
# sv_path = "GPT_SoVITS/pretrained_models/sv/pretrained_eres2netv2w24s4ep4.ckpt"
BASE = Path(__file__).resolve().parent                 # .../GPT_SoVITS
ERES2NET_DIR = BASE / "eres2net"
if str(ERES2NET_DIR) not in sys.path:
    sys.path.insert(0, str(ERES2NET_DIR))              # 로컬 kaldi.py 우선

# ckpt 경로를 파일 기준으로
sv_path = str((BASE / "pretrained_models" / "sv" / "pretrained_eres2netv2w24s4ep4.ckpt"))
print(f"[SV] ckpt={sv_path} exists={Path(sv_path).exists()}")  # 디버그용


from ERes2NetV2 import ERes2NetV2
import kaldi as Kaldi


class SV:
    def __init__(self, device, is_half):
        pretrained_state = torch.load(sv_path, map_location="cpu", weights_only=False)
        embedding_model = ERes2NetV2(baseWidth=24, scale=4, expansion=4)
        embedding_model.load_state_dict(pretrained_state)
        embedding_model.eval()
        self.embedding_model = embedding_model
        if is_half == False:
            self.embedding_model = self.embedding_model.to(device)
        else:
            self.embedding_model = self.embedding_model.half().to(device)
        self.is_half = is_half

    def compute_embedding3(self, wav):
        with torch.no_grad():
            if self.is_half == True:
                wav = wav.half()
            feat = torch.stack(
                [Kaldi.fbank(wav0.unsqueeze(0), num_mel_bins=80, sample_frequency=16000, dither=0) for wav0 in wav]
            )
            sv_emb = self.embedding_model.forward3(feat)
        return sv_emb
