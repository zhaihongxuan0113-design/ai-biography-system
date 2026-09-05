# -*- coding: utf-8 -*-
"""text-to-story：严格按 docs/语气保留指南.md 第二步规则，用 DeepSeek 把逐字转写稿整理成传记故事。
规则原文运行时读取，本脚本不自行修改规则。"""
import json
import os
import re
import time
import urllib.request
from pathlib import Path

KEY = os.environ.get('DEEPSEEK_API_KEY') or ''
if not KEY:
    raise SystemExit('缺少环境变量 DEEPSEEK_API_KEY')

GUIDE = Path('docs/语气保留指南.md').read_text(encoding='utf-8')
m = re.search(r'## 第二步：AI 整理故事时.*?(?=## 第三步)', GUIDE, re.S)
RULES = m.group(0).strip() if m else ''
if not RULES:
    raise SystemExit('未找到《语气保留指南》第二步规则')

OUT = Path('tests/stories')
OUT.mkdir(parents=True, exist_ok=True)
METRICS = Path('tests/metrics.json')
QUESTIONS = json.loads(Path('tests/questions.json').read_text(encoding='utf-8'))


def load_metrics():
    if METRICS.exists():
        try:
            return json.loads(METRICS.read_text(encoding='utf-8'))
        except Exception:
            pass
    return {}


def save_metrics(m):
    METRICS.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding='utf-8')


def call_deepseek(system, user):
    data = json.dumps({
        'model': 'deepseek-chat',
        'messages': [
            {'role': 'system', 'content': system},
            {'role': 'user', 'content': user},
        ],
        'temperature': 0.5,
        'max_tokens': 3000,
    }).encode('utf-8')
    req = urllib.request.Request(
        'https://api.deepseek.com/v1/chat/completions',
        data=data,
        headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + KEY},
    )
    with urllib.request.urlopen(req, timeout=300) as r:
        j = json.loads(r.read().decode('utf-8'))
    return j['choices'][0]['message']['content'], j.get('usage', {})


def main():
    metrics = load_metrics()
    metrics.setdefault('text_to_story', [])
    done_any = False
    for t in sorted(Path('tests/transcripts').glob('*_转写.md')):
        m2 = re.match(r'第(\d+)周_问题(\d+)_测试长者001_转写\.md', t.name)
        if not m2:
            continue
        week, q = int(m2.group(1)), int(m2.group(2))
        target = OUT / ('第%d周_问题%d_测试长者001_故事.md' % (week, q))
        if target.exists():
            print('已存在，跳过:', target.name)
            continue
        question = QUESTIONS[q - 1]['q']
        text = t.read_text(encoding='utf-8')
        system = (
            '你是银发传记的文字整理助手。必须严格按下面《语气保留指南》第二步的整理规则执行，不得自行修改规则。\n\n'
            '【整理规则（原样执行）】\n' + RULES + '\n\n'
            '【输出格式要求】\n'
            '1. 第一行用 Markdown 一级标题，格式：第%d周 问题%d · %s\n'
            '2. 正文按回忆主题分段，每段一个二级标题（## 小标题）概括该段主题；\n'
            '3. 正文中只梳理逻辑顺序、拆分段落，不改写措辞、不替换口语词、不补充虚构细节；\n'
            '4. 结尾单独一段二级标题「## 原话金句」，用引用格式（> 开头）保留长者最有味道的原话，一字不改。\n'
        ) % (week, q, question)
        user = ('下面是第%d周问题%d的逐字转写稿，请整理成传记故事：\n\n' % (week, q)) + text
        t0 = time.time()
        story = None
        usage = {}
        for attempt in range(3):
            try:
                story, usage = call_deepseek(system, user)
                break
            except Exception as e:
                print('DeepSeek 调用失败（第%d次）:' % (attempt + 1), e)
                time.sleep(10)
        if not story:
            raise SystemExit('DeepSeek 连续 3 次调用失败')
        target.write_text(
            story.rstrip() + '\n\n---\n\n> 本文由 DeepSeek 按《语气保留指南》第二步规则整理；原始逐字稿见 ' + t.name + '。\n',
            encoding='utf-8',
        )
        duration = round(time.time() - t0, 1)
        metrics['text_to_story'].append({
            'story': target.name,
            'transcript': t.name,
            'duration_sec': duration,
            'usage': usage,
            'story_bytes': target.stat().st_size,
        })
        save_metrics(metrics)
        print('完成:', target.name, duration, '秒 | tokens:', usage.get('total_tokens'))
        done_any = True
    if not done_any:
        print('无新转写稿需要整理。')


if __name__ == '__main__':
    main()
