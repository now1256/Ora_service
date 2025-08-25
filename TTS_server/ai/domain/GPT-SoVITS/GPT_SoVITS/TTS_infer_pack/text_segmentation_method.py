import re
from typing import Callable

punctuation = set(["!", "?", "…", ",", ".", "-", " "])
METHODS = dict()


def get_method(name: str) -> Callable:
    method = METHODS.get(name, None)
    if method is None:
        raise ValueError(f"Method {name} not found")
    return method


def get_method_names() -> list:
    return list(METHODS.keys())


def register_method(name):
    def decorator(func):
        METHODS[name] = func
        return func

    return decorator


splits = {
    "，",
    "。",
    "？",
    "！",
    ",",
    ".",
    "?",
    "!",
    "~",
    ":",
    "：",
    "—",
    "…",
}


def split_big_text(text, max_len=510):
    # 定义全角和半角标点符号
    punctuation = "".join(splits)

    # 切割文本
    segments = re.split("([" + punctuation + "])", text)

    # 初始化结果列表和当前片段
    result = []
    current_segment = ""

    for segment in segments:
        # 如果当前片段加上新的片段长度超过max_len，就将当前片段加入结果列表，并重置当前片段
        if len(current_segment + segment) > max_len:
            result.append(current_segment)
            current_segment = segment
        else:
            current_segment += segment

    # 将最后一个片段加入结果列表
    if current_segment:
        result.append(current_segment)

    return result


def split(todo_text):
    todo_text = todo_text.replace("……", "。").replace("——", "，")
    if todo_text[-1] not in splits:
        todo_text += "。"
    i_split_head = i_split_tail = 0
    len_text = len(todo_text)
    todo_texts = []
    while 1:
        if i_split_head >= len_text:
            break  # 结尾一定有标点，所以直接跳出即可，最后一段在上次已加入
        if todo_text[i_split_head] in splits:
            i_split_head += 1
            todo_texts.append(todo_text[i_split_tail:i_split_head])
            i_split_tail = i_split_head
        else:
            i_split_head += 1
    return todo_texts


# 不切
@register_method("cut0")
def cut0(inp):
    if not set(inp).issubset(punctuation):
        return inp
    else:
        return "/n"


# 凑四句一切
@register_method("cut1")
def cut1(inp):
    inp = inp.strip("\n")
    inps = split(inp)
    split_idx = list(range(0, len(inps), 4))
    split_idx[-1] = None
    if len(split_idx) > 1:
        opts = []
        for idx in range(len(split_idx) - 1):
            opts.append("".join(inps[split_idx[idx] : split_idx[idx + 1]]))
    else:
        opts = [inp]
    opts = [item for item in opts if not set(item).issubset(punctuation)]
    return "\n".join(opts)


# # 凑50字一切
# @register_method("cut2")
# def cut2(inp):
#     inp = inp.strip("\n")
#     inps = split(inp)
#     if len(inps) < 2:
#         return inp
#     opts = []
#     summ = 0
#     tmp_str = ""
#     for i in range(len(inps)):
#         summ += len(inps[i])
#         tmp_str += inps[i]
#         if summ > 15:
#             summ = 0
#             opts.append(tmp_str)
#             tmp_str = ""
#     if tmp_str != "":
#         opts.append(tmp_str)
#     # print(opts)
#     if len(opts) > 1 and len(opts[-1]) < 15:  ##如果最后一个太短了，和前一个合一起
#         opts[-2] = opts[-2] + opts[-1]
#         opts = opts[:-1]
#     opts = [item for item in opts if not set(item).issubset(punctuation)]
#     return "\n".join(opts)

@register_method("cut2")
def cut2(inp, chunk_chars: int = 15, min_tail: int = 15):
    s = inp.strip("\n")

    # 1) 먼저 내부 split으로 시도 (문장부호 기반)
    parts = split(s)

    # 2) 한국어 등에서 1조각만 나오면 문자 단위 폴백
    if len(parts) < 2:
        parts = list(s)  # 한 글자씩

    # 3) 글자 수 기준으로 누적하여 청크 만들기
    opts = []
    buf = []
    cnt = 0
    for p in parts:
        cnt += len(p)
        buf.append(p)
        if cnt >= chunk_chars:
            opts.append("".join(buf))
            buf = []
            cnt = 0
    if buf:
        opts.append("".join(buf))

    # 4) 마지막 조각이 너무 짧으면 앞 조각에 합치기
    if len(opts) > 1 and len(opts[-1]) < min_tail:
        opts[-2] = opts[-2] + opts[-1]
        opts.pop()

    # 5) 완전 문장부호만 남은 라인은 제거
    from TTS_infer_pack.text_segmentation_method import punctuation, splits as SPLITS
    opts = [x for x in opts if not set(x).issubset(punctuation)]

    # 6) 파이프라인 호환을 위해 각 청크 끝에 "분할 표지" 삽입
    # - 어떤 브랜치에선 '\n'로 나눔
    # - 어떤 브랜치에선 split()을 다시 돌리므로, SPLITS 안의 구두점을 끝에 붙여줌
    delimiter = "。" if "。" in SPLITS else ("." if "." in SPLITS else list(SPLITS)[0])
    opts = [x if len(x) > 0 and x[-1] in SPLITS else (x + delimiter) for x in opts]

    print(f"[cut2] chunk_chars=15, len(parts)={len(parts)} -> will chunk")

    # '\n' 조합 + 문장부호 둘 다 포함시켜 반환
    return "\n".join(opts)


# 按中文句号。切
@register_method("cut3")
def cut3(inp):
    inp = inp.strip("\n")
    opts = ["%s" % item for item in inp.strip("。").split("。")]
    opts = [item for item in opts if not set(item).issubset(punctuation)]
    return "\n".join(opts)


# 按英文句号.切
@register_method("cut4")
def cut4(inp):
    inp = inp.strip("\n")
    opts = re.split(r"(?<!\d)\.(?!\d)", inp.strip("."))
    opts = [item for item in opts if not set(item).issubset(punctuation)]
    return "\n".join(opts)


# 按标点符号切
# contributed by https://github.com/AI-Hobbyist/GPT-SoVITS/blob/main/GPT_SoVITS/inference_webui.py
@register_method("cut5")
def cut5(inp):
    inp = inp.strip("\n")
    punds = {",", ".", ";", "?", "!", "、", "，", "。", "？", "！", ";", "：", "…"}
    mergeitems = []
    items = []

    for i, char in enumerate(inp):
        if char in punds:
            if char == "." and i > 0 and i < len(inp) - 1 and inp[i - 1].isdigit() and inp[i + 1].isdigit():
                items.append(char)
            else:
                items.append(char)
                mergeitems.append("".join(items))
                items = []
        else:
            items.append(char)

    if items:
        mergeitems.append("".join(items))

    opt = [item for item in mergeitems if not set(item).issubset(punds)]
    return "\n".join(opt)

@register_method("cut15")
def cut15(
    inp: str,
    first_len: int = 5,   # 첫 조각 글자수
    max_len: int = 60,     # 이후 최대 글자수
    min_tail: int = 5,     # 마지막 조각이 너무 짧으면(이 값 미만) 앞에 합침
    count_spaces: bool = True,  # True면 공백도 글자수에 포함
):
    s = inp.replace("\r\n", "\n").strip("\n")
    if not s:
        return s

    # 1) 글자수(문자 단위)로 누적하여 조각 만들기
    chunks = []
    limit = first_len
    count = 0
    buf = []

    for ch in s:
        buf.append(ch)
        if count_spaces or not ch.isspace():
            count += 1
        if count >= limit:
            chunks.append("".join(buf))
            buf.clear()
            count = 0
            limit = max_len  # 두 번째 조각부터는 30자 기준

    if buf:
        chunks.append("".join(buf))

    # 2) 마지막 조각이 너무 짧으면 앞 조각에 합치기
    if len(chunks) > 1 and len(chunks[-1].strip()) < min_tail:
        chunks[-2] += chunks[-1]
        chunks.pop()

    # 3) 문장부호만 남은 조각 제거 + 후단 파이프라인 호환용 구두점 보강
    from TTS_infer_pack.text_segmentation_method import punctuation, splits as SPLITS
    chunks = [c for c in chunks if not set(c).issubset(punctuation)]
    delimiter = "。" if "。" in SPLITS else ("." if "." in SPLITS else list(SPLITS)[0])
    chunks = [c if (c and c[-1] in SPLITS) else (c + delimiter) for c in chunks]

    print(f"[cut15_30_chars] first_len={first_len}, max_len={max_len}, "
          f"count_spaces={count_spaces}, chunks={len(chunks)}")

    # 여러 조각은 개행으로 합쳐 반환 (브랜치에 따라 '\n' 또는 splits 기준 재분할됨)
    return "\n".join(chunks)

if __name__ == "__main__":
    method = get_method("cut5")
    print(method("你好，我是小明。你好，我是小红。你好，我是小刚。你好，我是小张。"))
