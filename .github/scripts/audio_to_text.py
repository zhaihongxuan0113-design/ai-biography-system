# -*- coding: utf-8 -*-
"""audio-to-text：CrisperWhisper 逐字转写 -> 带时间戳 Markdown（保留口语特征）。
规则来源：docs/语气保留指南.md 第一步。本脚本不做任何润色与删改。"""
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

FIX = Path('tests/fixtures')
OUT = Path('tests/transcripts')
OUT.mkdir(parents=True, exist_ok=True)
METRICS = Path('tests/metrics.json')


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


def srt_to_md(srt_text):
    blocks = []
    prev_end = None
    for blk in re.split(r'\n\s*\n', srt_text.strip()):
        lines = [l for l in blk.splitlines() if l.strip()]
        if len(lines) < 3:
            continue
        tm = re.match(r'(\d+):(\d+):(\d+)[,.](\d+)\s*-->\s*(\d+):(\d+):(\d+)[,.](\d+)', lines[1])
        if not tm:
            continue
        start = int(tm.group(1)) * 3600 + int(tm.group(2)) * 60 + int(tm.group(3)) + int(tm.group(4)) / 1000.0
        end = int(tm.group(5)) * 3600 + int(tm.group(6)) * 60 + int(tm.group(7)) + int(tm.group(8)) / 1000.0
        text = ' '.join(lines[2:]).strip()
        if prev_end is not None and start - prev_end > 1.2:
            blocks.append('[%s] ……' % fmt_ts(start))
        blocks.append('[%s] %s' % (fmt_ts(start), text))
        prev_end = end
    return blocks


def main():
    files = []
    for ext in ('*.wav', '*.mp3', '*.m4a'):
        files.extend(FIX.glob(ext))
    files = sorted(set(files), key=lambda p: p.name)
    metrics = load_metrics()
    metrics.setdefault('audio_to_text', [])
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
        bin_dir = os.path.join(sys.prefix, 'bin')
        cmd = [
            os.path.join(bin_dir, 'crisper-whisper'),
            str(f),
            '--model', 'small',
            '--language', 'zh',
            '--device', 'cpu',
            '--output_format', 'srt',
            '--output_dir', str(FIX),
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        srt_path = FIX / (f.stem + '.srt')
        if not srt_path.exists():
            raise RuntimeError('未生成 srt 文件: ' + str(srt_path))
        blocks = srt_to_md(srt_path.read_text(encoding='utf-8'))
        try:
            srt_path.unlink()
        except Exception:
            pass
        duration = round(time.time() - t0, 1)
        header = [
            '# 第%d周 问题%d · 测试长者001 · 转写稿' % (week, q),
            '',
            '> 来源录音：`tests/fixtures/%s`' % f.name,
            '> 转写方式：CrisperWhisper（模型 small，语言 zh，CPU）· 逐字转写，保留口语特征',
            '> 停顿用「……」标注；笑声/叹气等情绪由人工校对补标 [笑] [叹气]；方言词原样保留。',
            '',
        ]
        body = '\n\n'.join(blocks)
        target.write_text('\n'.join(header) + '\n' + body + '\n\n---\n\n转写信息：耗时 %s 秒。\n' % duration, encoding='utf-8')
        metrics['audio_to_text'].append({
            'audio': f.name,
            'transcript': target.name,
            'duration_sec': duration,
            'transcript_bytes': target.stat().st_size,
        })
        save_metrics(metrics)
        print('完成:', target.name, duration, '秒')
        done_any = True
    if not done_any:
        print('无新录音需要转写。')


if __name__ == '__main__':
    main()
