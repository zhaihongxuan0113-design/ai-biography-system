# 银发AI传记系统 · AI Biography System for Seniors

> 用 AI 帮助长者轻松讲述人生故事，自动整理成一本可保存、可分享、可打印的个人传记。

## 项目目标

- 打造一个类似 Remindo 的银发 AI 传记系统：以低门槛语音对话引导长者回忆人生，AI 自动完成整理、撰写、配图与排版，输出电子传记/纪念册。
- 当前阶段：**内部测试（MVP）**，先跑通「访谈 → 整理 → 成书」全流程，再逐步开放。
- 建设路线：**零代码 / 低代码优先**，以 GitHub Skills 与 Agent 编排实现，不写复杂代码。

## 当前进度（更新于 2026-09-06）

- ✅ 本地「银发AI传记项目」文件夹已与 GitHub 仓库 `ai-biography-system` 关联（默认分支 `main`）
- ✅ 仓库目录结构搭建完成：`skills/`、`docs/`、`tests/`
- ✅ 项目基础大纲已生成：`docs/项目基础大纲.md`（核心功能模块、关键步骤、Skills/Agent 资源清单）
- ✅ 本 README 已替换仓库默认版本
- ✅ 长者档案模板已生成：`docs/长者档案模板.md`（Markdown 版）+ `长者档案模板.docx`（本地打印版）
- ✅ 访谈提纲已生成：`docs/访谈提纲.md`（100 问，童年/青年/中年/老年/感悟各 20 问）+ `访谈提纲.xlsx`（本地 50 周发送计划与问题管理表）
- ✅ 语气保留指南已生成：`docs/语气保留指南.md`（逐字转写、AI 整理规则、原声二维码方案）
- ✅ 内测用例已就绪：`tests/全流程内测用例.md`（7 个场景）+ `tests/内测检查清单.xlsx` + 测试长者001示例档案 + 2 段模拟录音（tests/fixtures/）
- ✅ 每周 2 问自动发送已配置：`.github/workflows/weekly-question.yml`（每周一、周四北京时间 09:00 各建 1 个访谈 Issue，指派仓库所有者触发邮件通知）
- ✅ 录音提交说明页已上线（GitHub Pages）：https://zhaihongxuan0113-design.github.io/ai-biography-system/
- ✅ 第一位长者试访已启动：第 1 周问题（第 1、2 问）见 `tests/第1周试访问题.md`，首次发送已手动触发验证
- ✅ 语音转写自动化已配置：`skills/audio-to-text.md` + `.github/scripts/audio_to_text.py`（CrisperWhisper，逐字保留口头禅、停顿「…」、[笑]/[叹气] 等语气词，Markdown 时间戳分段）
- ✅ AI 故事整理自动化已配置：`skills/text-to-story.md` + `.github/scripts/text_to_story.py`（DeepSeek API，严格按 `docs/语气保留指南.md` 提示词整理，不改写措辞）
- ✅ 传记 PDF 生成已配置：`skills/story-to-book.md` + `.github/scripts/story_to_book.py`（封面 + 每篇故事 1 页宋体 + 页底「扫码收听原声」二维码）
- ✅ 全流程自动化工作流已上线：`.github/workflows/auto-process.yml`（新录音上传 `tests/fixtures/` 自动触发：转写 → 整理 → 成书 → 回传仓库 → Issue 评论通知，每步失败自动重试 2 次）
- ✅ 首轮全流程测试通过：2 段模拟录音已跑通，产物 `tests/transcripts/`（2 篇转写）、`tests/stories/`（2 篇故事）、`tests/books/测试长者001_第1辑.pdf`（4 页，2 个原声二维码扫码解码成功且 Pages 链接可访问）
- ✅ 测试报告已生成：`tests/全流程测试报告.md`（各步骤耗时与文件大小、转写覆盖率、语气保留度、二维码可用性、存储与 API 消耗统计）
- ⏳ 下一步：换真实长者录音复测，评估升级 Whisper medium 提升转写覆盖率，再进入批量试访

## 目录结构

```
ai-biography-system/
├── README.md                  # 项目说明与进度（本文件）
├── docs/                      # 文档：项目大纲、模板、访谈手册
│   ├── 项目基础大纲.md
│   ├── 长者档案模板.md        # 长者档案填写模板（Markdown 版）
│   ├── 访谈提纲.md            # 100 问访谈提纲 + 50 周发送计划
│   └── 语气保留指南.md        # 从录音到成书的语气保留方案
├── skills/                    # 3 个流水线技能：audio-to-text / text-to-story / story-to-book
├── tests/                     # 内测用例、测试数据、流水线产物
│   ├── 全流程内测用例.md
│   ├── 全流程测试报告.md      # 首轮全流程测试结果（耗时/准确率/消耗）
│   ├── 内测检查清单.xlsx
│   ├── 测试长者001档案.md
│   ├── 第1周试访问题.md
│   ├── 测试录音样例.md
│   ├── questions.json         # 100 问结构化数据（定时任务读取）
│   ├── metrics.json           # 每次流水线的耗时与 Token 消耗统计
│   ├── fixtures/              # 录音入口：新录音上传即自动触发全流程
│   ├── transcripts/           # 逐字转写（保留口语、停顿、语气词）
│   ├── stories/               # AI 整理后的传记故事
│   └── books/                 # 带原声二维码的 PDF（qr_codes/ 存二维码图）
├── index.html                 # GitHub Pages：录音提交说明页（根目录）
└── .github/
    ├── workflows/
    │   ├── weekly-question.yml   # 每周一、周四自动发送访谈问题
    │   └── auto-process.yml      # 录音全流程（转写→整理→成书→回传→通知）
    └── scripts/
        ├── audio_to_text.py      # CrisperWhisper 逐字转写
        ├── text_to_story.py      # DeepSeek 故事整理
        └── story_to_book.py      # WeasyPrint + qrencode 成书
```

> 本地「银发AI传记项目」文件夹另存有打印/管理用版本：`长者档案模板.docx`、`访谈提纲.xlsx`（随仓库同步上传，进度记录文档不随仓库上传）。

## 核心功能一览

| 模块 | 说明 | 主要 GitHub Skills / Agent |
| --- | --- | --- |
| 档案与用户管理 | 长者档案、家庭成员、访谈计划 | spreadsheets、数据分析师 |
| 智能访谈采集 | AI 提纲、语音问答、追问策略 | content-research-writer、meeting-notes-and-actions |
| 语音转写 | 录音 → 逐字文本（保留口语特征） | audio-to-text（CrisperWhisper） |
| 内容整理与记忆库 | 转写校对、时间线、记忆标签 | text-to-story（DeepSeek）、数据分析师 |
| 传记生成 | 分章撰写、文风定制、润色排版 | 内容创作师、documents、polish-prose |
| 多媒体与成品输出 | 老照片修复、封面插图、PDF 成书 | story-to-book（WeasyPrint + qrencode）、imagegen、pdf |
| 家庭共享与回顾 | 纪念册、节日回顾、二次增补 | presentations、效率管家 |

详见 [docs/项目基础大纲.md](docs/项目基础大纲.md)。

## 相关链接

- GitHub 仓库：https://github.com/zhaihongxuan0113-design/ai-biography-system
- 录音提交说明页（GitHub Pages）：https://zhaihongxuan0113-design.github.io/ai-biography-system/
- 每周访谈问题（Issue 列表）：https://github.com/zhaihongxuan0113-design/ai-biography-system/issues
- 本地进度记录：`银发AI传记项目/项目进度记录.docx`（本地文件，不随仓库上传）
- API 用量：DeepSeek 监控技能（deepseek-monitor）

## 参与方式（内部测试阶段）

1. 拉取本仓库到本地，与「银发AI传记项目」文件夹保持一致。
2. 在 `docs/` 阅读项目大纲、档案模板与访谈提纲，按「语气保留指南」开展访谈。
3. 在 `tests/` 按《全流程内测用例》执行内测，用《内测检查清单.xlsx》逐条核对。
4. Watch 本仓库并保持邮箱通知开启：每周一、周四新问题会以 Issue + 邮件形式送达。


