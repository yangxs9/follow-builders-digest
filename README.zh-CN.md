# Follow Builders Digest

[English](README.md) | 简体中文

一个将 [Follow Builders](https://github.com/zarazhangrui/follow-builders) 收集的 X 动态、博客和播客整理为带来源链接的 Markdown 摘要的 [Agent Skill](https://agentskills.io)。

按需运行，产物保存在本地：脚本准备候选内容，agent 负责选稿和摘要。

## 运行要求

- 能读取 skill、运行本地脚本并写入文件的 agent。
- Python 3.10+ 和时区数据，无需第三方 Python 包。
- 能访问 GitHub API 和 `raw.githubusercontent.com`。可选：通过 `GITHUB_TOKEN` 提高 API 额度。

## 使用

按所用 agent 的 skill 机制将本目录安装为 `follow-builders-digest`，或直接让 agent 阅读 [SKILL.md](SKILL.md)，然后提出请求：

> 使用 follow-builders-digest，生成过去七天的中文精选摘要，重点关注 agent 开发。

默认使用过去 168 小时、中文（`zh-CN`）、`Asia/Shanghai` 时区和 `./output` 目录。可在请求中指定周期、语言、时区、主题或写作风格。

每次运行创建独立目录，包含 `digest.md`（摘要）、`items.json`（候选内容）和 `manifest.json`（来源记录与采集状态）。

默认生成精选摘要，覆盖范围取决于上游数据；缺少有效发布时间的条目会被排除。可通过[写作规则](references/digest-writing.md)和[模板](assets/digest-template.md)调整默认风格。

## 许可证

[MIT](LICENSE)。来源内容仍受各自的权利和条款约束。
