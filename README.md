# 银发AI传记系统 · AI Biography System for Seniors

> 用 AI 帮助长者轻松讲述人生故事，自动整理成一本可保存、可分享、可打印的个人传记。

## 项目目标

- 打造一个类似 Remindo 的银发 AI 传记系统：以低门槛语音对话引导长者回忆人生，AI 自动完成整理、撰写、配图与排版，输出电子传记/纪念册。
- 当前阶段：**内部测试（MVP）**，先跑通「访谈 → 整理 → 成书」全流程，再逐步开放。
- 建设路线：**零代码 / 低代码优先**，以 GitHub Skills 与 Agent 编排实现，不写复杂代码。

## 当前进度（更新于 2026-09-05）

- ✅ 本地「银发AI传记项目」文件夹已与 GitHub 仓库 `ai-biography-system` 关联（默认分支 `main`）
- ✅ 仓库目录结构搭建完成：`skills/`、`docs/`、`tests/`
- ✅ 项目基础大纲已生成：`docs/项目基础大纲.md`（核心功能模块、关键步骤、Skills/Agent 资源清单）
- ✅ 本 README 已替换仓库默认版本
- ⏳ 下一步：制作内测档案模板与访谈提纲，编写 `tests/` 内测用例，邀请第一位长者试访

## 目录结构

```
ai-biography-system/
├── README.md              # 项目说明与进度（本文件）
├── docs/                  # 文档：项目大纲、需求、访谈手册、进度记录
│   └── 项目基础大纲.md
├── skills/                # 项目专用 Skills 与提示词模板
└── tests/                 # 内测用例、验收清单
```

## 核心功能一览

| 模块 | 说明 | 主要 GitHub Skills / Agent |
| --- | --- | --- |
| 档案与用户管理 | 长者档案、家庭成员、访谈计划 | spreadsheets、数据分析师 |
| 智能访谈采集 | AI 提纲、语音问答、追问策略 | content-research-writer、meeting-notes-and-actions |
| 内容整理与记忆库 | 转写校对、时间线、记忆标签 | 数据分析师、spreadsheet-formula-helper |
| 传记生成 | 分章撰写、文风定制、润色排版 | 内容创作师、documents、polish-prose |
| 多媒体与成品输出 | 老照片修复、封面插图、PDF 成书 | imagegen、image-enhancer、pdf |
| 家庭共享与回顾 | 纪念册、节日回顾、二次增补 | presentations、效率管家 |

详见 [docs/项目基础大纲.md](docs/项目基础大纲.md)。

## 相关链接

- GitHub 仓库：https://github.com/zhaihongxuan0113-design/ai-biography-system
- 本地进度记录：`银发AI传记项目/项目进度记录.docx`（本地文件，不随仓库上传）
- API 用量：DeepSeek 监控技能（deepseek-monitor）

## 参与方式（内部测试阶段）

1. 拉取本仓库到本地，与「银发AI传记项目」文件夹保持一致。
2. 在 `docs/` 阅读项目大纲与访谈手册。
3. 在 `tests/` 按内测用例执行，并把问题记录回 `docs/` 或本地进度文档。
