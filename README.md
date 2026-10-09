# Follow Builders Digest Skill

按需生成 [Follow Builders](https://github.com/zarazhangrui/follow-builders) 内容摘要的 agent skill。默认整理过去七天发布的内容，生成带原始链接的中文 Markdown digest。

触发时才读取上游 Git 历史，无需每天采集、部署常驻服务或维护内容数据库。脚本负责历史查询、下载、过滤和单次去重；agent 负责筛选内容和撰写摘要。

当前版本仅生成本地文件，不支持邮件投递或自动调度。

## 运行要求

- 能读取 skill 指令、运行本地脚本并写入文件的 agent。
- Python 3.10 或更新版本，以及可用的时区数据；无需安装第三方 Python 包。
- 能访问 GitHub API 和 `raw.githubusercontent.com` 的网络。
- 可选的 `GITHUB_TOKEN` 环境变量，用于提高 GitHub API 请求额度。

仅使用脚本时不需要 agent，但有内容的 digest 需要由 agent 撰写。

## 在 agent 中使用

本地项目目录统一命名为 `follow-builders-digest`；进入该目录后执行下文命令。

将整个项目目录放入你的 agent 支持的 skill 目录，保留 `SKILL.md`、`scripts/` 和配置文件的相对位置。不同 agent 的安装与发现机制不同，按对应宿主的说明加载；这个 skill 的名称是 `follow-builders-digest`。

也可以直接在项目目录中工作，让 agent 阅读 `SKILL.md` 后执行。示例请求：

> 阅读这个项目的 SKILL.md，按指引生成过去七天的 Follow Builders digest，保存到当前工作区的 output 目录。

> 使用 follow-builders-digest，整理上海时间 2026 年 10 月 1 日至 10 月 8 日的内容，结束时间不包含在内，生成中文摘要。

Agent 会运行脚本，阅读候选内容与运行报告，再按 `assets/digest-template.md` 在本次运行目录中写入 `digest.md`。摘要按 X、博客和播客分组，空分类省略；每条包含概括、具体细节、英文摘录和原始链接。

报告标题显示时间范围，正文不包含运行日志、数量统计或单条发布时间。数据缺失在交互回复或未来 cron job 的输出中简要说明，详细信息保留在 `manifest.json`。当前版本仍为手动触发。

### 调整报告模板

编辑 `assets/digest-template.md` 可调整栏目、条目顺序、篇幅和英文引用方式。`SKILL.md` 要求 agent 在生成前读取该文件。模板保留英文原文供直接阅读，不讲解英文用法；中文补充背景、例子和观点，重要内容可以增加摘录。

## 配置

可以直接使用 `config.example.json`，或复制后修改：

```sh
cp config.example.json config.json
```

```json
{
  "days": 7,
  "language": "zh-CN",
  "timezone": "Asia/Shanghai",
  "output_dir": "./output"
}
```

| 字段 | 用途 | 默认值 |
| --- | --- | --- |
| `days` | 默认回看天数，必须为正整数 | `7` |
| `language` | Agent 撰写摘要的语言 | `zh-CN` |
| `timezone` | 解释日期及不带偏移量的时间 | `Asia/Shanghai` |
| `output_dir` | 运行产物的父目录 | `./output` |

命令行参数覆盖对应配置。不指定配置文件也能使用上述默认值。相对输出路径基于**执行命令时的工作目录**，不是配置文件所在目录；安装后建议指定工作区中的输出路径。

## 单独运行脚本

以下命令在项目根目录执行。先发现可用解释器并逐个检查版本，不要假定 `python3` 满足要求。可用 `command -v` 查找 `python3` 或 `python3.14`、`python3.13`、`python3.12`、`python3.11`、`python3.10` 等版本化命令；macOS 也可检查 `/opt/homebrew/bin`、`/usr/local/bin` 和 `/Library/Frameworks/Python.framework/Versions/*/bin` 中已有的安装。其他环境可检查包管理器或虚拟环境提供的解释器。

用候选解释器自身的 `--version` 检查版本，选定 Python >=3.10 的绝对可执行路径；后续脚本和测试始终使用同一个 `PYTHON`。没有符合要求的解释器时，停止并报告缺少的运行要求。

```sh
PYTHON=/absolute/path/to/selected/python
"$PYTHON" -c 'import sys; print(sys.executable, sys.version); assert sys.version_info >= (3, 10), "Python >=3.10 required"'
```

默认过去七天：

```sh
"$PYTHON" scripts/prepare_digest.py --config config.example.json
```

指定回看天数和输出目录：

```sh
"$PYTHON" scripts/prepare_digest.py --days 14 --output-dir ./output
```

指定日期范围：

```sh
"$PYTHON" scripts/prepare_digest.py \
  --config config.example.json \
  --start 2026-10-01 \
  --end 2026-10-08
```

指定带时区的时间范围：

```sh
"$PYTHON" scripts/prepare_digest.py \
  --start '2026-10-01T09:00:00+08:00' \
  --end '2026-10-08T09:00:00+08:00'
```

`--start` 和 `--end` 必须同时提供，不能与命令行中的 `--days` 一起使用。配置中的默认 `days` 不妨碍指定日期范围。

筛选按内容发布时间，区间为 `[start, end)`：包含起点，不包含终点。日期表示配置时区的当天零点；带偏移量的时间按自身偏移量解释。默认七天是从运行开始时间向前推 **168 小时**，不是上一自然周。

**脚本通常只生成候选集和运行报告，不直接生成摘要。** 脚本结束后，让 agent 按 `SKILL.md` 读取本次目录中的文件并撰写 `digest.md`。只有成功获取但候选集为空时，脚本会直接生成简短的空结果 digest。

## 输出文件

每次执行创建独立目录，不覆盖之前的结果：

```text
output/
└── <UTC运行时间>-<随机后缀>/
    ├── items.json
    ├── manifest.json
    └── digest.md       # 通常由 agent 随后生成
```

- `items.json`：标准化、按发布时间过滤并去重后的内容，含正文、原始链接和快照出处。
- `manifest.json`：请求周期、运行时间、固定的上游 HEAD SHA、快照清单、统计、错误和数据质量提示。
- `digest.md`：供阅读的摘要。

脚本向标准输出打印一行 JSON，包含 `status`、绝对路径 `run_dir` 和 `item_count`。

| 状态 | 含义 | 退出码 |
| --- | --- | --- |
| `ok` | 获取和处理成功；候选集可能为空 | `0` |
| `partial` | 部分历史、快照或上游采集有错误；可继续摘要可用内容 | `0` |
| `failed` | 无法成功获取或处理任何来源；查看报告，不应解读为没有内容 | `1` |

参数或配置错误以退出码 `2` 结束。判断部分成功应查看 `status` 和报告，而不只检查退出码。原始快照暂存在临时目录，处理后删除；运行产物保留在输出目录，`output/` 默认被 Git 忽略。

## 时间、去重与覆盖范围

- 每次运行固定上游 `main` 的 HEAD SHA，随后按 SHA 读取历史快照。
- 除周期内的提交，还读取起点前的基准快照，以及周期结束后直到本次运行的提交，以纳入延迟采集的内容。
- 历史 digest 使用“截至本次运行已知的数据”，不保证与过去某次运行完全一致。
- X 按 tweet ID、播客按来源与 GUID、博客按规范化 URL 做单次去重。不同运行间不记录已读或已生成的内容，周期重叠时可以重复出现。
- 缺失或无效发布时间的条目排除并计数，不以采集时间替代。报告中的观察次数可能包含同一条目在不同快照中的重复出现。
- 只能恢复上游曾提交的内容。上游采集有数量限制，也可能失败，因此快照读取成功不代表源内容完整；空 feed 也不等于获取失败。

## 常见问题

**GitHub 限流或认证失败**

脚本可通过环境变量 `GITHUB_TOKEN` 使用已有凭据。凭据不放入配置文件，也不写入运行产物；请通过你的运行环境设置。匿名额度耗尽时，可配置 token 或等额度恢复后重新执行；认证失败时检查 token 是否有效。脚本不会自动读取本机 `gh` 登录。

**只有 JSON 文件，没有 digest.md**

这是有候选内容时的正常结果。继续让 agent 阅读 `SKILL.md`、`items.json` 和 `manifest.json`，完成筛选和摘要。

**部分来源失败或没有有效日期**

可以继续生成已有内容的摘要，并在任务输出中简要说明缺失，避免将缺失误写成“本周无动态”。报告正文不加入这些运行信息，详细原因见 `manifest.json`。

**摘要或源数据很长**

Agent 应分批完整读取正文再摘要，不静默截断。播客原始链接有时只指向频道或播放列表，digest 会说明这个限制。

## 验证

使用上面选定且检查过的同一个解释器，运行不依赖网络的测试：

```sh
"$PYTHON" -m unittest discover -s tests -v
```

测试覆盖时间边界、去重、版本更新、延迟采集、分页、重试和部分失败等行为。真实运行后，还应核对摘要来源链接、原文摘录、周期和模板结构。
