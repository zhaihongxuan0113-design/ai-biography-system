# 技能：audio-to-text（语音转写 · 保留口语特征）

> 对应工作流步骤：auto-process.yml 步骤 1 ｜ 实现脚本：.github/scripts/audio_to_text.py
> 调研来源：CrisperWhisper 2.0（https://github.com/nyrahealth/CrisperWhisper ，逐字转写、自带填充词/重复/停顿/笑声保留），配合 ffmpeg 解码。

## 功能
把长者访谈录音逐字转成带时间戳的 Markdown 转写稿，全程保留口语特征，供下一步 AI 整理使用。

## 输入
- 路径：`tests/fixtures/` 下所有 `.wav` / `.mp3` / `.m4a` 录音文件
- 文件命名二选一：
  - 规范式：`第1周_问题1_测试长者001_20260905.m4a`（周次、问题号、长者代号、日期）
  - 简式：`录音01_童年_小时候的家.wav`（录音序号即可，自动换算周次与问题号：第 (N+1)/2 周、第 N 问）

## 输出
- 路径：`tests/transcripts/`
- 命名：与录音一一对应，如 `第1周_问题1_测试长者001_转写.md`
- 格式：Markdown，按时间分段，每段带 `[MM:SS]` 时间戳

## 转写规则（严格遵循《语气保留指南》第一步）
1. 逐字转写：口头禅（嗯、啊、那个、对喽、哎呦）、语气词、重复的话、说一半的话，全部保留；
2. 不修正语法、不润色、不删除跑题内容；
3. 停顿用「……」标注（段间停顿超过约 1.2 秒时插入停顿行）；
4. 笑声/叹气等情绪用方括号标注，如「[笑]」「[叹气]」（CrisperWhisper 无情绪检测时，由人工校对补齐）；
5. 方言词、口音特色词原样保留，可加小括号注释；
6. 文末附转写信息：模型、语言、音频时长、转写耗时。

## 参数（CrisperWhisper 2.0 Python API）
- PyPI 包名：`crisperwhisper`（无连字符；旧包 `crisper-whisper` 与旧 CLI 已失效）
- 安装：`pip install "crisperwhisper[transformers]"`（纯 PyTorch CPU 后端；GPU 可用 `[ct2]`）
- 已知坑（2.0 上游打包遗漏）：`hallucination` 模块无条件 `import ctranslate2`，而 `[transformers]` 扩展不含它，需补装：`pip install ctranslate2`
- 已知坑（长音频 + HF 后端）：续写上下文过长会触发 Whisper `max_target_positions=448` 报错（「decoder_input_ids 269 + max_new_tokens 256 > 448」）；脚本内已将续写上下文截断至 60 字符规避
- 模型：`small` → HuggingFace `nyralabs/CrisperWhisper2.0_small`（首次运行自动下载，约 500MB，已配 HuggingFace 缓存）
- 调用方式（脚本内已实现）：
  ```python
  from crisperwhisper import CrisperWhisperModel
  model = CrisperWhisperModel("small", backend="transformers", device="cpu", compute_type="float32")
  result = model.transcribe("录音.wav", language="zh", mode="verbatim", word_timestamps=True)
  # result.text：完整转写文本；result.words：逐词 WordTimestamp(word, start, end)；
  # result.duration：音频时长；result.processing_time：模型处理耗时
  ```
- 输出：由脚本按 `result.words` 生成带 `[MM:SS]` 时间戳的 Markdown（不再是 srt 文件）
- 英文情绪标签自动换算：`[laughter]`→`[笑]`、`[sigh]`→`[叹气]`、`[cough]`→`[咳嗽]` 等；填充词 `[UM]`/`[UH]`→「嗯，」「啊，」；模型误报的非言语标签（`[crying]` `[scream]` `[sneeze]` 等）自动剔除
- 正文取整段解码的 `result.text`（避免逐词切分导致的中文 U+FFFD 乱码），`result.words` 仅用于行首时间戳与停顿（>1.2 秒插入「……」）标注

## 许可提示（内部测试备忘）
- 推理代码 MIT；标准模型权重为非商业研究许可，Pro 模型需商业许可。正式商用前需联系 Nyra 获取授权。

## 幂等与重试
- 已存在同名转写稿的录音自动跳过（不重复转写）；
- 工作流内自动重试 2 次（共 3 次），仍失败则向访谈 Issue 评论错误原因。

## 验证方法
- 对照 `tests/测试录音样例.md` 中的文字稿核对内容一致率与语气词保留率；
- 抽查 1 分钟音频与转写稿逐句比对；
- 检查每段均有时间戳、停顿与情绪标注符合约定。
