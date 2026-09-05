# -*- coding: utf-8 -*-
"""story-to-book：故事 -> 带原声二维码的传记 PDF（WeasyPrint 排版 + qrencode 二维码 + 思源宋体）。"""
import html as H
import json
import os
import re
import subprocess
import time
import urllib.parse
from pathlib import Path

PAGES_BASE = os.environ.get('PAGES_BASE', 'https://zhaihongxuan0113-design.github.io/ai-biography-system')
VOLUME = 1
OUT = Path('tests/books')
OUT.mkdir(parents=True, exist_ok=True)
QRDIR = OUT / 'qr_codes'
QRDIR.mkdir(parents=True, exist_ok=True)
METRICS = Path('tests/metrics.json')
FIX = Path('tests/fixtures')

# 两个故事分组：真人测试组（文件名带「真人测试_」前缀）与模拟测试组（测试长者001）。
# 两组各自成书，PDF 文件名互不覆盖。
GROUPS = [
    ('真人测试_', '真人测试'),
    ('', '测试长者001'),
]


def load_metrics():
    if METRICS.exists():
        try:
            return json.loads(METRICS.read_text(encoding='utf-8'))
        except Exception:
            pass
    return {}


def save_metrics(m):
    METRICS.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding='utf-8')


def find_audio(prefix, week, q):
    for ext in ('*.wav', '*.mp3', '*.m4a'):
        for f in sorted(FIX.glob(ext)):
            if f.stem.startswith('%s第%d周_问题%d_' % (prefix, week, q)):
                return f
    n = (week - 1) * 2 + q
    for ext in ('*.wav', '*.mp3', '*.m4a'):
        for f in sorted(FIX.glob(ext)):
            if re.match(r'^%s录音0*%d_' % (re.escape(prefix), n), f.stem):
                return f
    return None


def audio_url(f):
    return PAGES_BASE + '/tests/fixtures/' + urllib.parse.quote(f.name)


def md_to_html(md):
    out = []
    in_quote = False
    for line in md.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith('## '):
            if in_quote:
                out.append('</blockquote>')
                in_quote = False
            out.append('<h2>' + H.escape(s[3:]) + '</h2>')
        elif s.startswith('# '):
            if in_quote:
                out.append('</blockquote>')
                in_quote = False
            out.append('<h1>' + H.escape(s[2:]) + '</h1>')
        elif s.startswith('> 本文') or s.startswith('---'):
            continue
        elif s.startswith('> '):
            if not in_quote:
                out.append('<blockquote>')
                in_quote = True
            out.append('<p>' + H.escape(s[2:]) + '</p>')
        elif s.startswith('- '):
            if in_quote:
                out.append('</blockquote>')
                in_quote = False
            out.append('<p>· ' + H.escape(s[2:]) + '</p>')
        else:
            if in_quote:
                out.append('</blockquote>')
                in_quote = False
            out.append('<p>' + H.escape(s) + '</p>')
    if in_quote:
        out.append('</blockquote>')
    return '\n'.join(out)


def make_qr(url, png_path):
    subprocess.run(['qrencode', '-o', str(png_path), '-s', '6', '-m', '1', url], check=True)


def build_book(prefix, label):
    """按分组前缀把故事打包成一辑 PDF。返回 (pdf 名, 故事页数, 二维码数, 耗时) 或 None。"""
    stories = sorted(Path('tests/stories').glob('%s第*周_问题*_故事.md' % prefix))
    if not stories:
        print('没有故事文件，跳过成书:', label)
        return None
    pages_html = []
    qr_count = 0
    for st in stories:
        m = re.match(r'^%s第(\d+)周_问题(\d+)(?:_%s)?_故事\.md$' % (re.escape(prefix), label), st.name)
        if not m:
            continue
        week, q = int(m.group(1)), int(m.group(2))
        audio = find_audio(prefix, week, q)
        qr_html = ''
        if audio is not None:
            url = audio_url(audio)
            png = QRDIR / ('qr_%s第%d周_问题%d_%s.png' % (prefix, week, q, label))
            make_qr(url, png)
            qr_count += 1
            qr_html = (
                '<div class="qr"><img src="%s" alt="原声二维码"/><br/>'
                '<span class="qr-label">扫码收听原声</span></div>'
                % ('qr_codes/' + png.name)
            )
        body = md_to_html(st.read_text(encoding='utf-8'))
        pages_html.append(
            '<div class="story">' + body + qr_html + '</div>'
        )
    cover = (
        '<div class="cover">'
        '<h1 class="book-title">我的人生回忆录</h1>'
        '<p class="book-sub">%s · 第 %d 辑</p>'
        '<p class="book-date">2026 年 · 内部测试版</p>'
        '</div>'
    ) % (label, VOLUME)
    html_doc = (
        '<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8"/>'
        '<style>'
        '@page { size: A4; margin: 2cm 2cm 2.6cm 2cm; }'
        'body { font-family: "Noto Serif CJK SC", serif; font-size: 12pt; line-height: 1.9; color: #222; }'
        '.cover { page-break-after: always; text-align: center; padding-top: 9cm; }'
        '.book-title { font-size: 34pt; letter-spacing: 8pt; margin-bottom: 1.2cm; }'
        '.book-sub { font-size: 16pt; color: #555; }'
        '.book-date { font-size: 11pt; color: #999; margin-top: 0.6cm; }'
        '.story { page-break-after: always; }'
        '.story h1 { font-size: 15pt; font-weight: bold; border-bottom: 1.5pt solid #8c5a2b; padding-bottom: 6pt; }'
        '.story h2 { font-size: 13pt; font-weight: bold; color: #8c5a2b; margin-top: 10pt; }'
        '.story blockquote { border-left: 3pt solid #d9a05b; margin: 8pt 0; padding: 4pt 10pt; background: #fdf6ec; }'
        '.qr { text-align: center; margin-top: 24pt; page-break-inside: avoid; }'
        '.qr img { width: 3.2cm; height: 3.2cm; }'
        '.qr-label { font-size: 10.5pt; color: #666; }'
        '</style></head><body>' + cover + '\n'.join(pages_html) + '</body></html>'
    )
    html_path = OUT / ('%s_第%d辑.html' % (label, VOLUME))
    pdf_path = OUT / ('%s_第%d辑.pdf' % (label, VOLUME))
    html_path.write_text(html_doc, encoding='utf-8')
    t0 = time.time()
    subprocess.run(['weasyprint', str(html_path), str(pdf_path)], check=True, capture_output=True)
    duration = round(time.time() - t0, 1)
    print('完成:', pdf_path.name, duration, '秒 | 故事页数:', len(pages_html), '| 二维码:', qr_count)
    return pdf_path.name, len(pages_html), qr_count, duration


def main():
    metrics = load_metrics()
    metrics.setdefault('story_to_book', [])
    for prefix, label in GROUPS:
        result = build_book(prefix, label)
        if result is None:
            continue
        pdf_name, pages, qr_count, duration = result
        metrics['story_to_book'].append({
            'pdf': pdf_name,
            'stories': pages,
            'qr_codes': qr_count,
            'duration_sec': duration,
            'pdf_bytes': (OUT / pdf_name).stat().st_size,
        })
        save_metrics(metrics)


if __name__ == '__main__':
    main()

