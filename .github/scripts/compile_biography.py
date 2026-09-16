# -*- coding: utf-8 -*-
"""compile-biography（text-to-story 技能 · 传记整合模式）：
把「老爸自传_第X段_转写.md」多段逐字稿整合成章节化传记初稿。

规则来源：docs/语气保留指南.md 第二步原文 + 真人场景补充规则，本脚本不自行修改规则；
输出格式要求（章节划分、小标题、每章原话金句）在此脚本内按本次任务约定配置。
"""
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

TRANS_DIR = Path('tests/transcripts')
OUT = Path('tests/stories')
OUT.mkdir(parents=True, exist_ok=True)
METRICS = Path('tests/metrics.json')

# 真人场景补充规则（与 text_to_story.py 保持一致；冲突时以本补充为准）
REAL_RULES = (
    '【真人场景补充规则（真人口语访谈时生效；与上文冲突时以本补充为准）】\n'
    '1. 允许内容跑题：保留真实的聊天感，跑题内容不删除，可顺其自然归入相近的段落；\n'
    '2. 保留老人常用的口头禅、俗语、地方话，不解释、不替换、不翻译，必要时在旁边用小括号注明意思；\n'
    '3. 只梳理逻辑顺序、拆分段落，绝不改写措辞、不替换口语词、不补充虚构细节；\n'
    '4. 每段加一个小标题，概括该段回忆主题；\n'
    '5. 结尾提炼一句老人的原话作为金句，一字不改。'
)

CHAPTERS = [
    ('第一章', '童年与成长'),
    ('第二章', '军旅岁月'),
    ('第三章', '国企工作生涯'),
    ('第四章', '下海创业经历'),
    ('第五章', '房地产行业打拼'),
    ('第六章', '人生感悟与寄语'),
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


def call_deepseek(system, user):
    data = json.dumps({
        'model': 'deepseek-chat',
        'messages': [
            {'role': 'system', 'content': system},
            {'role': 'user', 'content': user},
        ],
        'temperature': 0.5,
        'max_tokens': 8000,
    }).encode('utf-8')
    req = urllib.request.Request(
        'https://api.deepseek.com/v1/chat/completions',
        data=data,
        headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + KEY},
    )
    with urllib.request.urlopen(req, timeout=600) as r:
        j = json.loads(r.read().decode('utf-8'))
    return j['choices'][0]['message']['content'], j.get('usage', {})


def md_to_txt(md):
    out = []
    for line in md.splitlines():
        s = line.strip()
        if not s:
            out.append('')
            continue
        s = re.sub(r'^#{1,6}\s*', '', s)
        s = s.replace('**', '')
        s = re.sub(r'^>\s*', '　', s)
        s = re.sub(r'\[([^\]]{1,4})\]', r'\1', s)
        out.append(s)
    return '\n'.join(out)


def main():
    files = sorted(TRANS_DIR.glob('老爸自传_第*段_转写.md'),
                   key=lambda p: int(re.match(r'老爸自传_第(\d+)段', p.name).group(1)))
    if not files:
        raise SystemExit('未找到老爸自传转写稿（tests/transcripts/老爸自传_第*段_转写.md）')
    parts = []
    for f in files:
        seg = int(re.match(r'老爸自传_第(\d+)段', f.name).group(1))
        text = f.read_text(encoding='utf-8')
        text = re.sub(r'^# .*$', '', text, count=1, flags=re.M).strip()
        text = re.sub(r'^> .*$\n?', '', text, flags=re.M).strip()
        text = re.sub(r'^---\s*$', '', text, flags=re.M).strip()
        parts.append('【第%d段录音的逐字转写稿】\n%s' % (seg, text))
    user = '下面是父亲自由讲述人生经历的 %d 段逐字转写稿（已按录音顺序排列）。\n请按系统要求整合成一部章节化传记初稿。\n\n%s' % (
        len(files), '\n\n'.join(parts))

    chapter_spec = '\n'.join(
        '%d. %s %s（本章结尾提炼 1-2 句父亲原话金句，用引用格式 > 开头，一字不改）' % (i, c[0], c[1])
        for i, c in enumerate(CHAPTERS, 1)
    )
    system = (
        '你是银发传记的文字整理助手。必须严格按下面《语气保留指南》第二步的整理规则执行，不得自行修改规则。\n\n'
        '【整理规则（原样执行）】\n' + RULES + '\n\n' + REAL_RULES + '\n\n'
        '【本次任务：把多段自由讲述整合成一部传记初稿】\n'
        '1. 第一行输出 Markdown 一级标题：# 老爸自传（初稿）；\n'
        '2. 全文严格按下面 6 章组织，每章用二级标题（## 第一章 童年与成长 等）：\n' + chapter_spec + '\n'
        '3. 章节内按回忆主题用小节（### 小标题）拆分段落；\n'
        '4. 允许跨录音段落整合：同一主题的内容可以合并到对应章节，不必对应原录音分段顺序；\n'
        '5. 内容必须全部来自转写稿：只梳理逻辑顺序、拆分段落、跨段整合，绝不改写措辞、不替换口语词、不补充虚构细节；\n'
        '6. 保留 [笑] [叹气] 等情绪标注，或自然写出「说到这里，老人家笑了」；保留时代特色表述（如大锅饭、下海、商品房等）；\n'
        '7. 若某章在录音中没有对应内容，保留该章标题，正文写「（本章素材不足，留待后续访谈补充。）」，不得虚构；\n'
        '8. 不要输出任何与传记正文无关的说明、点评或总结；结尾不要另起「原话金句」总章节，金句只放在各章末尾。'
    )

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
    story = story.rstrip()
    md_path = OUT / '老爸自传_初稿.md'
    txt_path = OUT / '老爸自传_初稿.txt'
    md_path.write_text(
        story + '\n\n---\n\n> 本文由 DeepSeek 按《语气保留指南》第二步规则 + 真人场景补充规则整理；'
        '原始逐字稿见 tests/transcripts/老爸自传_第1-6段_转写.md。\n',
        encoding='utf-8',
    )
    txt_path.write_text(md_to_txt(story) + '\n', encoding='utf-8')
    duration = round(time.time() - t0, 1)
    metrics = load_metrics()
    metrics.setdefault('text_to_story', []).append({
        'story': md_path.name,
        'kind': 'biography',
        'transcripts': [f.name for f in files],
        'duration_sec': duration,
        'usage': usage,
        'story_bytes': md_path.stat().st_size,
        'txt_bytes': txt_path.stat().st_size,
    })
    save_metrics(metrics)
    chinese = len(re.sub(r'[^\u4e00-\u9fff]', '', story))
    print('完成: %s | %d 秒 | tokens: %s | 总字数(含标点): %d | 汉字: %d | 纯文本版: %s' % (
        md_path.name, duration, usage.get('total_tokens'), len(story), chinese, txt_path.name))


if __name__ == '__main__':
    main()
