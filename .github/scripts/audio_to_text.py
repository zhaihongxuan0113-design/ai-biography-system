# -*- coding: utf-8 -*-
"""audio-to-text：CrisperWhisper 2.0 逐字转写 -> 带时间戳 Markdown（保留口语特征）。

规则来源：docs/语气保留指南.md 第一步。本脚本不做任何润色与删改。
依赖：pip install "crisperwhisper[transformers]"（PyPI 包名为 crisperwhisper，无连字符）。
"""
import json
import re
import time
from pathlib import Path

from crisperwhisper import CrisperWhisperModel

# CrisperWhisper 2.0 上游问题规避：长音频的延续上下文（上一段最后 12 个词）可能
# 因幻觉循环变得极长，导致 HF Whisper 报「decoder_input_ids + max_new_tokens > 448」。
# 这里把续写上下文截断到最多 60 个字符（仍保留语气与话题连续性），从根上避免超限。
MAX_CONTEXT_CHARS = 60
try:
    from crisperwhisper.prompt import PromptBuilder
    _orig_build = PromptBuilder._build

    def _build_capped(self, mode, hotwords=None, context=None):
        if context:
            context = ' '.join(str(context).split())
            if len(context) > MAX_CONTEXT_CHARS:
                cut = context[:MAX_CONTEXT_CHARS].rsplit(' ', 1)[0].strip()
                context = cut or context[:MAX_CONTEXT_CHARS]
        return _orig_build(self, mode, hotwords=hotwords, context=context)

    PromptBuilder._build = _build_capped
except Exception:
    pass

FIX = Path('tests/fixtures')
OUT = Path('tests/transcripts')
OUT.mkdir(parents=True, exist_ok=True)
METRICS = Path('tests/metrics.json')

MODEL_SIZE = 'small'
LANGUAGE = 'zh'
PAUSE_SEC = 1.2
WORDS_PER_LINE = 12

# verbatim 模式的英文情绪标签统一换算成中文标注（《语气保留指南》约定）
TAG_MAP = {
    '[laughter]': '[笑]',
    '[laugh]': '[笑]',
    '[laughs]': '[笑]',
    '[sigh]': '[叹气]',
    '[cough]': '[咳嗽]',
    '[applause]': '[掌声]',
    '[music]': '[音乐]',
    '[noise]': '[杂音]',
    '[gasp]': '[喘气]',
}

# verbatim 模式的英文填充词标签换成中文语气词（保留口语感）
FILLER_MAP = {
    '[um]': '嗯，',
    '[uh]': '啊，',
    '[erm]': '呃，',
    '[hm]': '嗯，',
}


def clean_tags(text):
    """清洗 verbatim 输出：
    1. 白名单情绪标签换算成中文（[笑] [叹气] 等）；
    2. [UM]/[UH] 等填充词换算成中文语气词；
    3. 其余非言语事件标签（[crying] [scream] [sneeze] 等，多为小模型误报）直接剔除；
    4. 连续重复的同一标签/语气词合并为一次。"""
    def repl(m):
        low = m.group(0).lower()
        if low in TAG_MAP:
            return ' %s ' % TAG_MAP[low]
        return FILLER_MAP.get(low, '')
    text = re.sub(r'\[[A-Za-z]+\]', repl, text)
    text = re.sub(r'(\[[^\]]{1,4}\])\s*\1+', r'\1', text)
    text = re.sub(r'(嗯，|啊，|呃，)\1+', r'\1', text)
    text = re.sub(r'\s{2,}', ' ', text)
    return text.strip()


def load_metrics():
    if METRICS.exists():
        try:
            return json.loads(METRICS.read_text(encoding='utf-8'))
        except Exception:
            pass
    return {}


def save_metrics(m):
    METRICS.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding='utf-8')


def parse_week_q(stem):
    m = re.match(r'第(\d+)周_问题(\d+)', stem)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.match(r'录音0*(\d+)', stem)
    if m:
        n = int(m.group(1))
        return (n + 1) // 2, n
    return 0, 0


def fmt_ts(sec):
    return '%02d:%02d' % (int(sec // 60), int(sec % 60))


def norm_token(token):
    token = token.strip()
    if not token:
        return ''
    low = token.lower()
    return TAG_MAP.get(low, token)


def is_cjk(ch):
    return ('\u3400' <= ch <= '\u4dbf'
            or '\u4e00' <= ch <= '\u9fff'
            or '\uf900' <= ch <= '\ufaff')


def text_with_pauses(text, words):
    """以 result.text 为正文（整段解码，无乱码），用逐词时间戳标注每行开头并插入停顿「……」。

    CrisperWhisper 的逐词文本（result.words）按词切分解码会把部分中文字符切成半个字节，
    产生 U+FFFD 乱码；但其时间戳是可靠的。因此：正文取 result.text，词表只用来取时间与停顿。
    """
    text = clean_tags(text)
    if not text:
        return []
    tokens = text.split()
    word_times = []
    for w in words or []:
        wt = clean_tags(norm_token(getattr(w, 'word', '')))
        if not wt:
            continue
        word_times.append((wt, float(w.start), float(w.end)))
    # 游标匹配：给每个 token 找对应词的起止时间；乱码词匹配不上时继承上一个 token 的时间
    times = []
    wi = 0
    prev = (0.0, 0.0)
    for tok in tokens:
        found = None
        while wi < len(word_times):
            wt, s, e = word_times[wi]
            if wt == tok:
                found = (s, e)
                wi += 1
                break
            wi += 1
        if found is None:
            found = prev
        else:
            prev = found
        times.append(found)
    lines = []
    buf = []
    line_start = None
    last_end = None
    for tok, (s, e) in zip(tokens, times):
        if line_start is None:
            line_start = s
        if last_end is not None and s - last_end > PAUSE_SEC:
            lines.append(('[%s]' % fmt_ts(line_start), ' '.join(buf) + '……'))
            buf = []
            line_start = s
        buf.append(tok)
        if sum(len(t) for t in buf) + len(buf) >= WORDS_PER_LINE * 6:
            lines.append(('[%s]' % fmt_ts(line_start), ' '.join(buf)))
            buf = []
            line_start = None
        last_end = e
    if buf:
        lines.append(('[%s]' % fmt_ts(line_start if line_start is not None else 0.0), ' '.join(buf)))
    return lines


def main():
    files = []
    for ext in ('*.wav', '*.mp3', '*.m4a'):
        files.extend(FIX.glob(ext))
    files = sorted(set(files), key=lambda p: p.name)
    if not files:
        print('无新录音需要转写。')
        return
    metrics = load_metrics()
    metrics.setdefault('audio_to_text', [])
    print('加载 CrisperWhisper 2.0 模型（%s · 语言 %s · CPU · 逐字模式）...' % (MODEL_SIZE, LANGUAGE))
    model = CrisperWhisperModel(
        MODEL_SIZE,
        backend='transformers',
        device='cpu',
        compute_type='float32',
    )
    done_any = False
    for f in files:
        week, q = parse_week_q(f.stem)
        if not week:
            print('跳过（无法解析周次/问题号）:', f.name)
            continue
        target = OUT / ('第%d周_问题%d_测试长者001_转写.md' % (week, q))
        if target.exists():
            print('已存在，跳过:', target.name)
            continue
        t0 = time.time()
        print('转写中:', f.name)
        result = model.transcribe(
            str(f),
            language=LANGUAGE,
            mode='verbatim',
            word_timestamps=True,
        )
        words = getattr(result, 'words', None) or []
        raw_text = (getattr(result, 'text', '') or '').strip()
        lines = text_with_pauses(raw_text, words)
        if not lines and raw_text:
            lines = [('[00:00]', clean_tags(raw_text))]
        if not lines:
            lines = [('[00:00]', '（未识别出语音内容，请重录或换更清晰的录音）')]
        audio_sec = round(float(getattr(result, 'duration', 0.0)), 1)
        proc_sec = round(float(getattr(result, 'processing_time', 0.0)), 1)
        wall_sec = round(time.time() - t0, 1)
        word_count = len(words) or len((getattr(result, 'text', '') or '').split())
        header = [
            '# 第%d周 问题%d · 测试长者001 · 转写稿' % (week, q),
            '',
            '> 来源录音：`tests/fixtures/%s`' % f.name,
            '> 转写方式：CrisperWhisper 2.0（模型 %s，语言 %s，verbatim 逐字模式，CPU）' % (MODEL_SIZE, LANGUAGE),
            '> 转写规则：逐字保留口头禅、语气词、重复、说一半的话；不修正语法、不润色、不删除跑题内容。',
            '> 停顿用「……」标注；情绪用 [笑] [叹气] 等方括号标注；方言词原样保留。',
            '',
        ]
        body = '\n\n'.join('%s %s' % (ts, text) for ts, text in lines)
        footer = [
            '',
            '---',
            '',
            '转写信息：音频时长 %s 秒 ｜ 模型处理耗时 %s 秒 ｜ 脚本总耗时 %s 秒 ｜ 词数 %d。' % (
                audio_sec, proc_sec, wall_sec, word_count),
            '',
        ]
        target.write_text(
            '\n'.join(header) + body + '\n'.join(footer),
            encoding='utf-8',
        )
        metrics['audio_to_text'].append({
            'audio': f.name,
            'transcript': target.name,
            'audio_duration_sec': audio_sec,
            'model_processing_sec': proc_sec,
            'duration_sec': wall_sec,
            'word_count': word_count,
            'transcript_bytes': target.stat().st_size,
        })
        save_metrics(metrics)
        print('完成:', target.name, '| 模型耗时', proc_sec, '秒 | 总耗时', wall_sec, '秒 | 词数', word_count)
        done_any = True
    if not done_any:
        print('无新录音需要转写。')


if __name__ == '__main__':
    main()
