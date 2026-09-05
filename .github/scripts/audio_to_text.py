# -*- coding: utf-8 -*-
"""audio-to-text：CrisperWhisper 2.0 逐字转写 -> 带时间戳 Markdown（保留口语特征）。

规则来源：docs/语气保留指南.md 第一步。本脚本不做任何润色与删改。
依赖：pip install "crisperwhisper[transformers]"（PyPI 包名为 crisperwhisper，无连字符）。

v3 说明：
- 长音频保留 continuation 策略（跨段上下文延续，避免丢句）+ 默认幻觉修复（防重复循环）；
- Whisper small 对生僻字会按 UTF-8 字节级 token 解码，偶发字节序列不完整产生 U+FFFD，
  清洗时统一替换为「□」并在文末标注数量（诚实保留原位置，供人工复核）；
- 正文直接取各 chunk 的干净文本；行时间戳与「……」停顿来自逐词时间戳（词文本可能有乱码，
  只用于取时间，不影响正文）；
- [UH]/[UM] 等填充词标签换算成「啊，/嗯，」后，合并连续重复（含空格分隔的重复）。
"""
import json
import re
import time
from pathlib import Path

from crisperwhisper import CrisperWhisperModel

FIX = Path('tests/fixtures')
OUT = Path('tests/transcripts')
OUT.mkdir(parents=True, exist_ok=True)
METRICS = Path('tests/metrics.json')

MODEL_SIZE = 'small'
LANGUAGE = 'zh'
PAUSE_SEC = 1.2
MAX_LINE_CHARS = 60

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
    4. 连续重复的同一标签/语气词合并为一次（含空格分隔的重复）。"""
    def repl(m):
        low = m.group(0).lower()
        if low in TAG_MAP:
            return ' %s ' % TAG_MAP[low]
        return FILLER_MAP.get(low, '')

    text = re.sub(r'\[[A-Za-z]+\]', repl, text)
    text = text.replace('\ufffd', '□')
    text = re.sub(r'(\[[^\]]{1,4}\])(?:\s*\1)+', r'\1', text)
    text = re.sub(r'((?:嗯|啊|呃)，)(?:\s*\1)+', r'\1', text)
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


def split_long_line(line_text):
    """把过长的行按标点切成多行，尽量在逗号/句号/省略号后断。"""
    if len(line_text) <= MAX_LINE_CHARS:
        return [line_text]
    pieces = []
    rest = line_text
    while len(rest) > MAX_LINE_CHARS:
        cut = -1
        for marker in ('……', '。', '！', '？', '，', ' '):
            pos = rest.rfind(marker, MAX_LINE_CHARS // 2, MAX_LINE_CHARS)
            if pos > cut:
                cut = pos + len(marker)
        if cut <= 0:
            cut = MAX_LINE_CHARS
        pieces.append(rest[:cut].strip())
        rest = rest[cut:].strip()
    if rest:
        pieces.append(rest)
    return pieces


def build_lines(chunks, words):
    """正文取各 chunk 干净文本；每个词组用逐词时间按顺序比例映射；
    相邻词组间隔 > PAUSE_SEC 时行尾补「……」。返回 [(ts, text)] 与 FFFD 计数。"""
    chunk_list = []
    for c in chunks or []:
        raw = getattr(c, 'text', '') or ''
        fffd_chunk = raw.count('\ufffd')
        text = clean_tags(raw)
        if not text:
            continue
        s = float(getattr(c, 'start_sec', 0.0) or 0.0)
        e = float(getattr(c, 'end_sec', 0.0) or 0.0)
        chunk_list.append({'start': s, 'end': e, 'text': text, 'fffd': fffd_chunk})
    chunk_list.sort(key=lambda c: c['start'])
    if not chunk_list:
        return [], 0

    fffd = 0
    lines = []
    last_word_end = None
    for ci, c in enumerate(chunk_list):
        groups = c['text'].split()
        fffd += c['fffd']
        wtimes = []
        for w in words or []:
            t = float(getattr(w, 'start', -1.0) or -1.0)
            e = float(getattr(w, 'end', t) or t)
            if c['start'] <= t < c['end']:
                wtimes.append((t, e))
            elif ci == len(chunk_list) - 1 and t >= c['start']:
                wtimes.append((t, e))
        if not wtimes:
            wtimes = [(c['start'], c['end'])]
        n_g, n_w = len(groups), len(wtimes)
        group_times = []
        for i in range(n_g):
            idx = int(round(i * (n_w - 1) / max(n_g - 1, 1))) if n_g > 1 else 0
            idx = max(0, min(n_w - 1, idx))
            group_times.append(wtimes[idx])
        # 组句：先按停顿切，再按长度切
        segs = []          # [(start_time, text)]
        cur = []
        cur_start = None
        for g, (s, e) in zip(groups, group_times):
            if last_word_end is not None and s - last_word_end > PAUSE_SEC:
                if cur:
                    segs.append((cur_start if cur_start is not None else s, ' '.join(cur) + '……'))
                    cur = []
                    cur_start = None
                else:
                    segs.append((s, '……'))
            if cur_start is None:
                cur_start = s
            cur.append(g)
            last_word_end = e
        if cur:
            segs.append((cur_start if cur_start is not None else c['start'], ' '.join(cur)))
        for s, text in segs:
            pieces = split_long_line(text)
            for pi, piece in enumerate(pieces):
                ts = '[%s]' % fmt_ts(s) if pi == 0 else '      '
                lines.append((ts, piece))
    return lines, fffd


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
    print('加载 CrisperWhisper 2.0 模型（%s · 语言 %s · CPU · verbatim 逐字 · continuation 分段）...' % (MODEL_SIZE, LANGUAGE))
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
        chunks = getattr(result, 'chunks', None) or []
        raw_text = (getattr(result, 'text', '') or '').strip()
        lines, fffd = build_lines(chunks, words)
        if not lines:
            if raw_text:
                lines = [('[00:00]', clean_tags(raw_text))]
            else:
                lines = [('[00:00]', '（未识别出语音内容，请重录或换更清晰的录音）')]
        audio_sec = round(float(getattr(result, 'duration', 0.0)), 1)
        proc_sec = round(float(getattr(result, 'processing_time', 0.0)), 1)
        wall_sec = round(time.time() - t0, 1)
        word_count = len(words) or len(raw_text.split())
        header = [
            '# 第%d周 问题%d · 测试长者001 · 转写稿' % (week, q),
            '',
            '> 来源录音：`tests/fixtures/%s`' % f.name,
            '> 转写方式：CrisperWhisper 2.0（模型 %s，语言 %s，verbatim 逐字模式，continuation 分段，CPU）' % (MODEL_SIZE, LANGUAGE),
            '> 转写规则：逐字保留口头禅、语气词、重复、说一半的话；不修正语法、不润色、不删除跑题内容。',
            '> 停顿用「……」标注；情绪用 [笑] [叹气] 等方括号标注；方言词原样保留。',
            '',
        ]
        body = '\n\n'.join('%s %s' % (ts, text) for ts, text in lines)
        footer = [
            '',
            '---',
            '',
            '转写信息：音频时长 %s 秒 ｜ 模型处理耗时 %s 秒 ｜ 脚本总耗时 %s 秒 ｜ 词数 %d ｜ 分段数 %d。' % (
                audio_sec, proc_sec, wall_sec, word_count, len(chunks)),
            '',
        ]
        if fffd:
            footer.insert(-1, '> ⚠️ 本稿含 %d 处无法解码的字符，已用「□」标出，建议人工复核对应位置。' % fffd)
            footer.insert(-1, '')
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
            'chunks': len(chunks),
            'fffd_count': fffd,
            'transcript_bytes': target.stat().st_size,
        })
        save_metrics(metrics)
        print('完成:', target.name, '| 模型耗时', proc_sec, '秒 | 总耗时', wall_sec, '秒 | 词数', word_count, '| FFFD', fffd)
        done_any = True
    if not done_any:
        print('无新录音需要转写。')


if __name__ == '__main__':
    main()
